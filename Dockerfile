# Use a slim Python 3.12 image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies if any (none required for now)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy local code into the container
COPY . .

# Install dependencies using pip (or uv if preferred, but pip is standard in Dockerfiles)
RUN pip install --no-cache-dir .

# Set PYTHONPATH to the root to allow relative imports
ENV PYTHONPATH=/app

# Default command (can be overridden in docker-compose)
ENTRYPOINT ["python", "src/main.py"]
