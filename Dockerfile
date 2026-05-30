# Backend image for Railway (FastAPI + the shared angar_* packages).
# The frontend deploys separately on Vercel — see DEPLOY.md.
FROM python:3.12-slim

# Faster, quieter Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the project (backend + angar_schema + angar_extraction) and its
# runtime deps from pyproject. Copy the whole repo first — .dockerignore keeps
# out the frontend, local state, secrets, and caches.
COPY . .
RUN pip install --upgrade pip && pip install .

# Railway provides $PORT at runtime; default to 8000 for local `docker run`.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
