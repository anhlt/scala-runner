"""
Bash session endpoints.
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
    prefix="/bash",
    tags=["bash"],
    responses={404: {"description": "Not found"}},
)

# Import managers - these will be injected via dependency injection
bash_session_manager = None

def set_managers(bash_mgr):
    """Set the bash session manager instance"""
    global bash_session_manager
    bash_session_manager = bash_mgr


# Pydantic models
class CreateBashSessionRequest(BaseModel):
    workspace_name: str

    @field_validator("workspace_name")
    def validate_workspace_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Workspace name cannot be empty")
        return v.strip()


class ExecuteBashCommandRequest(BaseModel):
    session_id: str
    command: str
    timeout: Optional[int] = 30

    @field_validator("session_id")
    def validate_session_id(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Session ID cannot be empty")
        return v.strip()

    @field_validator("command")
    def validate_command(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Command cannot be empty")
        return v.strip()


class CloseBashSessionRequest(BaseModel):
    session_id: str

    @field_validator("session_id") 
    def validate_session_id(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Session ID cannot be empty")
        return v.strip()


class ConfigureCleanupRequest(BaseModel):
    session_timeout: Optional[int] = None
    cleanup_interval: Optional[int] = None
    auto_cleanup_enabled: Optional[bool] = None

    @field_validator("session_timeout")
    def validate_session_timeout(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Session timeout must be positive")
        return v

    @field_validator("cleanup_interval")
    def validate_cleanup_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Cleanup interval must be positive")
        return v


# Bash Session Endpoints
@router.post("/sessions", summary="Create a new bash session")
@limiter.limit(RATE_LIMIT)
async def create_bash_session(request: Request, payload: CreateBashSessionRequest):
    """Create a new bash session for a workspace"""
    try:
        result = await bash_session_manager.create_session(payload.workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error creating bash session: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/execute", summary="Execute command in bash session")
@limiter.limit(RATE_LIMIT)
async def execute_bash_command(request: Request, payload: ExecuteBashCommandRequest):
    """Execute a command in an existing bash session"""
    try:
        result = await bash_session_manager.execute_command(
            payload.session_id, 
            payload.command, 
            payload.timeout or 30
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error executing bash command: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.delete("/sessions/{session_id}", summary="Close a bash session")
@limiter.limit(RATE_LIMIT)
async def close_bash_session(request: Request, session_id: str):
    """Close a specific bash session"""
    try:
        result = await bash_session_manager.close_session(session_id)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error closing bash session: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.delete("/workspaces/{workspace_name}/sessions", summary="Close all bash sessions for workspace")
@limiter.limit(RATE_LIMIT)
async def close_workspace_bash_sessions(request: Request, workspace_name: str):
    """Close all bash sessions for a workspace"""
    try:
        result = await bash_session_manager.close_workspace_sessions(workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error closing workspace bash sessions: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/sessions", summary="List all bash sessions")
@limiter.limit(RATE_LIMIT)
async def list_bash_sessions(request: Request, workspace_name: Optional[str] = None):
    """List all bash sessions or sessions for a specific workspace"""
    try:
        result = bash_session_manager.list_sessions(workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error listing bash sessions: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/sessions/{session_id}", summary="Get bash session info")
@limiter.limit(RATE_LIMIT)
async def get_bash_session_info(request: Request, session_id: str):
    """Get detailed information about a specific bash session"""
    try:
        result = bash_session_manager.get_session_info(session_id)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error getting bash session info: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/cleanup", summary="Clean up inactive bash sessions")
@limiter.limit(RATE_LIMIT)
async def cleanup_bash_sessions(request: Request):
    """Clean up inactive or timed-out bash sessions"""
    try:
        result = await bash_session_manager.cleanup_inactive_sessions()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error cleaning up bash sessions: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/auto-cleanup/start", summary="Start automatic cleanup of inactive bash sessions")
@limiter.limit(RATE_LIMIT)
async def start_auto_cleanup(request: Request):
    """Start the automatic cleanup background task for inactive bash sessions"""
    try:
        result = await bash_session_manager.start_auto_cleanup()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error starting auto-cleanup: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.post("/auto-cleanup/stop", summary="Stop automatic cleanup of inactive bash sessions")
@limiter.limit(RATE_LIMIT)
async def stop_auto_cleanup(request: Request):
    """Stop the automatic cleanup background task for inactive bash sessions"""
    try:
        result = await bash_session_manager.stop_auto_cleanup()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error stopping auto-cleanup: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.put("/auto-cleanup/configure", summary="Configure automatic cleanup settings")
@limiter.limit(RATE_LIMIT)
async def configure_auto_cleanup(request: Request, payload: ConfigureCleanupRequest):
    """Configure automatic cleanup settings (timeout, interval, enabled)"""
    try:
        result = bash_session_manager.configure_cleanup(
            session_timeout=payload.session_timeout,
            cleanup_interval=payload.cleanup_interval,
            auto_cleanup_enabled=payload.auto_cleanup_enabled
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error configuring auto-cleanup: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/auto-cleanup/stats", summary="Get automatic cleanup statistics")
@limiter.limit(RATE_LIMIT)
async def get_auto_cleanup_stats(request: Request):
    """Get automatic cleanup configuration and statistics"""
    try:
        result = bash_session_manager.get_cleanup_stats()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error getting auto-cleanup stats: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}") 