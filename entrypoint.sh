#!/bin/bash

# Exit on any error
set -e

echo "Starting Scala SBT Workspace API..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Docker is not available. Please ensure Docker is installed and running."
    exit 1
fi

# Pre-pull the SBT Docker image to avoid delays during first run
echo "Pulling SBT Docker image..."
docker pull sbtscala/scala-sbt:eclipse-temurin-jammy-17.0.8.1_1.9.6_3.3.1 || {
    echo "Warning: Failed to pull SBT Docker image. Commands may fail later."
}

# Create necessary directories
mkdir -p /tmp/workspaces
mkdir -p /tmp/sbt-cache
mkdir -p /tmp/ivy-cache
mkdir -p /tmp/coursier-cache
mkdir -p /tmp/search_index

# Set permissions
chmod 755 /tmp/workspaces /tmp/sbt-cache /tmp/ivy-cache /tmp/coursier-cache /tmp/search_index

echo "Directories created and permissions set."

# Start the FastAPI server
echo "Starting FastAPI server on 0.0.0.0:8000..."
exec uvicorn scala_runner.main:app --host 0.0.0.0 --port 8000