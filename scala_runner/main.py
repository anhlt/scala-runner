import os
import subprocess
import tempfile
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
    code: Optional[str] = None
    file_path: Optional[str] = None
    scala_version: str = SCALA_VERSION
    dependency: str = DEFAULT_DEP


@app.post("/run", summary="Run Scala script via scala-cli in Docker")
@limiter.limit(RATE_LIMIT)  # applies per-client-IP
async def run_scala(request: Request, payload: RunRequest):
    # 1) Write code to temp file if provided
    input_path = payload.file_path
    temp_created = False
    if payload.code:
        fd, input_path = tempfile.mkstemp(suffix=".worksheet.sc", text=True)
        os.write(fd, payload.code.encode())
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
        "--scala", payload.scala_version,
        "--dependency", payload.dependency,
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
