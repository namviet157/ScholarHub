# ScholarHub FastAPI backend (RAG, semantic search, document proxy)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Cache BGE weights in the image so the API does not download on first request
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5')"

# API only needs the server package and vector_service (loaded via importlib from repo root)
COPY server/ ./server/
COPY processing/vector_service.py ./processing/vector_service.py

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
  CMD python -c "import os, urllib.request; p=os.environ.get('PORT','8000'); urllib.request.urlopen(f'http://127.0.0.1:{p}/health', timeout=5)"

CMD ["sh", "-c", "exec uvicorn server.scholarhub_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
