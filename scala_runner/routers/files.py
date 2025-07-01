"""
File management endpoints.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
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
    prefix="/files",
    tags=["files"],
    responses={404: {"description": "Not found"}},
)

# Import managers - these will be injected via dependency injection
workspace_manager = None

def set_managers(ws_manager):
    """Set the workspace manager instance"""
    global workspace_manager
    workspace_manager = ws_manager


# Pydantic models
class CreateFileRequest(BaseModel):
    workspace_name: str
    file_path: str
    content: str


class UpdateFileRequest(BaseModel):
    workspace_name: str
    file_path: str
    content: str


class PatchFileRequest(BaseModel):
    workspace_name: str
    patch: str
    
    @field_validator("patch")
    def validate_patch(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Patch content cannot be empty")
        return v.strip()


# File Management Endpoints
@router.post("", summary="Create a new file")
@limiter.limit(RATE_LIMIT)
async def create_file(request: Request, payload: CreateFileRequest):
    """Create a new file in a workspace"""
    try:
        result = await workspace_manager.create_file(
            payload.workspace_name, 
            payload.file_path, 
            payload.content
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.put("", summary="Update an existing file")
@limiter.limit(RATE_LIMIT)
async def update_file(request: Request, payload: UpdateFileRequest):
    """Update an existing file in a workspace"""
    try:
        result = await workspace_manager.update_file(
            payload.workspace_name, 
            payload.file_path, 
            payload.content
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error updating file: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.patch("", summary="Apply git diff patch to files")
@limiter.limit(RATE_LIMIT)
async def patch_files(request: Request, payload: PatchFileRequest):
    """Apply git diff patch to workspace files"""
    try:
        result = await workspace_manager.apply_patch(
            payload.workspace_name,
            payload.patch
        )
        
        # Check if patch application failed due to syntax errors
        if not result.get("patch_applied", True) and "error_code" in result:
            # Return HTTP 400 for syntax errors with detailed error information
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error_code": result["error_code"],
                    "error_message": result["error_message"],
                    "data": result
                }
            )
        
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error applying patch: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.delete("/{workspace_name}/{file_path:path}", summary="Delete a file")
@limiter.limit(RATE_LIMIT)
async def delete_file(request: Request, workspace_name: str, file_path: str):
    """Delete a file from a workspace"""
    try:
        result = await workspace_manager.delete_file(workspace_name, file_path)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@router.get("/{workspace_name}/{file_path:path}", summary="Get file content")
@limiter.limit(RATE_LIMIT)
async def get_file_content(request: Request, workspace_name: str, file_path: str):
    """Get the content of a file"""
    try:
        result = await workspace_manager.get_file_content(workspace_name, file_path)
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Error getting file content: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}") 