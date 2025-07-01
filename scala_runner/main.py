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
# slowapi imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
# logger
import logging
from .workspace_manager import WorkspaceManager
from .sbt_runner import SBTRunner
from .bash_session_manager import BashSessionManager

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

app = FastAPI(
    title="Scala SBT Workspace API",
    description="Manage SBT workspaces and run SBT commands via Docker",
    version="0.2.0",
)
# register the exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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


class SearchRequest(BaseModel):
    workspace_name: str  # Can be "all" to search across all workspaces
    query: str
    limit: Optional[int] = 10


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


# Workspace Management Endpoints
@app.post("/workspaces", summary="Create a new workspace")
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


@app.get("/workspaces", summary="List all workspaces")
@limiter.limit(RATE_LIMIT)
async def list_workspaces(request: Request):
    """List all available workspaces"""
    try:
        workspaces = workspace_manager.list_workspaces()
        return JSONResponse({"status": "success", "data": workspaces})
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.delete("/workspaces/{workspace_name}", summary="Delete a workspace")
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


@app.get("/workspaces/{workspace_name}/tree", summary="Get workspace file tree")
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


@app.post("/workspaces/clone", summary="Clone workspace from Git repository")
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


@app.get("/workspaces/{workspace_name}/git-info", summary="Get Git repository information")
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


# Git Operations Endpoints
@app.post("/git/checkout", summary="Checkout Git branch")
@limiter.limit(RATE_LIMIT)
async def git_checkout_branch(request: Request, payload: GitCheckoutRequest):
    """Checkout a Git branch (optionally create new branch)"""
    try:
        result = await workspace_manager.git_checkout_branch(
            payload.workspace_name,
            payload.branch_name,
            payload.create_new
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git checkout: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.post("/git/add", summary="Add files to Git staging area")
@limiter.limit(RATE_LIMIT)
async def git_add_files(request: Request, payload: GitAddRequest):
    """Add files to Git staging area"""
    try:
        result = await workspace_manager.git_add_files(
            payload.workspace_name,
            payload.file_paths
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git add: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.post("/git/commit", summary="Commit staged changes")
@limiter.limit(RATE_LIMIT)
async def git_commit_changes(request: Request, payload: GitCommitRequest):
    """Commit staged changes to Git repository"""
    try:
        result = await workspace_manager.git_commit(
            payload.workspace_name,
            payload.message,
            payload.author_name,
            payload.author_email
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git commit: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.post("/git/push", summary="Push changes to remote repository")
@limiter.limit(RATE_LIMIT)
async def git_push_changes(request: Request, payload: GitPushPullRequest):
    """Push changes to remote Git repository"""
    try:
        result = await workspace_manager.git_push(
            payload.workspace_name,
            payload.remote_name,
            payload.branch_name
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git push: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.post("/git/pull", summary="Pull changes from remote repository")
@limiter.limit(RATE_LIMIT)
async def git_pull_changes(request: Request, payload: GitPushPullRequest):
    """Pull changes from remote Git repository"""
    try:
        result = await workspace_manager.git_pull(
            payload.workspace_name,
            payload.remote_name,
            payload.branch_name
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error during Git pull: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.get("/git/status/{workspace_name}", summary="Get Git status")
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


@app.get("/git/log/{workspace_name}", summary="Get Git commit history")
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


# File Management Endpoints
@app.post("/files", summary="Create a new file")
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


@app.put("/files", summary="Update an existing file")
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


@app.patch("/files", summary="Apply git diff patch to files")
@limiter.limit(RATE_LIMIT)
async def patch_files(request: Request, payload: PatchFileRequest):
    """Apply git diff patch to workspace files"""
    try:
        result = await workspace_manager.apply_patch(
            payload.workspace_name,
            payload.patch
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error applying patch: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.delete("/files/{workspace_name}/{file_path:path}", summary="Delete a file")
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


@app.get("/files/{workspace_name}/{file_path:path}", summary="Get file content")
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


# Search Endpoints
@app.post("/search", summary="Search files by content")
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


# SBT Command Endpoints
@app.post("/sbt/run", summary="Run SBT command")
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


@app.post("/sbt/compile", summary="Compile SBT project")
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


@app.post("/sbt/run-project", summary="Run SBT project")
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


@app.post("/sbt/test", summary="Run SBT tests")
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


@app.post("/sbt/clean", summary="Clean SBT project")
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


@app.get("/sbt/project-info/{workspace_name}", summary="Get SBT project info")
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


# Bash Session Endpoints
@app.post("/bash/sessions", summary="Create a new bash session")
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


@app.post("/bash/execute", summary="Execute command in bash session")
@limiter.limit(RATE_LIMIT)
async def execute_bash_command(request: Request, payload: ExecuteBashCommandRequest):
    """Execute a command in an existing bash session"""
    try:
        result = await bash_session_manager.execute_command(
            payload.session_id, 
            payload.command, 
            payload.timeout
        )
        return JSONResponse({"status": "success", "data": result})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Error executing bash command: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.delete("/bash/sessions/{session_id}", summary="Close a bash session")
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


@app.delete("/bash/workspaces/{workspace_name}/sessions", summary="Close all bash sessions for workspace")
@limiter.limit(RATE_LIMIT)
async def close_workspace_bash_sessions(request: Request, workspace_name: str):
    """Close all bash sessions for a workspace"""
    try:
        result = await bash_session_manager.close_workspace_sessions(workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error closing workspace bash sessions: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.get("/bash/sessions", summary="List all bash sessions")
@limiter.limit(RATE_LIMIT)
async def list_bash_sessions(request: Request, workspace_name: Optional[str] = None):
    """List all bash sessions or sessions for a specific workspace"""
    try:
        result = bash_session_manager.list_sessions(workspace_name)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error listing bash sessions: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


@app.get("/bash/sessions/{session_id}", summary="Get bash session info")
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


@app.post("/bash/cleanup", summary="Clean up inactive bash sessions")
@limiter.limit(RATE_LIMIT)
async def cleanup_bash_sessions(request: Request):
    """Clean up inactive or timed-out bash sessions"""
    try:
        result = await bash_session_manager.cleanup_inactive_sessions()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error cleaning up bash sessions: {e}")
        raise HTTPException(500, f"Internal server error: {str(e)}")


# Legacy and Utility Endpoints
@app.get("/ping", summary="Health check endpoint")
async def ping():
    """Simple health check endpoint that returns 'pong' to confirm the API is running."""
    return {"status": "pong"}


@app.get(
    "/openapi",
    summary="Alias for the OpenAPI schema",
    include_in_schema=False
)
async def openapi_schema():
    """Return the OpenAPI schema (alias for /openapi.json). No rate-limit applied."""
    return JSONResponse(app.openapi()) 