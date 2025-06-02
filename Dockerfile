FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      docker.io \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Install FastAPI, uvicorn, etc.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy code & entrypoint

# 3) Copy app & install it
COPY setup.py .
COPY scala_runner/ ./scala_runner/
RUN pip install --no-cache-dir .

# 4) Use our script as ENTRYPOINT
COPY entrypoint.sh .
ENTRYPOINT ["./entrypoint.sh"]