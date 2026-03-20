# Local Run Guide

This project is set up for local development without NVIDIA/GPU containers by default.

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
python soccer_analytics.py
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

## 4) Use GPU backend later (GCP/Compute Engine)

When you are ready for NVIDIA runtime, override the backend Dockerfile:

```bash
BACKEND_DOCKERFILE=backend/Dockerfile docker compose up --build
```

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

- Running backend locally (non-NVIDIA) is recommended for your current phase.
- Save GPU deployment tuning for GCP phase to avoid large local image pulls.
- Keep `ENABLE_GEMINI=false` unless you have GCP credentials configured and want AI narratives.
