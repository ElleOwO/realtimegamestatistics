# USask Soccer Analytics Engine — Project Context (Updated March 2026)

Welcome to the **USask Soccer Analytics Engine**. This system provides real-time tracking, tactical insights, and automated dataset management for the University of Saskatchewan Women's Soccer team.

---

## 🏗️ Project Overview

The project is a full-stack real-time analytics suite composed of:
1.  **Analytics Engine (Backend)**: A FastAPI server that processes live video streams (RTSP/Webcam) using YOLOv8/v11. It performs player tracking, tactical analysis (possession, defensive lines, etc.), and xG calculation.
2.  **Coach Dashboard (Frontend)**: A Next.js dashboard built for real-time visualization of tactical data, heatmaps, and AI-generated insights.
3.  **Data Pipeline**: An automated system for merging distributed image annotations and uploading them to Roboflow via GitHub Actions.
4.  **AI Insights**: Integration with Google Cloud Vertex AI (Gemini 2.5 Flash) for periodic tactical narrative generation.

---

## 🛠️ Tech Stack

### Backend
- **Core Logic**: Python 3.11, FastAPI, WebSockets.
- **ML/CV**: `ultralytics` (YOLO), `supervision` (Tracking), `inference`, `roboflow`.
- **Analytics**: `XGBoost` (xG model), `scipy` (Convex Hull for compactness), `numpy`.
- **Message Broker**: `Redis` (Pub/Sub).

### Frontend
- **Framework**: **Next.js 15.1.0** (Stable), **React 18.3.1**.
- **Styling**: Tailwind CSS 4, shadcn/ui.
- **Visualization**: Recharts, Lucide Icons.
- **State/Data**: Native WebSockets for live feed.

### Infrastructure & DevOps
- **Containerization**: Docker & Docker Compose.
- **Media Server**: `MediaMTX` (RTSP/RTMP relay).
- **CI/CD**: GitHub Actions (`merge-upload.yml`).
- **Cloud**: Optimized for GCP Compute Engine with NVIDIA L4 GPU.

---

## 🚀 Getting Started

### 📦 Prerequisites
- Docker & Docker Compose.
- Node.js (for local frontend dev).
- Roboflow API Key.

### 🐳 Running via Docker (CPU Default)
```bash
# Start all services (Frontend, Backend, Redis, MediaMTX)
docker compose up --build
```
- **Frontend**: `http://localhost`
- **Backend API/WS**: `ws://localhost:8000/ws`

### ⚛️ Frontend Local Development
```bash
cd frontend
npm install
npm run dev
```

### 🐍 Backend Local Development (No Docker)
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ROBOFLOW_API_KEY="your_key"
export VIDEO_SOURCE="webcam"
python soccer_analytics.py
```

---

## 📁 Repository Structure

- `backend/`: Python source, `requirements.txt`, and dual Dockerfiles (`Dockerfile` for GPU, `Dockerfile.cpu` for CPU).
- `frontend/`: Next.js source. Renamed to `rtgs-dashboard`.
- `annotations/`: Member-specific labeling folders.
- `merge_and_upload.py`: Data pipeline script that merges member annotations and handles Roboflow API uploads.
- `.github/workflows/`: Automation for the data pipeline.
- `mediamtx.yml`: Media server configuration for Veo camera integration.
- `football_ai.ipynb`: R&D notebook for model experimentation.

---

## 📋 Development Conventions & Workflows

### 📊 Dataset Pipeline
- **Member Folders**: Each member uses `annotations/member_name/`.
- **Merging**: `merge_and_upload.py` combines images and labels, renaming files with unique UUID suffixes to prevent collisions.
- **Automation**: Any push to `annotations/**` triggers a GitHub Action that runs the merge and uploads to the Roboflow project `rtgs-omuwo`.

### 🛡️ Development History & Troubleshooting
- **Frontend Stability**: The project was originally using Next.js 16/React 19, which caused "Turbopack Panic" errors and peer dependency conflicts with UI libraries. It has been **surgically downgraded** to **Next.js 15.1.0** and **React 18.3.1** to ensure a stable development environment.
- **Package Conflicts**: Always use `npm install --legacy-peer-deps` if conflicts arise with legacy UI components.
- **GPU Usage**: To run with GPU support locally, set `BACKEND_DOCKERFILE=backend/Dockerfile` in your environment or compose command.

---

## 💡 Key Architectural Features

- **ByteTrack**: Maintains persistent player IDs for distance and sprint tracking.
- **Field Calibration**: Transforms 2D image coordinates into meters for accurate speed and distance metrics.
- **Dual Inference**: Supports both local YOLO inference and Roboflow Hosted Inference.
- **Tactical Narrative**: Every 2 minutes, a JSON match summary is sent to Gemini 2.5 Flash to generate coach-friendly insights.
