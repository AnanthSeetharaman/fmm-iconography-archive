# ==============================================================================
# Five Metal Masonry (FMM) Iconography Archive
# Universal Dockerfile for Google Cloud Run & Hugging Face Spaces (Free Tier)
# ==============================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code, assets, and seed data
COPY . .

# Ensure read/write access for non-root container runtimes (e.g. Hugging Face Spaces UID 1000)
RUN chmod -R 777 /app

# Expose standard port
EXPOSE 8000 8080 7860

# Container Health Check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT}/api/health || exit 1

# Launch application
CMD ["python", "run_app.py"]
