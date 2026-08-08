"""
Train an Expected Goals (xG) logistic-regression model on StatsBomb open data
and export coefficients to xg_coeffs.json, which soccer_analytics.py loads at
startup.

The features (distance to goal, visible goal angle) are computed EXACTLY the
same way as calculate_xg() in soccer_analytics.py, so the learned coefficients
transfer directly to live inference.

StatsBomb open data is fetched straight from their public GitHub repo, so the
only dependencies are: requests, pandas, scikit-learn (already installed).

Usage:
    python train_xg.py                 # default: up to 200 matches
    python train_xg.py --max-matches 50
    python train_xg.py --competition 11 --season 90   # specific comp/season
"""

import os
import json
import argparse
from typing import List, Optional

import requests
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, log_loss
from analytics_core import PITCH_LENGTH_M, PITCH_WIDTH_M, shot_features as canonical_shot_features

# Keep these in sync with soccer_analytics.py

# StatsBomb pitch coordinate system is 120 x 80
SB_LENGTH = 120.0
SB_WIDTH = 80.0

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
COEFFS_PATH = os.path.join(os.path.dirname(__file__), "xg_coeffs.json")

_session = requests.Session()


def _get_json(url: str):
    """Fetch and parse a JSON document, raising on HTTP errors."""
    resp = _session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def shot_features(x_sb: float, y_sb: float) -> Optional[tuple]:
    """
    Convert a StatsBomb shot location to (distance, angle) features,
    computed identically to calculate_xg() in soccer_analytics.py.

    Returns None if the location is invalid.
    """
    if x_sb is None or y_sb is None:
        return None

    # Convert StatsBomb coords -> meters on a 105 x 68 pitch
    sx = x_sb / SB_LENGTH * PITCH_LENGTH_M
    sy = y_sb / SB_WIDTH * PITCH_WIDTH_M

    return canonical_shot_features((sx, sy), "right")


def list_match_ids(competition: Optional[int],
                   season: Optional[int],
                   max_matches: int) -> List[int]:
    """Collect match IDs from StatsBomb open data."""
    competitions = _get_json(f"{BASE_URL}/competitions.json")

    pairs = []
    for comp in competitions:
        cid, sid = comp["competition_id"], comp["season_id"]
        if competition is not None and cid != competition:
            continue
        if season is not None and sid != season:
            continue
        pairs.append((cid, sid))

    match_ids = []
    for cid, sid in pairs:
        try:
            matches = _get_json(f"{BASE_URL}/matches/{cid}/{sid}.json")
        except requests.HTTPError:
            continue
        for m in matches:
            match_ids.append(m["match_id"])
            if len(match_ids) >= max_matches:
                return match_ids
    return match_ids


def collect_shots(match_ids: List[int]) -> pd.DataFrame:
    """Download events for each match and extract shot rows."""
    rows = []
    for i, match_id in enumerate(match_ids, 1):
        try:
            events = _get_json(f"{BASE_URL}/events/{match_id}.json")
        except requests.HTTPError:
            continue

        for ev in events:
            if ev.get("type", {}).get("name") != "Shot":
                continue
            shot = ev.get("shot", {})
            # Exclude penalties: fixed-spot, distort a distance/angle model
            if shot.get("type", {}).get("name") == "Penalty":
                continue

            loc = ev.get("location")
            if not loc or len(loc) < 2:
                continue

            feats = shot_features(loc[0], loc[1])
            if feats is None:
                continue

            is_goal = 1 if shot.get("outcome", {}).get("name") == "Goal" else 0
            rows.append({
                "distance": feats[0],
                "angle": feats[1],
                "goal": is_goal,
                "sb_xg": shot.get("statsbomb_xg"),
            })

        if i % 10 == 0 or i == len(match_ids):
            print(f"   … processed {i}/{len(match_ids)} matches, "
                  f"{len(rows)} shots so far")

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Train an xG logistic model on StatsBomb open data.")
    parser.add_argument("--max-matches", type=int, default=200,
                        help="Maximum number of matches to download.")
    parser.add_argument("--competition", type=int, default=None,
                        help="Restrict to a StatsBomb competition_id.")
    parser.add_argument("--season", type=int, default=None,
                        help="Restrict to a StatsBomb season_id.")
    args = parser.parse_args()

    print("Fetching match list from StatsBomb open data...")
    match_ids = list_match_ids(args.competition, args.season, args.max_matches)
    if not match_ids:
        print("No matches found for the given filters.")
        return
    print(f"Found {len(match_ids)} matches. Downloading shot events...")

    df = collect_shots(match_ids)
    if df.empty:
        print("No shots collected.")
        return

    print(f"\nCollected {len(df)} shots "
          f"({int(df['goal'].sum())} goals, "
          f"{df['goal'].mean() * 100:.1f}% conversion).")

    X = df[["distance", "angle"]].to_numpy()
    y = df["goal"].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    # Evaluate
    proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)
    ll = log_loss(y_test, proba)
    print(f"\nModel performance on held-out test set:")
    print(f"   ROC AUC : {auc:.3f}")
    print(f"   LogLoss : {ll:.3f}")

    # Sanity check vs StatsBomb's own xG, where available
    sb = df.dropna(subset=["sb_xg"])
    if len(sb) > 0:
        sb_ll = log_loss(sb["goal"], sb["sb_xg"].clip(1e-6, 1 - 1e-6))
        print(f"   (StatsBomb's own xG LogLoss on all shots: {sb_ll:.3f})")

    coeffs = {
        "intercept": float(model.intercept_[0]),
        "distance": float(model.coef_[0][0]),
        "angle": float(model.coef_[0][1]),
        "_meta": {
            "n_shots": int(len(df)),
            "n_goals": int(df["goal"].sum()),
            "test_auc": round(float(auc), 4),
            "test_logloss": round(float(ll), 4),
            "pitch_length_m": PITCH_LENGTH_M,
            "pitch_width_m": PITCH_WIDTH_M,
            "feature_version": 2,
        },
    }

    with open(COEFFS_PATH, "w") as f:
        json.dump(coeffs, f, indent=2)

    print(f"\nSaved trained coefficients to {COEFFS_PATH}:")
    print(f"   log_odds = {coeffs['intercept']:.3f} "
          f"+ ({coeffs['distance']:.3f})*distance "
          f"+ ({coeffs['angle']:.3f})*angle")
    print("\nsoccer_analytics.py will load these automatically on next run.")


if __name__ == "__main__":
    main()
