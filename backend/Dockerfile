# ============================================================================
# USask Soccer Analytics Backend
# Production Dockerfile for GCP Compute Engine with NVIDIA L4 GPU
# ============================================================================
#
# BASE IMAGE CHOICE:
#   nvidia/cuda:12.1.1-runtime-ubuntu22.04
#     - Includes CUDA 12.1 + cuDNN
#     - Optimized for inference (not training)
#     - ~2.5 GB (smaller than -devel which includes build tools)
#
# BUILD STAGES:
#   Stage 1 (builder): Install dependencies, cache Python packages
#   Stage 2 (runtime): Copy only what's needed for running the service

FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04 AS builder

# Install system dependencies for OpenCV, ffmpeg, build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential \
    libopencv-dev \
    python3-opencv \
    ffmpeg \
    wget \
    git \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Use Python 3.11
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build dependencies
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install Python packages
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ============================================================================
# Runtime Stage
# ============================================================================
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# System dependencies (minimal, runtime only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    libopencv-core4.5d \
    libopencv-imgproc4.5d \
    libopencv-highgui4.5d \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgomp1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user (security best practice)
RUN useradd -m -u 1000 soccer && \
    mkdir -p /app && \
    chown -R soccer:soccer /app

WORKDIR /app

# Copy backend code
COPY backend/soccer_analytics.py /app/


# Set permissions
RUN chown -R soccer:soccer /app
USER soccer

# Health check (optional, for orchestrators like Docker Compose/Kubernetes)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Expose WebSocket port
EXPOSE 8000

# Run the analytics engine
CMD ["python", "soccer_analytics.py"]
