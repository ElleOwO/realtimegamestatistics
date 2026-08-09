# RTGS Post-Game Veo Analysis

The primary workstation workflow is now a persistent post-game service. Copy a
Veo follow-cam MP4 into `data/inbox/`, start the API with
`python backend/postgame_server.py`, and open `http://localhost:3000/matches`.
The operator supplies teams, score, period boundaries, attacking directions,
and confirms the USask kit cluster before the single-GPU worker starts.

Runtime data is kept under `data/` (gitignored): imported source videos,
preflight images, annotated H.264 proxies, diagnostics, and the WAL-mode SQLite
database. Reports survive restarts; a job interrupted by a restart can be run
again from the beginning. No missing metric is represented as a measured zero,
and mock dashboard values are enabled only with
`NEXT_PUBLIC_DEMO_MODE=true`.

```bash
# Backend API and one-job GPU worker (Python 3.11/3.12)
export ROBOFLOW_API_KEY="..."
python backend/postgame_server.py

# Frontend
cd frontend
npm install --legacy-peer-deps
npm run dev

# Lightweight backend validation
pytest -q backend/tests
```

The original live camera runtime remains available with
`python backend/soccer_analytics.py`. It publishes the versioned live coaching
payload on `ws://localhost:8001/ws`; the dashboard can control match phase,
clock, score, direction, tactical targets, and shot review over the same socket.

The live release reports quality-gated team metrics: provisional/reviewed
shots and xG with a shot map, true final-third and penalty-area crossings,
time-weighted possession and field tilt, phase-split team shape, transitions,
and experimental pressure episodes. Missing observations are reported as
unavailable instead of measured zeroes.

```bash
# Live camera or local video (Python 3.11/3.12)
export QT_QPA_PLATFORM=xcb
export ROBOFLOW_API_KEY="..."
python backend/soccer_analytics.py --port 8001
python backend/soccer_analytics.py --video PATH --port 8001
python backend/soccer_analytics.py --stream 'http://PHONE_IP:PORT/VIDEO_PATH' --port 8001

# Optional Linux iPhone-stream/X11 Docker profile. Post-game remains on :8000.
IPHONE_STREAM_URL='rtsp://192.168.1.25:8554/live' \
  docker compose --profile live up --build
```

## Live game capture from an iPhone

The iPhone and analytics computer must be on the same network. The native
iPhone Camera app does not publish a network video URL, so use an iOS camera
app that exposes either an **RTSP** feed or an **HTTP/MJPEG** feed. Copy the
complete URL shown by that app and start the live runtime with `--stream`:

```bash
export QT_QPA_PLATFORM=xcb
export ROBOFLOW_API_KEY="..."
python backend/soccer_analytics.py \
  --stream 'rtsp://192.168.1.25:8554/live' \
  --port 8001
```

An HTTP/MJPEG URL works the same way; use the actual video endpoint shown by
the phone app, not merely its browser control-page address. Keep the iPhone
plugged in, disable auto-lock, mount it high near midfield in landscape, and
use the rear wide camera with the whole pitch visible. A dedicated local Wi-Fi
network is strongly preferable to venue Wi-Fi.

Start the frontend in another terminal:

```bash
cd frontend
npm install --legacy-peer-deps
NEXT_PUBLIC_WS_URL=ws://localhost:8001/ws npm run dev
```

Then open `http://localhost:3000`. The backend calibrates the two kit clusters
first and then publishes player/ball positions and derived match analytics to
the dashboard over WebSocket. If the dashboard is opened on another device,
replace `localhost` in `NEXT_PUBLIC_WS_URL` with the analytics computer's LAN
IP and allow TCP port 8001 through its firewall.

Use `--video` for files, YouTube, and other hosted video pages. Use `--stream`
for a direct iPhone/live-camera feed; this prevents the camera URL from being
treated as a YouTube-style page by `yt-dlp`.

### Run the iPhone feed with Docker

For DroidCam over USB, the DroidCam Linux client runs on the host and publishes
the phone camera through its v4l2loopback device. Connect and unlock the iPhone,
tap **Trust** if prompted, open DroidCam on both devices, select the iPhone in
the Linux client, and click **Activate**. Confirm the virtual camera path with:

```bash
v4l2-ctl --list-devices
```

Create the gitignored `.env` file in the repository root. Do not set
`IPHONE_STREAM_URL` for USB:

```dotenv
ROBOFLOW_API_KEY=your_key
LIVE_VIDEO_DEVICE=/dev/video2
```

On the Linux analytics computer, permit the live container to open its OpenCV
preview windows, then start the stack:

```bash
xhost +local:docker
docker compose --profile live up --build
```

Open `http://localhost:3000`. Compose exposes the live analytics WebSocket on
`localhost:8001`, which is already baked into the frontend image. Keep the
DroidCam host client active for the entire match.

Use `docker compose --profile live logs -f live-analytics` to confirm that the
feed opens and team calibration completes. When finished:

```bash
docker compose --profile live down
xhost -local:docker
```

