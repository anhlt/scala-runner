import os
import subprocess
import tempfile
import asyncio
import json
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
# slowapi imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
# logger
import logging
from .workspace_manager import WorkspaceManager
from .sbt_runner import SBTRunner
from .bash_session_manager import BashSessionManager

# Import all routers
from .routers import (
    workspace_router,
    git_router,
    files_router,
    search_router,
    sbt_router,
    bash_router,
    utils_router
)
from .routers import workspace, git, files, search, sbt, bash

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
RATE_LIMIT = os.getenv("RATE_LIMIT", "1000/minute")  # e.g. "5/minute"
BASE_DIR = os.getenv("BASE_DIR", os.path.expanduser("~/scala-runner-workspaces"))

#
# 2. Create limiter and managers
#
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT]
)

# Initialize managers
workspace_manager = WorkspaceManager(base_dir=BASE_DIR)
sbt_runner = SBTRunner()
bash_session_manager = BashSessionManager(workspace_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    # Startup
    if bash_session_manager.auto_cleanup_enabled:
        result = await bash_session_manager.start_auto_cleanup()
        logger.info(f"Application startup: Auto-cleanup task {result.get('status', 'unknown')}")
    
    yield
    
    # Shutdown
    result = await bash_session_manager.stop_auto_cleanup()
    logger.info(f"Application shutdown: Auto-cleanup task {result.get('status', 'unknown')}")
    
    # Close any remaining sessions
    cleanup_result = await bash_session_manager.cleanup_inactive_sessions()
    logger.info(f"Application shutdown: Cleaned up {cleanup_result.get('cleaned_sessions', 0)} sessions")

app = FastAPI(
    title="Scala SBT Workspace API",
    description="Manage SBT workspaces and run SBT commands via Docker",
    version="0.2.0",
    lifespan=lifespan,
)
# register the exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize managers in routers
workspace.set_managers(workspace_manager)
git.set_managers(workspace_manager)
files.set_managers(workspace_manager)
search.set_managers(workspace_manager)
sbt.set_managers(workspace_manager, sbt_runner)
bash.set_managers(bash_session_manager)

# Include all routers
app.include_router(workspace_router)
app.include_router(git_router)
app.include_router(files_router)
app.include_router(search_router)
app.include_router(sbt_router)
app.include_router(bash_router, include_in_schema=False)  # Exclude bash APIs from OpenAPI schema
app.include_router(utils_router)

# Update the openapi endpoint in utils router to return actual schema
@app.get(
    "/openapi",
    summary="Alias for the OpenAPI schema",
    include_in_schema=False
)
async def openapi_schema():
    """Return the OpenAPI schema (alias for /openapi.json). No rate-limit applied."""
    return JSONResponse(app.openapi()) 