"""
Utility endpoints.
"""

from fastapi import APIRouter

router = APIRouter(
    tags=["utils"],
)

# Legacy and Utility Endpoints
@router.get("/ping", summary="Health check endpoint")
async def ping():
    """Simple health check endpoint that returns 'pong' to confirm the API is running."""
    return {"status": "pong"} 