# Local Run Guide

This project is set up for local development without NVIDIA/GPU containers by default.

## Project Structure

The repository is split into a few clear layers so it behaves like the reference repos:

```text
realtimegamestatistics/
├── backend/                 # FastAPI analytics engine and model/runtime code
│   ├── main.py              # Backend entrypoint used by Docker and local runs
│   ├── constants.py         # Shared runtime configuration
│   ├── analytics/           # Match metrics, registry state, tactical summaries
│   ├── api/                 # Payload assembly and websocket transport
│   ├── keypoint_detection/  # Pitch calibration and keypoint helpers
│   ├── pipelines/           # Orchestration layer for detection/tracking flow
│   ├── player_detection/    # Detection model helpers and training stubs
│   ├── player_tracking/     # ByteTrack-related helpers
│   ├── player_clustering/   # Team assignment / embeddings
│   ├── player_annotations/  # Visualization helpers
│   ├── tactical_analysis/   # Homography and pitch transforms
│   ├── xg_model/            # xG model utilities and feature prep
│   ├── models/              # Exported model artifacts and cacheable weights
│   └── training_notebooks/  # Notebook exports / offline training refs
├── frontend/                # Vite + React dashboard
│   ├── src/app/pages/       # Route-level screens
│   ├── src/app/components/  # Reusable UI pieces
│   ├── src/app/hooks/       # Live WebSocket data hook
│   └── src/app/layouts/     # Shared app shell
├── notebooks/               # Colab / experiment notebooks
├── annotations/             # Human-labeled image sets per annotator
└── docs/                    # Setup and usage docs
```

Workflow split:

- Notebooks are for training and validation only.
- The backend runs the live camera or RTSP pipeline and publishes JSON.
- The frontend listens to the backend websocket and renders the dashboard.

For the notebook specifically, section 1-6 should stay in the training notebook, while section 7 onward is a good candidate for a second demo/integration notebook.

## 1) Frontend only (fastest)

Run this when you only want to work on UI.

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite (usually `http://localhost:5173`).

If you want the frontend to attempt WebSocket backend connection:

```bash
export VITE_WS_URL=ws://localhost:8000/ws
npm run dev
```

## 2) Backend locally on your machine (no Docker)

Use this for backend development without GPU images.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Set required environment values (minimum Roboflow key):

```bash
export ROBOFLOW_API_KEY="your_key"
export VIDEO_SOURCE="webcam"
export WEBCAM_INDEX=0
```

Run backend:

```bash
python main.py
```

Backend WebSocket endpoint:

- `ws://localhost:8000/ws`

## 3) Full stack with Docker Compose (CPU default)

Compose now defaults to the CPU backend Dockerfile.

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost`
- Backend WS: `ws://localhost:8000/ws`
- Redis: `localhost:6379`
- MediaMTX: `rtsp://localhost:8554/live`

Veo camera note:

- Veo Cam 2/3 do not expose direct RTSP for local playback.
- Configure Veo Live custom destination with RTMP to your MediaMTX ingest:
	- Example ingest URL: `rtmp://<HOST_OR_VM_IP>:1935/live`
- Analytics should then consume MediaMTX RTSP output:
	- `rtsp://localhost:8554/live` (host) or `rtsp://mediamtx:8554/live` (inside compose)

### Veo live setup checklist

1. In Veo Live, add a Custom destination.
2. Set destination URL to your MediaMTX RTMP ingest, for example:
	- `rtmp://YOUR_PUBLIC_IP:1935/live`
3. Start MediaMTX before going live:
	- `docker compose up -d mediamtx`
4. Set analytics source to RTSP output from MediaMTX (not Veo directly):
	- `export VIDEO_SOURCE=rtsp`
	- `export RTSP_URL=rtsp://mediamtx:8554/live` (inside compose)
	- `export RTSP_URL=rtsp://localhost:8554/live` (host run)
5. Start analytics service, then check logs to confirm frames are being read.

## 4) Backend layout

The backend now follows a more modular structure so it can evolve toward the
reference repos' style:

- `backend/main.py` is the container and local entrypoint
- `backend/constants.py` centralizes runtime configuration
- `backend/api/` owns websocket transport and dashboard payload shaping
- `backend/analytics/` owns match metrics, registry state, and tactical summaries
- `backend/xg_model/` owns xG loading and feature computation
- `backend/player_detection/` will hold detection helpers and training stubs
- `backend/player_tracking/`, `backend/player_clustering/`, and
	`backend/player_annotations/` will hold tracking, team assignment, and
	visualization modules
- `backend/keypoint_detection/` and `backend/tactical_analysis/` will hold
	pitch calibration and coordinate transform code
- `backend/pipelines/` will coordinate the end-to-end video flow

## 5) Environment variables

Copy and edit root env template:

```bash
cp .env.example .env
```

Important keys:

- `ROBOFLOW_API_KEY`
- `VIDEO_SOURCE` (`webcam` or `rtsp`)
- `RTSP_URL` (MediaMTX output stream, not a direct Veo URL)
- `VITE_WS_URL`
- `PLAYER_MODEL_ID`
- `FIELD_MODEL_ID`
- `ENABLE_GEMINI` (`false` by default for local runs)

## Notes

- Running backend locally (CPU) is recommended for your current phase.
- Keep `ENABLE_GEMINI=false` unless you have GCP credentials configured and want AI narratives.
