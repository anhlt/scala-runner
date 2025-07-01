"""
SBT command endpoints.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging
import os

# Get rate limit from environment
RATE_LIMIT = os.getenv("RATE_LIMIT", "1000/minute")

# Create limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT]
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sbt",
    tags=["sbt"],
    responses={404: {"description": "Not found"}},
)

# Import managers - these will be injected via dependency injection
workspace_manager = None
sbt_runner = None

def set_managers(ws_manager, sbt_r):
    """Set the manager instances"""
    global workspace_manager, sbt_runner
    workspace_manager = ws_manager
    sbt_runner = sbt_r


# Pydantic models
class SBTCommandRequest(BaseModel):
    workspace_name: str
    command: str
    timeout: Optional[int] = None
    main_class: Optional[str] = None
    test_name: Optional[str] = None


class SBTProjectRequest(BaseModel):
    workspace_name: str
    timeout: Optional[int] = None
    main_class: Optional[str] = None
    test_name: Optional[str] = None


# SBT Command Endpoints
@router.post("/run", summary="Run SBT command")
@limiter.limit(RATE_LIMIT)
async def run_sbt_command(request: Request, payload: SBTCommandRequest):
    """Execute an SBT command in a workspace"""
    try:
        workspace_path = workspace_manager.get_workspace_path(payload.workspace_name)
        
        if not workspace_path.exists():
            raise HTTPException(404, f"Workspace '{payload.workspace_name}' not found")
        
        result = await sbt_runner.run_sbt_command(
            workspace_path, 
            payload.command, 
            payload.timeout
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error running SBT command: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/compile", summary="Compile SBT project")
@limiter.limit(RATE_LIMIT)
async def compile_project(request: Request, payload: dict):
    """Compile the SBT project in a workspace"""
    workspace_name = payload.get("workspace_name")
    if not workspace_name:
        raise HTTPException(400, "workspace_name is required")
    
    try:
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        if not workspace_path.exists():
            raise HTTPException(404, f"Workspace '{workspace_name}' not found")
        
        result = await sbt_runner.compile_project(workspace_path)
        return JSONResponse({"status": "success", "data": result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error compiling project: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/run-project", summary="Run SBT project")
@limiter.limit(RATE_LIMIT)
async def run_project(request: Request, payload: SBTProjectRequest):
    """Run the main class of the SBT project"""
    try:
        workspace_path = workspace_manager.get_workspace_path(payload.workspace_name)
        result = await sbt_runner.run_project(workspace_path, payload.main_class)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error running project: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/test", summary="Run SBT tests")
@limiter.limit(RATE_LIMIT)
async def test_project(request: Request, payload: SBTProjectRequest):
    """Run tests in the SBT project"""
    try:
        workspace_path = workspace_manager.get_workspace_path(payload.workspace_name)
        result = await sbt_runner.test_project(workspace_path, payload.test_name)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/clean", summary="Clean SBT project")
@limiter.limit(RATE_LIMIT)
async def clean_project(request: Request, payload: dict):
    """Clean the SBT project build artifacts"""
    workspace_name = payload.get("workspace_name")
    if not workspace_name:
        raise HTTPException(400, "workspace_name is required")
    
    try:
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        if not workspace_path.exists():
            raise HTTPException(404, f"Workspace '{workspace_name}' not found")
        
        result = await sbt_runner.clean_project(workspace_path)
        return JSONResponse({"status": "success", "data": result})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning project: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/project-info/{workspace_name}", summary="Get SBT project info")
@limiter.limit(RATE_LIMIT)
async def get_project_info(request: Request, workspace_name: str):
    """Get information about the SBT project structure"""
    try:
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        result = await sbt_runner.get_project_info(workspace_path)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error getting project info: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}") 