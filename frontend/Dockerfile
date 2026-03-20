# ============================================================================
# USask Soccer Dashboard Frontend
# Production Dockerfile for Vercel or standalone deployment
# ============================================================================
#
# BUILD STAGES:
#   Stage 1 (builder): Node.js environment, install deps, build Vite bundle
#   Stage 2 (runtime): Nginx to serve the static dist/ folder

FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency files
COPY frontend/package.json frontend/package-lock.json* frontend/pnpm-lock.yaml* ./

# Install dependencies
# Try pnpm first (faster), then npm ci when lockfile exists, else npm install
RUN npm install -g pnpm && \
        if [ -f pnpm-lock.yaml ]; then \
            pnpm install; \
        elif [ -f package-lock.json ]; then \
            npm ci; \
        else \
            npm install; \
        fi

# Copy source code
COPY frontend/. .

# Build Vite bundle
# This generates dist/ with optimized JS/CSS/HTML bundles
RUN npm run build

# ============================================================================
# Runtime Stage
# ============================================================================
FROM nginx:alpine

# Copy Vite build output to Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: serve SPA index.html, enable GZIP, set CORS headers
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 80;
    server_name _;
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1000;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # SPA routing: all non-file routes → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Static assets (long cache)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # CORS headers for WebSocket (if needed)
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type' always;
}
EOF

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
