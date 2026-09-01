# Production Dockerfile for Vibe Vault
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure upload directories exist
RUN mkdir -p uploads/songs uploads/covers uploads/profiles

EXPOSE 5000

# Run with Gunicorn WSGI production server
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --threads 2 --timeout 120 app:app"]
