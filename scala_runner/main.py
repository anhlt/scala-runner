import os
import subprocess
import tempfile
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from dotenv import load_dotenv
from typing import List, Optional  # Added List for handling multiple dependencies
# slowapi imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
# logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# log formatting
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Configure the logger to output to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
#
# 1. Load env
#
load_dotenv()  # will look for .env in CWD
RATE_LIMIT = os.getenv("RATE_LIMIT", "5/minute")  # e.g. "5/minute"
SCALA_VERSION = os.getenv("DEFAULT_SCALA_VERSION", "3.6.4")
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
    code: str
    scala_version: str
    dependencies: List[str] = [DEFAULT_DEP]
    code: str
    file_extension: str

    @validator("file_extension")
    def clean_and_check_extension(cls, v: str) -> str:
        # strip any leading dot and normalize
        ext = v.lstrip(".").lower()
        allowed = {"sc", "scala"}
        if ext not in allowed:
            raise ValueError(f"file_extension must be one of {allowed}")
        return ext


@app.post("/run", summary="Run Scala script via scala-cli in Docker")
@limiter.limit(RATE_LIMIT)  # applies per-client-IP
async def run_scala(request: Request, payload: RunRequest):
    # 1) Write the user code to a temp file
    fd, input_path = tempfile.mkstemp(suffix=f".{payload.file_extension}", text=True)
    try:
        os.write(fd, payload.code.encode())
        os.close(fd)

        # 2) Build the Docker command
        workdir = os.path.abspath(os.path.dirname(input_path))
        filename = os.path.basename(input_path)
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{workdir}:/tmp/",
            "-v", "/tmp/scala-cache:/home/scala/.cache",
            "virtuslab/scala-cli:latest",
            "run", f"/tmp/{filename}",
            "--scala", payload.scala_version,
        ]
        for dep in payload.dependencies:
            docker_cmd.extend(["--dependency", dep])

        # 3) Log the exact command we’re about to run
        logger.info("Running Docker command: %s", " ".join(docker_cmd))

        # 4) Spawn & await the Docker process with a timeout
        try:
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            logger.error("Docker command timed out after 60s: %s",
                         " ".join(docker_cmd))
            # best effort kill if still running
            process.kill()
            _, stderr = await process.communicate()
            logger.error("Stderr after timeout: %s",
                         stderr.decode(errors="ignore"))
            raise HTTPException(500, "Docker run timed out")

        out_text = stdout.decode(errors="ignore")
        err_text = stderr.decode(errors="ignore")

        # 5) Handle exit code
        if process.returncode == 0:
            logger.info("Docker run succeeded. Stdout: %s", out_text)
            return JSONResponse({"status": "success", "output": out_text})
        else:
            logger.error("Docker run failed (code=%d).", process.returncode)
            logger.error("Stdout: %s", out_text)
            logger.error("Stderr: %s", err_text)
            # Also log the code and tmp file for post-mortem
            logger.error("Input code:\n%s", payload.code)
            logger.error("Temp file path: %s", input_path)
            with open(input_path, 'r') as f:
                logger.error("Temp file content:\n%s", f.read())
            raise HTTPException(500, f"Error running Docker: {err_text}")

    finally:
        # 6) Always clean up
        try:
            os.unlink(input_path)
        except OSError:
            logger.warning("Failed to delete temp file: %s", input_path)


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
