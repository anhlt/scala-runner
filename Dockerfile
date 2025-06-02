# Dockerfile

# 1. Base image
FROM python:3.11-slim

# 2. Install system deps + Docker CLI
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      docker.io \
 && rm -rf /var/lib/apt/lists/*

# 3. Set working dir
WORKDIR /app

# 4. Copy & install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy app & install it
COPY setup.py .
COPY scala_runner/ ./scala_runner/
RUN pip install --no-cache-dir .

# 6. Expose port and default cmd
EXPOSE 80
CMD ["uvicorn", "scala_runner.main:app", "--host", "0.0.0.0", "--port", "80"]