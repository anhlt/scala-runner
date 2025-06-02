import os
from collections import defaultdict, deque
from time import time
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Rate limiting settings (requests per minute)
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))
WINDOW_SIZE = 60  # in seconds

# In-memory store for tracking request timestamps per client IP
_clients = defaultdict(deque)

app = FastAPI(
    title="Scala-Runner API",
    description="Wrap scala-cli Docker invocation in an HTTP service with rate limiting",
    version="0.1.1",
)

# Rate limit middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    now = time()
    queue = _clients[client_ip]

    # Remove timestamps outside the window
    while queue and queue[0] <= now - WINDOW_SIZE:
        queue.popleft()

    if len(queue) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {RATE_LIMIT} requests per {WINDOW_SIZE} seconds"},
        )

    queue.append(now)
    response = await call_next(request)
    return response

class RunRequest(BaseModel):
    code: str | None = None
    file_path: str | None = None
    scala_version: str = "2.13"
    dependency: str = "org.typelevel::cats-core:2.12.0"

@app.post("/run", summary="Run Scala script via scala-cli in Docker")
async def run_scala(request: RunRequest):
    if not request.code and not request.file_path:
        raise HTTPException(400, "Must provide 'code' or 'file_path' in the request body.")

    # 1) Write code to temp file if provided
    input_path = request.file_path
    temp_created = False
    if request.code:
        fd, input_path = tempfile.mkstemp(suffix=".worksheet.sc", text=True)
        os.write(fd, request.code.encode())
        os.close(fd)
        temp_created = True

    # 2) Verify file existence
    if not os.path.exists(input_path):
        raise HTTPException(400, f"File not found: {input_path}")

    # 3) Build Docker command
    workdir = os.path.abspath(os.path.dirname(input_path))
    filename = os.path.basename(input_path)
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{workdir}:/mnt",
        "virtuslab/scala-cli:latest",
        "run", f"/mnt/{filename}",
        "--scala", request.scala_version,
        "--dependency", request.dependency,
    ]

    # 4) Execute
    try:
        proc = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return JSONResponse({"status": "success", "output": proc.stdout})
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, e.stderr or "Unknown error running Docker")
    finally:
        if temp_created:
            os.unlink(input_path)
