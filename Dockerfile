# WealthMitra — single-service image: FastAPI serves the built React SPA + /api + /ws.
#
# Stage 1 builds the frontend static bundle (Node), stage 2 runs the backend
# (Python) and serves that bundle. One image, one process, one public URL —
# matches the local dev shape (`make build && make run`) so there are no
# deploy-only surprises.

# ---- Stage 1: frontend build -------------------------------------------------
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend runtime -------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY data/synthetic data/synthetic
COPY --from=frontend-builder /app/frontend/dist frontend/dist

# Non-root: Render (and most PaaS runtimes) run containers as root by default,
# but there's no reason this process needs it.
RUN useradd --create-home --uid 1000 wealthmitra \
    && chown -R wealthmitra:wealthmitra /app
USER wealthmitra

# PYTHONPATH=backend mirrors the Makefile (`export PYTHONPATH := backend`),
# so the same `app.main:app` import path works locally and in the container.
ENV PYTHONPATH=backend \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Render (and most PaaS hosts) inject $PORT at runtime and route traffic to
# it; ${PORT:-8000} keeps `docker run -p 8000:8000 <image>` working locally
# with no env vars set.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
