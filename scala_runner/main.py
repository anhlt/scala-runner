import os
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Scala-Runner API",
    description="Wrap scala-cli Docker invocation in an HTTP service",
    version="0.1.0",
)

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