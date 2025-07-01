"""
Utility endpoints.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(
    tags=["utils"],
)

# Legacy and Utility Endpoints
@router.get("/ping", summary="Health check endpoint")
async def ping():
    """Simple health check endpoint that returns 'pong' to confirm the API is running."""
    return {"status": "pong"}


@router.get(
    "/openapi",
    summary="Alias for the OpenAPI schema",
    include_in_schema=False
)
async def openapi_schema():
    """Return the OpenAPI schema (alias for /openapi.json). No rate-limit applied."""
    # This will be populated by the main app
    return JSONResponse({}) 