# ============================================================
# Quantum MCP Relayer — Production Multi-Stage Dockerfile
# ============================================================

# ---------- Stage 1: Build dependencies ----------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY pyproject.toml .

# Install production deps only (no dev extras) into a virtual env
# that we can copy cleanly into the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache .

# ---------- Stage 2: Slim runtime ----------
FROM python:3.12-slim AS runtime

# Security: run as non-root
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy pre-built virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy application source and static assets
COPY src/ src/
COPY pyproject.toml .
COPY static/ static/

# Install the project itself (editable so src package resolves)
RUN uv pip install --no-cache -e . 2>/dev/null || pip install --no-cache-dir -e .

# Own everything by appuser
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check — hit the /health endpoint every 30s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info"]
