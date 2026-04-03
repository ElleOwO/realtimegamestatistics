# Google Compute Engine Deployment Guide

Deploy the full stack (backend + frontend + redis + mediamtx) on a single GCE VM using Docker Compose.

---

## 1. Create the GCE VM

### Console (cloud.google.com)

1. Navigate to **Compute Engine > VM instances > Create Instance**
2. Configure:

| Setting | Value |
|---|---|
| **Name** | `rtgs-analytics` |
| **Region/Zone** | Closest to your users (e.g., `us-central1-a`) |
| **Machine type** | `e2-standard-4` (4 vCPU, 16 GB RAM) |
| **Boot disk** | Ubuntu 22.04 LTS, 50 GB SSD |
| **Firewall** | Check **Allow HTTP traffic** and **Allow HTTPS traffic** |

3. Click **Create**

### Firewall Rules

Create custom firewall rules for the app's ports:

```bash
# In GCP Console: VPC Network > Firewall > Create Firewall Rule
# Or via gcloud CLI:

gcloud compute firewall-rules create rtgs-app-ports \
    --allow tcp:3000,tcp:8000,tcp:1935,tcp:8554,tcp:8888,udp:8554,udp:8888 \
    --source-ranges 0.0.0.0/0 \
    --target-tags rtgs-server \
    --description "RTGS app ports"
```

Then add the `rtgs-server` network tag to your VM instance.

---

## 2. SSH into the VM

```bash
gcloud compute ssh rtgs-analytics --zone=YOUR_ZONE
```

Or use the **SSH** button in the GCP Console.

---

## 3. Install Docker & Docker Compose

```bash
# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER

# Verify
docker --version
docker compose version

# Log out and back in for group changes to take effect
exit
# Then SSH back in
```

---

## 4. Clone the Repository

```bash
git clone https://github.com/ElleOwO/realtimegamestatistics.git
cd realtimegamestatistics
```

---

## 5. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cat > .env << 'EOF'
# ── Video source ─────────────────────────────────────────────
# "webcam" for testing, "rtsp" for game day with MediaMTX
VIDEO_SOURCE=webcam
WEBCAM_INDEX=0
RTSP_URL=rtsp://mediamtx:8554/live

# ── Roboflow ─────────────────────────────────────────────────
ROBOFLOW_API_KEY=your_roboflow_api_key_here

# ── Model IDs ────────────────────────────────────────────────
PLAYER_MODEL_ID=spen-rtgs-oc4ez/4
FIELD_MODEL_ID=football-field-detection-f07vi/14
XG_MODEL_PATH=xg_model_womens.ubj

# ── Frontend WebSocket URL ───────────────────────────────────
# REPLACE with your VM's external IP
NEXT_PUBLIC_WS_URL=ws://YOUR_VM_EXTERNAL_IP:8000/ws

# ── Redis ────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379
EOF
```

> **Important**: Replace `YOUR_VM_EXTERNAL_IP` with your VM's external IP address. Find it in the GCP Console under VM instances, or run:
> ```bash
> curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google"
> ```

---

## 6. Deploy

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### What this does

- Builds the backend (CPU-only YOLO + FastAPI) and frontend (Next.js) images
- Starts all 4 services: `analytics`, `frontend`, `redis`, `mediamtx`
- Applies production overrides (resource limits, no dev volumes, structured logging)

---

## 7. Verify Deployment

### Check all services are running

```bash
docker compose ps
```

Expected output: all 4 services showing `Up` status.

### Test backend API

```bash
curl http://localhost:8000/health
```

### Test frontend

Open a browser and navigate to:

```
http://YOUR_VM_EXTERNAL_IP:3000
```

### Check logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f analytics
docker compose logs -f frontend
```

---

## 8. (Optional) Auto-start on Boot

Create a systemd service to start the app automatically:

```bash
sudo tee /etc/systemd/system/rtgs.service > /dev/null << 'EOF'
[Unit]
Description=RTGS Soccer Analytics Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/YOUR_USERNAME/realtimegamestatistics
ExecStart=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
ExecStop=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml down
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
EOF

# Replace YOUR_USERNAME with your actual username (run `whoami` to check)
sudo systemctl daemon-reload
sudo systemctl enable rtgs.service
sudo systemctl start rtgs.service
```

---

## Troubleshooting

### Frontend can't connect to WebSocket

- Verify `NEXT_PUBLIC_WS_URL` in `.env` uses the correct external IP
- Rebuild frontend after changing env vars: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build frontend`

### Backend OOM / crashes

- The `e2-standard-4` (16 GB RAM) is the minimum. YOLO + OpenCV + XGBoost are memory-heavy.
- Check logs: `docker compose logs analytics`
- Consider upgrading to `e2-standard-8` (32 GB) or adding a GPU instance.

### Mediamtx not receiving RTSP stream

- Ensure port 1935 (RTMP) is open for your Veo camera to push to
- Check mediamtx logs: `docker compose logs mediamtx`
- Verify the camera is configured to push RTMP to `rtmp://YOUR_VM_EXTERNAL_IP:1935/live`

### Rebuild after code changes

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## Cost Estimate (as of 2026)

| Resource | Monthly Cost (approx.) |
|---|---|
| `e2-standard-4` (4 vCPU, 16 GB) | ~$97/month |
| 50 GB SSD | ~$8.50/month |
| Egress (first 100 GB) | Free |
| **Total** | **~$105/month** |

With GPU (`n1-standard-4` + NVIDIA T4): ~$350+/month
