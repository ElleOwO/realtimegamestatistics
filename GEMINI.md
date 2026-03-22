# USask Soccer Analytics Engine — Project Context

Welcome to the **USask Soccer Analytics Engine**. This project provides real-time game statistics and tactical insights for the University of Saskatchewan Women's Soccer team.

---

## 🏗️ Project Overview

The system captures live video (from a Veo camera or webcam), processes it using computer vision models (YOLO), and streams real-time tactical data to a Next.js dashboard via WebSockets.

### Core Services:
- **Analytics Engine (Backend)**: A FastAPI-based Python server that performs object detection, player tracking, xG (Expected Goals) calculation, and tactical analysis.
- **Coach Dashboard (Frontend)**: A Next.js application that displays live stats, heatmaps, and AI-generated tactical insights.
- **Data Pipeline**: A custom workflow that merges annotations from multiple team members and automates dataset uploads to Roboflow.
- **Media Relay**: MediaMTX handles RTSP/RTMP streams from professional cameras (e.g., Veo Cam 3).

---

## 🛠️ Tech Stack

- **Computer Vision**: `ultralytics` (YOLOv8/v11), `supervision`, `opencv-python`.
- **Backend**: Python 3.10+, `FastAPI`, `WebSockets`, `XGBoost` (for xG model), `Redis`.
- **Frontend**: `Next.js 15+`, `React 19`, `TypeScript`, `Tailwind CSS`, `shadcn/ui`, `Recharts`.
- **AI/LLM**: Google Cloud Vertex AI (Gemini 2.5 Flash) for tactical narrative generation.
- **Infrastructure**: `Docker`, `Docker Compose`, `MediaMTX`.
- **Data Management**: `Roboflow API`, GitHub Actions.

---

## 🚀 Getting Started

### 📦 Prerequisites
- Docker & Docker Compose
- Node.js & npm (for local frontend development)
- Python 3.10+ (for local backend development)
- Roboflow API Key

### 🐳 Running with Docker (Recommended)
```bash
# Start all services (analytics, dashboard, redis, mediamtx)
docker-compose up --build
```
The dashboard will be available at `http://localhost`.

### 🐍 Manual Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Set environment variables
export ROBOFLOW_API_KEY="your_key"
export VIDEO_SOURCE="webcam" # "webcam" for dev, "rtsp" for production
export WEBCAM_INDEX=0

python soccer_analytics.py
```

### ⚛️ Manual Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The dashboard will be available at `http://localhost:3000`.

---

## 📁 Repository Structure

- `backend/`: The heart of the project. Contains `soccer_analytics.py` (main logic), `requirements.txt`, and Docker configuration.
- `frontend/`: Next.js application. Main components are in `src/app/components`.
- `annotations/`: Folder for team members to store their labeled data. Each member should have their own subdirectory.
- `merge_and_upload.py`: Script to combine all annotations and upload them to Roboflow.
- `.github/workflows/`: Automation for dataset merging and uploading.
- `mediamtx.yml`: Configuration for the media server.
- `football_ai.ipynb`: Research and development notebook for AI models.

---

## 📋 Development Conventions

### 📊 Dataset Workflow
Team members should follow this workflow for annotations:
1. Create a personal folder in `annotations/yourname/`.
2. Add a local `.gitignore` to only track your own folder:
   ```
   annotations/*
   !annotations/yourname/**
   ```
3. Commit and push your changes. GitHub Actions will handle the rest.

### 🧪 Testing & Validation
- **Backend**: Use the `VIDEO_SOURCE="webcam"` or a sample `.mp4` file for testing CV logic.
- **Frontend**: Verify WebSocket connection to the backend (`ws://localhost:8000/ws`).
- **xG Model**: Trained on StatsBomb Open Data (women's football events).

---

## 💡 Key Architectural Insights

- **Real-time Tracking**: Uses ByteTrack (via `supervision`) to maintain player IDs across frames.
- **Pitch Calibration**: Uses field detection models to transform image coordinates into pitch coordinates (105m x 68m).
- **AI Insights**: Every 2 minutes, the backend sends a match summary to Gemini and receives a tactical narrative to display on the dashboard.
- **Multi-Client Support**: Redis is used as a pub/sub broker to allow multiple dashboard instances to receive synced data.
