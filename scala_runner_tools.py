"""
title: Scala Runner Tools
author: You
description: |
  Provides async operations to interact with a Scala Runner HTTP service,
  including health checks, workspace management, file operations, git operations,
  SBT commands, search functionality, and bash session management.
requirements: httpx,pydantic
version: 0.2.0
license: MIT
"""

import logging
import httpx
from typing import List, Optional, Callable, Union, Dict, Any
from pydantic import BaseModel, Field

# configure logger
logger = logging.getLogger("scala_runner_tools")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
)
logger.addHandler(handler)


async def _emit(
    emitter: Optional[Callable[[Dict], None]], description: str, done: bool = False
):
    """
    Emit a status update if an event emitter callback is provided.
    """
    if emitter:
        logger.info(f"Emitting status: {description} (done={done})")
        await emitter(
            {
                "type": "status",
                "data": {"description": description, "done": done, "hidden": False},
            }
        )


def _build_headers() -> Dict[str, str]:
    """
    Build default HTTP headers. Extend for auth if needed.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    logger.debug("Built headers for Scala-Runner request: %s", headers)
    return headers


class Tools:
    """
    Async client for the Scala-Runner API.

    Endpoints:
      - GET  /ping  : health check, returns "pong"
      - POST /run   : execute Scala code via scala-cli in Docker
      - Workspace management (create, list, delete, clone)
      - File operations (create, read, update, delete, patch)
      - Git operations (checkout, add, commit, push, pull, status, log)
      - SBT operations (compile, run, test, clean, project info)
      - Search operations (search files by content)
      - Bash session management (create, execute, close sessions)

    Configuration via Valves:
      - SCALA_RUNNER_SERVER_URL: base URL of the service
      - TIMEOUT: per-request timeout (seconds)
    """

    class Valves(BaseModel):
        SCALA_RUNNER_SERVER_URL: str = Field(
            "http://localhost:8000", description="Base URL of the Scala-Runner service"
        )
        TIMEOUT: float = Field(
            30.0, description="Default timeout for HTTP operations (seconds)"
        )

    class UserValves(BaseModel):
        """Placeholder for user-specific auth info, if needed in future."""
        pass

    def __init__(self, valves: Optional[Dict[str, Union[str, float]]] = None):
        # Load defaults, then override from provided dict if any
        self.valves = self.Valves(**(valves or {}))
        logger.info(
            f"ScalaRunner Tools configured with server="
            f"{self.valves.SCALA_RUNNER_SERVER_URL!r}, timeout={self.valves.TIMEOUT}s"
        )

    # Health Check
    async def ping(
        self, __event_emitter__: Optional[Callable[[Dict], None]] = None
    ) -> Union[str, Dict[str, str]]:
        """
        Health-check against /ping endpoint.
        Returns:
          - "pong" on success
          - {"error": "..."} on failure or timeout
        """
        timeout = self.valves.TIMEOUT
        await _emit(__event_emitter__, "Pinging Scala-Runner…")
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/ping",
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            await _emit(__event_emitter__, "Ping successful", done=True)
            return resp.json()

        except httpx.ReadTimeout:
            msg = f"Ping timed out after {timeout}s"
            await _emit(__event_emitter__, msg, done=True)
            return {"error": msg}

        except Exception as e:
            await _emit(__event_emitter__, f"Ping failed: {e}", done=True)
            return {"error": str(e)}

    # Legacy run_scala method (keeping for compatibility)
    async def run_scala(
        self,
        worksheet_code: str,
        scala_version: str,
        file_extension: str,
        dependencies: Optional[List[str]] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """
        Submit Scala code to /run endpoint and return execution result.
        Note: This endpoint may not exist in current API - using SBT operations instead.
        """
        timeout = self.valves.TIMEOUT
        if dependencies is None:
            dependencies = ["org.typelevel::cats-core:2.13.0"]

        payload = {
            "code": worksheet_code,
            "scala_version": scala_version,
            "dependencies": dependencies,
            "file_extension": file_extension,
        }

        await _emit(__event_emitter__, f"Submitting Scala code (timeout={timeout}s)…")
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/run",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Scala code executed", done=True)
            return result

        except httpx.ReadTimeout:
            msg = f"Execution timed out after {timeout}s"
            await _emit(__event_emitter__, msg, done=True)
            return {"error": msg}

        except httpx.HTTPStatusError as e:
            response = e.response
            try:
                body = response.json()
            except Exception:
                body = response.text
            msg = f"HTTP {response.status_code} {response.reason_phrase}"
            await _emit(__event_emitter__, msg, done=True)
            return {"error": msg, "status_code": response.status_code, "body": body}

        except Exception as e:
            await _emit(__event_emitter__, f"Execution failed: {e}", done=True)
            return {"error": str(e)}

    # Workspace Management
    async def create_workspace(
        self,
        name: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Create a new SBT workspace with basic project structure"""
        await _emit(__event_emitter__, f"Creating workspace '{name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/workspaces",
                    json={"name": name},
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"Workspace '{name}' created", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to create workspace: {e}", done=True)
            return {"error": str(e)}

    async def list_workspaces(
        self, __event_emitter__: Optional[Callable[[Dict], None]] = None
    ) -> Union[Dict, Dict[str, str]]:
        """List all available workspaces"""
        await _emit(__event_emitter__, "Listing workspaces…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/workspaces",
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Workspaces listed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to list workspaces: {e}", done=True)
            return {"error": str(e)}

    async def delete_workspace(
        self,
        workspace_name: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Delete a workspace and all its files"""
        await _emit(__event_emitter__, f"Deleting workspace '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.delete(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/workspaces/{workspace_name}",
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"Workspace '{workspace_name}' deleted", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to delete workspace: {e}", done=True)
            return {"error": str(e)}

    async def clone_workspace_from_git(
        self,
        name: str,
        git_url: str,
        branch: Optional[str] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Clone a Git repository into a new workspace"""
        await _emit(__event_emitter__, f"Cloning Git repository to workspace '{name}'…")
        try:
            payload = {"name": name, "git_url": git_url}
            if branch:
                payload["branch"] = branch
            
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/workspaces/clone",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"Repository cloned to workspace '{name}'", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to clone repository: {e}", done=True)
            return {"error": str(e)}

    async def get_workspace_tree(
        self,
        workspace_name: str,
        show_all: bool = False,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Get the file tree structure of a workspace
        
        Args:
            workspace_name: Name of the workspace
            show_all: If False (default), filters out compiler-generated files and build artifacts.
                     If True, shows all files including .git, target/, .bsp/, etc.
        """
        await _emit(__event_emitter__, f"Getting file tree for '{workspace_name}'…")
        try:
            params = {}
            if show_all:
                params["show_all"] = True
                
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/workspaces/{workspace_name}/tree",
                    params=params,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "File tree retrieved", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to get file tree: {e}", done=True)
            return {"error": str(e)}

    # File Operations
    async def create_file(
        self,
        workspace_name: str,
        file_path: str,
        content: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Create a new file in a workspace"""
        await _emit(__event_emitter__, f"Creating file '{file_path}' in '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/files",
                    json={
                        "workspace_name": workspace_name,
                        "file_path": file_path,
                        "content": content,
                    },
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"File '{file_path}' created", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to create file: {e}", done=True)
            return {"error": str(e)}

    async def get_file_content(
        self,
        workspace_name: str,
        file_path: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Get the content of a file"""
        await _emit(__event_emitter__, f"Reading file '{file_path}' from '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/files/{workspace_name}/{file_path}",
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"File '{file_path}' content retrieved", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to read file: {e}", done=True)
            return {"error": str(e)}

    async def update_file(
        self,
        workspace_name: str,
        file_path: str,
        content: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Update an existing file in a workspace"""
        await _emit(__event_emitter__, f"Updating file '{file_path}' in '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.put(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/files",
                    json={
                        "workspace_name": workspace_name,
                        "file_path": file_path,
                        "content": content,
                    },
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"File '{file_path}' updated", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to update file: {e}", done=True)
            return {"error": str(e)}

    async def delete_file(
        self,
        workspace_name: str,
        file_path: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Delete a file from a workspace"""
        await _emit(__event_emitter__, f"Deleting file '{file_path}' from '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.delete(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/files/{workspace_name}/{file_path}",
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"File '{file_path}' deleted", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to delete file: {e}", done=True)
            return {"error": str(e)}

    async def apply_patch(
        self,
        workspace_name: str,
        patch: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Apply git diff patch to workspace files"""
        await _emit(__event_emitter__, f"Applying patch to '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.patch(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/files",
                    json={
                        "workspace_name": workspace_name,
                        "patch": patch,
                    },
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Patch applied successfully", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to apply patch: {e}", done=True)
            return {"error": str(e)}

    # SBT Operations
    async def sbt_compile(
        self,
        workspace_name: str,
        timeout: Optional[int] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Compile the SBT project in a workspace"""
        await _emit(__event_emitter__, f"Compiling SBT project in '{workspace_name}'…")
        try:
            payload = {"workspace_name": workspace_name}
            if timeout:
                payload["timeout"] = timeout
                
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/sbt/compile",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "SBT compilation completed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"SBT compilation failed: {e}", done=True)
            return {"error": str(e)}

    async def sbt_run(
        self,
        workspace_name: str,
        main_class: Optional[str] = None,
        timeout: Optional[int] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Run the main class of the SBT project"""
        await _emit(__event_emitter__, f"Running SBT project in '{workspace_name}'…")
        try:
            payload = {"workspace_name": workspace_name}
            if main_class:
                payload["main_class"] = main_class
            if timeout:
                payload["timeout"] = timeout
                
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/sbt/run-project",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "SBT project run completed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"SBT run failed: {e}", done=True)
            return {"error": str(e)}

    async def sbt_test(
        self,
        workspace_name: str,
        test_name: Optional[str] = None,
        timeout: Optional[int] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Run tests in the SBT project"""
        await _emit(__event_emitter__, f"Running SBT tests in '{workspace_name}'…")
        try:
            payload = {"workspace_name": workspace_name}
            if test_name:
                payload["test_name"] = test_name
            if timeout:
                payload["timeout"] = timeout
                
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/sbt/test",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "SBT tests completed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"SBT tests failed: {e}", done=True)
            return {"error": str(e)}

    async def sbt_clean(
        self,
        workspace_name: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Clean the SBT project build artifacts"""
        await _emit(__event_emitter__, f"Cleaning SBT project in '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/sbt/clean",
                    json={"workspace_name": workspace_name},
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "SBT project cleaned", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"SBT clean failed: {e}", done=True)
            return {"error": str(e)}

    async def sbt_custom_command(
        self,
        workspace_name: str,
        command: str,
        timeout: Optional[int] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Execute a custom SBT command in a workspace"""
        await _emit(__event_emitter__, f"Running SBT command '{command}' in '{workspace_name}'…")
        try:
            payload = {"workspace_name": workspace_name, "command": command}
            if timeout:
                payload["timeout"] = timeout
                
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/sbt/run",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"SBT command '{command}' completed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"SBT command failed: {e}", done=True)
            return {"error": str(e)}

    # Git Operations
    async def git_status(
        self,
        workspace_name: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Get Git status of a workspace"""
        await _emit(__event_emitter__, f"Getting Git status for '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/git/status/{workspace_name}",
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Git status retrieved", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to get Git status: {e}", done=True)
            return {"error": str(e)}

    async def git_add(
        self,
        workspace_name: str,
        file_paths: Optional[List[str]] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Add files to Git staging area"""
        await _emit(__event_emitter__, f"Adding files to Git staging in '{workspace_name}'…")
        try:
            payload = {"workspace_name": workspace_name}
            if file_paths:
                payload["file_paths"] = file_paths
                
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/git/add",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Files added to Git staging", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to add files to Git: {e}", done=True)
            return {"error": str(e)}

    async def git_commit(
        self,
        workspace_name: str,
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Commit staged changes to Git repository"""
        await _emit(__event_emitter__, f"Committing changes in '{workspace_name}'…")
        try:
            payload = {"workspace_name": workspace_name, "message": message}
            if author_name:
                payload["author_name"] = author_name
            if author_email:
                payload["author_email"] = author_email
                
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/git/commit",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Git commit completed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Git commit failed: {e}", done=True)
            return {"error": str(e)}

    # Search Operations
    async def search_files(
        self,
        workspace_name: str,
        query: str,
        limit: Optional[int] = 10,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Search for files containing the specified query"""
        await _emit(__event_emitter__, f"Searching for '{query}' in '{workspace_name}'…")
        try:
            payload = {
                "workspace_name": workspace_name,
                "query": query,
                "limit": limit or 10,
            }
            
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/search",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, f"Search completed, found {result.get('data', {}).get('count', 0)} results", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Search failed: {e}", done=True)
            return {"error": str(e)}

    # Bash Session Operations  
    async def create_bash_session(
        self,
        workspace_name: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Create a new bash session for a workspace"""
        await _emit(__event_emitter__, f"Creating bash session for '{workspace_name}'…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/bash/sessions",
                    json={"workspace_name": workspace_name},
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Bash session created", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to create bash session: {e}", done=True)
            return {"error": str(e)}

    async def execute_bash_command(
        self,
        session_id: str,
        command: str,
        timeout: Optional[int] = 30,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Execute a command in an existing bash session"""
        await _emit(__event_emitter__, f"Executing command '{command}' in session {session_id}…")
        try:
            payload = {
                "session_id": session_id,
                "command": command,
                "timeout": timeout or 30,
            }
            
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.post(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/bash/execute",
                    json=payload,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Command executed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Command execution failed: {e}", done=True)
            return {"error": str(e)}

    async def list_bash_sessions(
        self,
        workspace_name: Optional[str] = None,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """List all bash sessions or sessions for a specific workspace"""
        await _emit(__event_emitter__, "Listing bash sessions…")
        try:
            params = {}
            if workspace_name:
                params["workspace_name"] = workspace_name
                
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/bash/sessions",
                    params=params,
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Bash sessions listed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to list bash sessions: {e}", done=True)
            return {"error": str(e)}

    async def close_bash_session(
        self,
        session_id: str,
        __event_emitter__: Optional[Callable[[Dict], None]] = None,
    ) -> Union[Dict, Dict[str, str]]:
        """Close a specific bash session"""
        await _emit(__event_emitter__, f"Closing bash session {session_id}…")
        try:
            async with httpx.AsyncClient(timeout=self.valves.TIMEOUT) as client:
                resp = await client.delete(
                    f"{self.valves.SCALA_RUNNER_SERVER_URL}/bash/sessions/{session_id}",
                    headers=_build_headers(),
                )
            resp.raise_for_status()
            result = resp.json()
            await _emit(__event_emitter__, "Bash session closed", done=True)
            return result
        except Exception as e:
            await _emit(__event_emitter__, f"Failed to close bash session: {e}", done=True)
            return {"error": str(e)} 