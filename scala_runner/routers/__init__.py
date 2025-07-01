"""
Router modules for organizing FastAPI endpoints by service.
"""

from .workspace import router as workspace_router
from .git import router as git_router
from .files import router as files_router
from .search import router as search_router
from .sbt import router as sbt_router
from .bash import router as bash_router
from .utils import router as utils_router

__all__ = [
    "workspace_router",
    "git_router", 
    "files_router",
    "search_router",
    "sbt_router",
    "bash_router",
    "utils_router"
] 