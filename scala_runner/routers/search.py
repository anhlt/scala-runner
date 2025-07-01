"""
Search endpoints.
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
    prefix="/search",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)

# Import managers - these will be injected via dependency injection
workspace_manager = None

def set_managers(ws_manager):
    """Set the workspace manager instance"""
    global workspace_manager
    workspace_manager = ws_manager


# Pydantic models
class SearchRequest(BaseModel):
    workspace_name: str  # Can be "all" to search across all workspaces
    query: str
    limit: Optional[int] = 10


# Search Endpoints
@router.post("", summary="Search files by content")
@limiter.limit(RATE_LIMIT)
async def search_files(request: Request, payload: SearchRequest):
    """Search for files containing the specified query"""
    try:
        results = await workspace_manager.search_files(
            payload.workspace_name,
            payload.query,
            payload.limit or 10
        )
        return JSONResponse({
            "status": "success", 
            "data": {
                "query": payload.query,
                "workspace": payload.workspace_name,
                "results": results,
                "count": len(results)
            }
        })
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}") 