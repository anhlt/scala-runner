import os
import subprocess
import tempfile
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

# slowapi imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

#
# 1. Load env
#
load_dotenv()  # will look for .env in CWD
RATE_LIMIT = os.getenv("RATE_LIMIT", "5/minute")  # e.g. "5/minute"
SCALA_VERSION = os.getenv("DEFAULT_SCALA_VERSION", "2.13")
DEFAULT_DEP = os.getenv(
    "DEFAULT_DEPENDENCY",
    "org.typelevel::cats-core:2.12.0"
)

#
# 2. Create limiter
#
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT]
)

app = FastAPI(
    title="Scala-Runner API",
    description="Wrap scala-cli Docker invocation in an HTTP service",
    version="0.1.1",
)
# register the exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class RunRequest(BaseModel):
    code: str  # Made code required; removed file_path
    scala_version: str = SCALA_VERSION
    dependency: str = DEFAULT_DEP


@app.post("/run", summary="Run Scala script via scala-cli in Docker")
@limiter.limit(RATE_LIMIT)  # applies per-client-IP
async def run_scala(request: Request, payload: RunRequest):
    # Always create a temp file from the provided code
    fd, input_path = tempfile.mkstemp(suffix=".worksheet.sc", text=True)
    try:
        os.write(fd, payload.code.encode())
        os.close(fd)

        # Build Docker command
        workdir = os.path.abspath(os.path.dirname(input_path))
        filename = os.path.basename(input_path)
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{workdir}:/mnt",
            "virtuslab/scala-cli:latest",
            "run", f"/mnt/{filename}",
            "--scala", payload.scala_version,
            "--dependency", payload.dependency,
        ]

        # Execute
        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return JSONResponse({"status": "success", "output": stdout.decode()})
        else:
            raise HTTPException(500, f"Error running Docker: {stderr.decode()}")
    finally:
        os.unlink(input_path)  # Always delete the temp file


@app.get(
    "/openapi",
    summary="Alias for the OpenAPI schema",
    include_in_schema=False
)
async def openapi_schema():
    """
    Return the OpenAPI schema (alias for /openapi.json).
    No rate-limit applied.
    """
    return JSONResponse(app.openapi())


# Add this after the other route definitions, e.g., after the '/openapi' route
@app.get("/ping", summary="Health check endpoint")
async def ping():
    """
    Simple health check endpoint that returns 'pong' to confirm the API is running.
    """
    return {"status": "pong"}