To use a direct network stream instead, set `IPHONE_STREAM_URL`; it takes
priority over the video device. If that URL contains a username or password,
keep it in `.env`; the backend redacts credentials from its own source-status
messages.

# Annotation Progress Tracker Spreadsheet:
https://docs.google.com/spreadsheets/d/11xHF4m3nwdMaOhU0I3eYglJJ1yJcFLXcJ8fwwgNiOz0/edit?gid=0#gid=0

# GitHub Desktop
1. Install GitHub Desktop

2. Click “File → Clone Repository” and paste your repo link:
https://github.com/ElleOwO/realtimegamestatistics.git

3. It’ll download the repo to your computer.

4. When you finish annotating, drag your new files into your local annotations folder.

5. Open GitHub Desktop:

  - You’ll see your changes listed.

  - Add a short description like "Added annotations for frames 0–99."

  - Click Commit to main → Push origin.

  - That sends your changes to GitHub for everyone to see.

# RTGS Team Setup Guide

How to set up Git and work only in your own folder
1. Clone the Repository
  1. Go to your GitHub Desktop or Terminal.
  2. Clone the project using this link:
   https://github.com/ElleOwO/realtimegamestatistics.git
  3. Navigate into the folder after it downloads.
2. Create Your Personal Folder
    Inside the 'annotations' folder, make your own folder using your name.
    Example:
    annotations/lyinmya/
    annotations/alex/
    annotations/priya/
3. Set Up Your Local .gitignore
  1. Open the project folder.
  2. Create a file named '.gitignore' (if it doesn't exist).
  3. Add the following lines (replace 'yourname' with your folder name):
   annotations/*
   !annotations/yourname/**
  This makes Git track only your folder and ignore others.
4. Keep Your .gitignore Local
  -- Do not commit your .gitignore file!
  This should stay on your computer only.
  If you accidentally added it, run:
   git rm --cached .gitignore
5. Verify It Works
  Run 'git status' in your terminal.
  You should only see your files (e.g., annotations/lyinmya/...).
  If you see other people's folders, check your .gitignore lines again.
6. Optional: Local Exclude File
  You can also edit '.git/info/exclude' and add the same lines there.
  This works like .gitignore but is always local (never synced).
# When pushing commits:
1. Instead of git add *, each member should do:

```
git add annotations/theirname/

Or even more specific:

git add annotations/lyinmya/images/
git add annotations/lyinmya/labels/
```
That’s the safest way. It only stages their folder.

# GitHub Actions behind the scenes
Whenever someone uploads new annotations:

GitHub Actions runs a workflow automatically (merge-upload.yml).

It merges everyone’s data and uploads it to Roboflow.

You don’t have to do anything special — it happens automatically in the background.

# Real-Time Game Statistics

This GitHub repository automates dataset management for our **real-time soccer game analytics system**.  
It merges image annotations from multiple team members, compresses the data, and uploads the latest version to **Roboflow** automatically using **GitHub Actions**.

---

## Repository Structure

```
/realtimegamestatistics/
├── annotations/                     # Each member stores their own labeled data here
│   ├── member1/
│   │   ├── images/                  # Labeled images (e.g., frame1.png)
│   │   └── labels/                  # Corresponding YOLO annotation files (e.g., frame1.txt)
│   ├── member2/
│   └── ...
│
├── merged_dataset/                  # Auto-created by merge_and_upload.py after merging all member folders
│   ├── images/                      # Combined images from all annotators
│   └── labels/                      # Combined label files
│
├── merge_and_upload.py              # Python script to merge and upload datasets to Roboflow
│                                    # 1. Collects all member data
│                                    # 2. Merges into merged_dataset/
│                                    # 3. Uploads each image individually to Roboflow
│
├── .github/
│   └── workflows/
│       └── merge-upload.yml         # GitHub Action that runs the script automatically
│                                    # - Installs dependencies
│                                    # - Merges annotations
│                                    # - Uploads images to Roboflow
│
└── .gitignore                       # Prevents system files, venvs, and merged outputs from being committed

```

---

## How It Works

### Data Collection
Each team member annotates soccer game images locally (using Roboflow, LabelImg, or another tool) and saves their work under:

```
annotations/member_name/images/
annotations/member_name/labels/
```
Each label file must share the same base name as its image.

---

### Scripts

#### `merge_and_upload.py`
How it works

Merges all member annotation folders (annotations/memberX/images and annotations/memberX/labels) into merged_dataset/.

Uploads every image inside merged_dataset/images to Roboflow individually.

Each image upload will automatically include its YOLO-style label if the file names match (e.g., frame123.png and frame123.txt).

The script automatically uses your **private API key** from GitHub Secrets and your project’s **WORKSPACE** and **PROJECT** slugs from Roboflow.

---

#### `.github/workflows/merge-upload.yml`
This GitHub Actions workflow runs the script automatically whenever new annotations are pushed.

It:
- Checks out the repo.
- Installs dependencies (`roboflow`).
- Runs `merge_and_upload.py` using your secret Roboflow key.

**Trigger conditions:**
- Any new commits in `annotations/**`
- Manual trigger via the GitHub Actions tab
