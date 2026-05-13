FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# libgomp1 is required by onnxruntime (fastembed + flashrank backends).
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps in their own layer so code changes don't bust the cache.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code and the parsed-markdown cache that the data-status endpoint
# reads. data/raw_filings/ and data/chroma_db/ are excluded via .dockerignore.
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY index.html ./
COPY data/ ./data/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
