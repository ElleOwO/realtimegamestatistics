"""Gemini-based tactical insight helpers."""

from __future__ import annotations

from typing import Dict, Optional

from ..constants import ENABLE_GEMINI, GOOGLE_CLOUD_LOCATION, GOOGLE_CLOUD_PROJECT
from .player_registry import PlayerStats

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    genai_types = None
    GEMINI_AVAILABLE = False

GEMINI_MODEL = "gemini-2.5-flash"


def init_gemini():
    """Connect to Vertex AI Gemini client. Returns None if unavailable."""
    if not ENABLE_GEMINI:
        print("ℹ️  Gemini disabled via ENABLE_GEMINI=false")
        return None
    if not GEMINI_AVAILABLE:
        print("⚠️  google-genai not installed — AI insights disabled.")
        return None
    try:
        client = genai.Client(vertexai=True, project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION)
        print(f"✅ Gemini client ready  ({GOOGLE_CLOUD_PROJECT} / {GEMINI_MODEL})")
        return client
    except Exception as exc:
        print(f"⚠️  Gemini init failed: {exc}")
        return None


def build_gemini_prompt(
    match_min: float,
    possession_pct: float,
    xg_team0: float,
    xg_team1: float,
    transition_spd: float,
    hull_area: float,
    def_line_height: float,
    width_of_attack: float,
    zone_t0: dict,
    zone_t1: dict,
    registry: Dict[int, PlayerStats],
    recent_events: list,
) -> str:
    """Build the tactical prompt sent to Gemini."""
    usask = sorted([s for s in registry.values() if s.team_id == 0], key=lambda s: s.distance_km, reverse=True)[:4]
    player_lines = "\n".join([f"  #{s.tracker_id}: {s.distance_km:.2f}km | {s.sprint_count} sprints | zone: {max(s.zone_frames, key=s.zone_frames.get)}" for s in usask]) or "  No data yet"
    events_lines = "\n".join([f"  {e.get('minute','?')}' {e.get('type','')} — {e.get('description','')}" for e in recent_events[-5:]]) or "  None yet"

    return f"""You are an AI assistant for the USask Huskies women's soccer coaching staff.
Based on the live match data below, give ONE specific tactical recommendation.
Be direct — the coach is on the sideline and has 20 seconds to read this.
Do NOT restate numbers. Focus on the CAUSE and SOLUTION. Maximum 3 sentences.

MATCH MINUTE: {match_min:.0f}
Possession: USask {possession_pct:.0f}% / Opponent {100 - possession_pct:.0f}%
xG: USask {xg_team0:.2f} vs Opponent {xg_team1:.2f}
Def line: {def_line_height:.0f}m | Atk width: {width_of_attack:.0f}m
Transition: {transition_spd:.1f}s | Def shape area: {hull_area:.0f}m²

ZONE PRESSURE:
USask — def third: {zone_t0.get('defensive_third_count',0)} players | atk third: {zone_t0.get('attacking_third_count',0)} players
Opponent — in USask def third: {zone_t1.get('defensive_third_count',0)} | dominant zone: {zone_t1.get('dominant_zone','?')}

USask TOP PLAYERS:
{player_lines}

RECENT EVENTS:
{events_lines}"""


async def request_gemini_insight(prompt: str, match_min: float, gemini_client) -> Optional[dict]:
    """Call Gemini asynchronously and wrap the result as an insight payload."""
    if gemini_client is None or genai_types is None:
        return None
    try:
        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=150,
                system_instruction=(
                    "You are a concise soccer tactical analyst. "
                    "Respond in plain sentences only, no bullet points. "
                    "Always end with one specific actionable instruction."
                ),
            ),
        )
        return {"type": "ai_narrative", "title": f"AI Tactical Insight ({match_min:.0f}')", "body": response.text.strip(), "minute": round(match_min, 1)}
    except Exception as exc:
        print(f"⚠️  Gemini call failed at {match_min:.0f}': {exc}")
        return None
