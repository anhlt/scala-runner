import os
import subprocess
import tempfile
import asyncio
import json
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from typing import List, Optional  # Added List for handling multiple dependencies
# slowapi imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
# logger
import logging
from .output_process import clean_subprocess_output

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
RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")  # e.g. "5/minute"
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
    file_extension: str

    @field_validator("file_extension")
    def clean_and_check_extension(cls, v: str) -> str:
        # strip any leading dot and normalize
        ext = v.lstrip(".").lower()
        allowed = {"sc", "scala"}
        if ext not in allowed:
            raise ValueError(f"file_extension must be one of {allowed}")
        return ext


@app.post("/run", summary="Run Scala script via scala-cli in Docker")
@limiter.limit(RATE_LIMIT)  # applies per-client-IP
async def run_scala(
    request: Request,
    payload: RunRequest,
    background_tasks: BackgroundTasks,     # ← added
):
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
            "-v", "/home/scala/.cache:/home/scala/.cache",
            "virtuslab/scala-cli:latest",
            "run", f"/tmp/{filename}",
            "--scala", payload.scala_version,
            "-q"
        ]
        for dep in payload.dependencies:
            docker_cmd.extend(["--dependency", dep])

        # 3) Log the exact command we're about to run
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
            logger.error("Docker command timed out after 60s: %s", " ".join(docker_cmd))
            process.kill()
            _, stderr = await process.communicate()
            logger.error("Stderr after timeout: %s", stderr.decode(errors="ignore"))
            raise HTTPException(500, "Docker run timed out")

        out_text = stdout.decode(errors="ignore")
        err_text = clean_subprocess_output(stderr.decode(errors="ignore"))

        background_tasks.add_task(
                _cleanup_scala_cache,
            )
        # 5) Handle exit code
        if process.returncode == 0:
            logger.info("Docker run succeeded. Stdout: %s", out_text)
            # Schedule background cache cleanup

            return JSONResponse({"status": "success", "output": out_text})
        else:
            logger.error("Docker run failed (code=%d).", process.returncode)

            error_response = json.dumps({"status": "error", "error": err_text})
            raise HTTPException(500, f"{error_response}")

    finally:
        # 6) Always clean up
        try:
            os.unlink(input_path)
        except OSError:
            logger.warning("Failed to delete temp file: %s", input_path)


# 7) Background cleanup helper
async def _cleanup_scala_cache():
    """
    Runs `scala-cli clean` inside the Docker image to purge caches.
    """
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", "/home/scala/.cache:/home/scala/.cache",
        "virtuslab/scala-cli:latest",
        "clean"
    ]

    proc = await asyncio.create_subprocess_exec(
        *docker_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        logger.warning(
            "Background scala-cli clean failed (code=%d): %s",
            proc.returncode,
            err.decode(errors="ignore")
        )


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


@app.get("/ping", summary="Health check endpoint")
async def ping():
    """
    Simple health check endpoint that returns 'pong' to confirm the API is running.
    """
    return {"status": "pong"}