"""
Git operations endpoints.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional, List
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
    prefix="/git",
    tags=["git"],
    responses={404: {"description": "Not found"}},
)

# Import managers - these will be injected via dependency injection
workspace_manager = None

def set_managers(ws_manager):
    """Set the workspace manager instance"""
    global workspace_manager
    workspace_manager = ws_manager


# Pydantic models
class GitCheckoutRequest(BaseModel):
    workspace_name: str
    branch_name: str
    create_new: Optional[bool] = False

    @field_validator("branch_name")
    def validate_branch_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Branch name cannot be empty")
        return v.strip()


class GitAddRequest(BaseModel):
    workspace_name: str
    file_paths: Optional[List[str]] = None


class GitCommitRequest(BaseModel):
    workspace_name: str
    message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None

    @field_validator("message")
    def validate_message(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Commit message cannot be empty")
        return v.strip()


class GitPushPullRequest(BaseModel):
    workspace_name: str
    remote_name: Optional[str] = "origin"
    branch_name: Optional[str] = None


# Git Operations Endpoints
@router.post("/checkout", summary="Checkout Git branch")
@limiter.limit(RATE_LIMIT)
async def git_checkout_branch(request: Request, payload: GitCheckoutRequest):
    """Checkout a Git branch (optionally create new branch)"""
    try:
        result = await workspace_manager.git_checkout_branch(
            payload.workspace_name,
            payload.branch_name,
            payload.create_new or False
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git checkout: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/add", summary="Add files to Git staging area")
@limiter.limit(RATE_LIMIT)
async def git_add_files(request: Request, payload: GitAddRequest):
    """Add files to Git staging area"""
    try:
        result = await workspace_manager.git_add_files(
            payload.workspace_name,
            payload.file_paths or []
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git add: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/commit", summary="Commit staged changes")
@limiter.limit(RATE_LIMIT)
async def git_commit_changes(request: Request, payload: GitCommitRequest):
    """Commit staged changes to Git repository"""
    try:
        result = await workspace_manager.git_commit(
            payload.workspace_name,
            payload.message,
            payload.author_name or "",
            payload.author_email or ""
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git commit: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/push", summary="Push changes to remote repository")
@limiter.limit(RATE_LIMIT)
async def git_push_changes(request: Request, payload: GitPushPullRequest):
    """Push changes to remote Git repository"""
    try:
        result = await workspace_manager.git_push(
            payload.workspace_name,
            payload.remote_name or "origin",
            payload.branch_name or ""
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git push: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/pull", summary="Pull changes from remote repository")
@limiter.limit(RATE_LIMIT)
async def git_pull_changes(request: Request, payload: GitPushPullRequest):
    """Pull changes from remote Git repository"""
    try:
        result = await workspace_manager.git_pull(
            payload.workspace_name,
            payload.remote_name or "origin",
            payload.branch_name or ""
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git pull: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/status/{workspace_name}", summary="Get Git status")
@limiter.limit(RATE_LIMIT)
async def git_get_status(request: Request, workspace_name: str):
    """Get Git status of a workspace"""
    try:
        result = await workspace_manager.git_status(workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error getting Git status: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/log/{workspace_name}", summary="Get Git commit history")
@limiter.limit(RATE_LIMIT)
async def git_get_log(request: Request, workspace_name: str, limit: int = 10):
    """Get Git commit history of a workspace"""
    try:
        result = await workspace_manager.git_log(workspace_name, limit)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error getting Git log: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}") 