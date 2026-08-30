# Testing RTGS without a GPU or full match video

The normal development loop is video-free. It replays compact pitch
observations through the same `AnalyticsEngine`, payload builder, WebSocket
commands, post-game adapter, persistence, reporting, and dashboard contracts
used by the GPU runtime.

## One-command local replay

```bash
./rtgs dev
```

On first use this creates `.rtgs/local/venv`, installs lightweight API/test
dependencies and frontend packages, then starts the post-game API on port 8000,
CPU replay socket on 8001, and Next.js on 3000.

Open `/`, select **1H**, and inspect the live report. The default 0.1× playback
makes the short fixture last about 50 seconds; `./rtgs dev --speed 1` runs it in
real time. Operator phase, clock, score, names, reset, and review commands use
the real WebSocket contract.

Open `/matches` and select **Run replay fixture** to exercise the post-game
queue, SQLite persistence, events, report, and review without uploading video
or loading Roboflow. Ctrl+C deletes temporary state; `--keep-data` retains it.

## Fixtures and recordings

`backend/fixtures/standard.json` is the committed data-only scenario.
`backend/replay_scenarios.py` expands its ball paths, control, quality change,
and expectations into canonical 105×68 m observations. Do not store images,
base64 frames, model objects, or player names in fixtures.

Expensive CV runs write schema-versioned JSONL recordings at the vision →
analytics boundary. Live cloud runs write `live-observations.jsonl.gz`; each
post-game run writes `matches/<id>/observations.jsonl.gz`. Sanitize a captured
recording and turn it into a regression fixture when a real match exposes a bug.

## Free validation

```bash
./rtgs test
```

This runs backend tests, frontend unit tests, the Next.js production build and
typecheck, Python syntax checks, and shell syntax checks. It does not import the
Roboflow runtime, need an API key, read video, or start a GPU. CI runs the same
contracts before building the RunPod image.

## Paid GPU smoke test

Use a short private H.264 clip that shows both kits, field markings, normal
camera motion, a final-third sequence, and ideally a shot. Keep it outside Git.

```bash
./rtgs cloud configure
./rtgs cloud test --clip /secure/path/rtgs-smoke.mp4
```

The command uses the image tagged with the current Git commit, creates a
disposable RunPod, uploads the clip through an authenticated test endpoint,
runs post-game preflight/analysis, then publishes the same clip through the real
RTMPS relay and validates live payloads. It downloads compact artifacts under
`downloads/` and terminates the pod in a `finally` block on pass or failure.

The live gate requires at least 8 unique processed payload frames per second;
post-game requires a completed report and 0.70 calibration coverage by default.
A manifest can override setup and coverage:

```json
{
  "minimum_calibration_coverage": 0.75,
  "setup": {
    "home_team": "USask",
    "away_team": "Opponent",
    "home_score": 0,
    "away_score": 0,
    "usask_side": "home",
    "periods": [{"number": 1, "start_ms": 0, "end_ms": 45000}],
    "directions": {"1": "right"},
    "usask_cluster": 0
  }
}
```

Run `./rtgs cloud soak --video FILE` before a release or match day. `--keep` is
opt-in; if used, the operator owns termination and should run
`./rtgs cloud cleanup` afterward.

## Storage policies

`RTGS_ARTIFACT_POLICY` controls post-game retention:

- `compact` (default) keeps report data and compressed observations, removing
  source/proxy/annotated video and calibration caches after report persistence;
- `source` keeps the source and calibration data but discards generated video;
- `full` keeps all media and diagnostics.

Live mode keeps a run summary, compressed observations, and short event clips.
`./rtgs clean` is a dry-run audit; `./rtgs clean --confirm` moves legacy caches
to `data/.trash` instead of permanently deleting them.
