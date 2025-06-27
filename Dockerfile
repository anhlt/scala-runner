FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scala_runner/ ./scala_runner/
COPY setup.py ./
COPY entrypoint.sh ./

# Create directories for workspaces and cache
RUN mkdir -p /tmp/workspaces /tmp/sbt-cache /tmp/ivy-cache /tmp/coursier-cache /tmp/search_index

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV BASE_DIR=/tmp
ENV RATE_LIMIT=10/minute

# Use entrypoint script
ENTRYPOINT ["./entrypoint.sh"]