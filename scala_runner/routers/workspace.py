"""
Workspace management endpoints.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
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
    prefix="/workspaces",
    tags=["workspace"],
    responses={404: {"description": "Not found"}},
)

# Import managers - these will be injected via dependency injection
workspace_manager = None

def set_managers(ws_manager):
    """Set the workspace manager instance"""
    global workspace_manager
    workspace_manager = ws_manager


# Pydantic models
class CreateWorkspaceRequest(BaseModel):
    name: str

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Workspace name cannot be empty")
        return v.strip()


class CloneWorkspaceRequest(BaseModel):
    name: str
    git_url: str
    branch: Optional[str] = None

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Workspace name cannot be empty")
        return v.strip()

    @field_validator("git_url")
    def validate_git_url(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Git URL cannot be empty")
        return v.strip()


# Workspace Management Endpoints
@router.post("", summary="Create a new workspace")
@limiter.limit(RATE_LIMIT)
async def create_workspace(request: Request, payload: CreateWorkspaceRequest):
    """Create a new SBT workspace with basic project structure"""
    try:
        result = await workspace_manager.create_workspace(payload.name)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("", summary="List all workspaces")
@limiter.limit(RATE_LIMIT)
async def list_workspaces(request: Request):
    """List all available workspaces"""
    try:
        workspaces = workspace_manager.list_workspaces()
        return JSONResponse({"status": "success", "data": workspaces})
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.delete("/{workspace_name}", summary="Delete a workspace")
@limiter.limit(RATE_LIMIT)
async def delete_workspace(request: Request, workspace_name: str):
    """Delete a workspace and all its files"""
    try:
        result = await workspace_manager.delete_workspace(workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/{workspace_name}/tree", summary="Get workspace file tree")
@limiter.limit(RATE_LIMIT)
async def get_workspace_tree(request: Request, workspace_name: str):
    """Get the file tree structure of a workspace (like 'tree' command)"""
    try:
        result = await workspace_manager.get_file_tree(workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error getting workspace tree: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/clone", summary="Clone workspace from Git repository")
@limiter.limit(RATE_LIMIT)
async def clone_workspace_from_git(request: Request, payload: CloneWorkspaceRequest):
    """Clone a Git repository into a new workspace"""
    try:
        result = await workspace_manager.clone_workspace_from_git(
            payload.name, 
            payload.git_url, 
            payload.branch
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error cloning workspace: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/{workspace_name}/git-info", summary="Get Git repository information")
@limiter.limit(RATE_LIMIT)
async def get_workspace_git_info(request: Request, workspace_name: str):
    """Get Git repository information for a workspace"""
    try:
        result = await workspace_manager.get_workspace_git_info(workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error getting Git info: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}") 