#!/usr/bin/env bash
# ============================================================
# Quantum MCP Relayer — Manual Deploy Script
# Usage: ./scripts/deploy.sh [server] [registry]
#
# Example:
#   ./scripts/deploy.sh deploy@prod.example.com ghcr.io/agentagency
# ============================================================

set -euo pipefail

# --------------- Configuration ---------------
DEPLOY_TARGET="${1:?Usage: $0 <user@host> [registry]}"
REGISTRY="${2:-ghcr.io/agentagency}"
IMAGE_NAME="quantum-mcp-relayer"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/quantum-mcp-relayer}"
GIT_SHA="$(git rev-parse --short HEAD)"
TAG="${GIT_SHA}"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"

# --------------- Helpers ---------------
info()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m[deploy]\033[0m %s\n' "$*"; }
fail()  { printf '\033[1;31m[deploy]\033[0m %s\n' "$*" >&2; exit 1; }

# --------------- Step 1: Build ---------------
info "Building Docker image: ${FULL_IMAGE}:${TAG}"
docker build -t "${FULL_IMAGE}:${TAG}" -t "${FULL_IMAGE}:latest" .

# --------------- Step 2: Push ---------------
info "Pushing image to registry..."
docker push "${FULL_IMAGE}:${TAG}"
docker push "${FULL_IMAGE}:latest"

# --------------- Step 3: Deploy via SSH ---------------
info "Deploying to ${DEPLOY_TARGET}..."
ssh -o StrictHostKeyChecking=accept-new "${DEPLOY_TARGET}" bash -s <<REMOTE
set -euo pipefail
cd "${DEPLOY_PATH}"

# Pull the freshly-pushed image
docker compose pull api

# Bring up with production overrides
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --remove-orphans

# Clean up old images
docker image prune -f
REMOTE

# --------------- Step 4: Health Check ---------------
info "Running post-deploy health check..."
for i in $(seq 1 12); do
    STATUS=$(ssh "${DEPLOY_TARGET}" "curl -sf '${HEALTH_URL}'" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || true)
    if [ "${STATUS}" = "ok" ]; then
        ok "Health check passed (attempt ${i}/12). Deployment complete."
        exit 0
    fi
    info "Attempt ${i}/12 — waiting 10s..."
    sleep 10
done

fail "Health check failed after 2 minutes. Investigate immediately."
