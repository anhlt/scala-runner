"""
API client for Scala Runner HTTP API.
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ScalaRunnerAPIClient:
    def __init__(self, server_url: str, timeout: float = 30.0):
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # Health Check
    async def ping(self) -> Dict[str, Any]:
        """Health check endpoint"""
        response = await self.client.get(f"{self.server_url}/ping")
        response.raise_for_status()
        return response.json()
    
    # Workspace Management
    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all workspaces"""
        response = await self.client.get(f"{self.server_url}/workspaces")
        response.raise_for_status()
        result = response.json()
        return result.get("data", [])
    
    async def create_workspace(self, name: str) -> Dict[str, Any]:
        """Create a new workspace"""
        response = await self.client.post(
            f"{self.server_url}/workspaces",
            json={"name": name}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def delete_workspace(self, workspace_name: str) -> Dict[str, Any]:
        """Delete a workspace"""
        response = await self.client.delete(f"{self.server_url}/workspaces/{workspace_name}")
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def clone_workspace(self, name: str, git_url: str, branch: str = "main") -> Dict[str, Any]:
        """Clone a workspace from Git repository"""
        response = await self.client.post(
            f"{self.server_url}/workspaces/clone",
            json={"name": name, "git_url": git_url, "branch": branch}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def get_file_tree(self, workspace_name: str, show_all: bool = False) -> Dict[str, Any]:
        """Get file tree structure for a workspace"""
        params = {"show_all": show_all} if show_all else {}
        response = await self.client.get(
            f"{self.server_url}/workspaces/{workspace_name}/tree",
            params=params
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def get_git_info(self, workspace_name: str) -> Dict[str, Any]:
        """Get Git repository information for a workspace"""
        response = await self.client.get(f"{self.server_url}/workspaces/{workspace_name}/git-info")
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    # File Operations
    async def create_file(self, workspace_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Create a new file"""
        response = await self.client.post(
            f"{self.server_url}/files",
            json={
                "workspace_name": workspace_name,
                "file_path": file_path,
                "content": content
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def update_file(self, workspace_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Update an existing file"""
        response = await self.client.put(
            f"{self.server_url}/files",
            json={
                "workspace_name": workspace_name,
                "file_path": file_path,
                "content": content
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def get_file_content(self, workspace_name: str, file_path: str) -> Dict[str, Any]:
        """Get file content"""
        response = await self.client.get(f"{self.server_url}/files/{workspace_name}/{file_path}")
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def delete_file(self, workspace_name: str, file_path: str) -> Dict[str, Any]:
        """Delete a file"""
        response = await self.client.delete(f"{self.server_url}/files/{workspace_name}/{file_path}")
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def patch_files(self, workspace_name: str, patch: str) -> Dict[str, Any]:
        """Apply a git diff patch to files"""
        response = await self.client.patch(
            f"{self.server_url}/files",
            json={
                "workspace_name": workspace_name,
                "patch": patch
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    # Search Operations
    async def search_files(self, workspace_name: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search files by content"""
        response = await self.client.post(
            f"{self.server_url}/search",
            json={
                "workspace_name": workspace_name,
                "query": query,
                "limit": limit
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {}).get("results", [])
    
    # Git Operations
    async def git_status(self, workspace_name: str) -> Dict[str, Any]:
        """Get Git status"""
        response = await self.client.get(f"{self.server_url}/git/status/{workspace_name}")
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def git_add(self, workspace_name: str, file_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Add files to Git staging"""
        payload = {"workspace_name": workspace_name}
        if file_paths:
            payload["file_paths"] = file_paths
        
        response = await self.client.post(f"{self.server_url}/git/add", json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def git_commit(self, workspace_name: str, message: str, 
                        author_name: Optional[str] = None, 
                        author_email: Optional[str] = None) -> Dict[str, Any]:
        """Commit changes"""
        payload = {"workspace_name": workspace_name, "message": message}
        if author_name:
            payload["author_name"] = author_name
        if author_email:
            payload["author_email"] = author_email
        
        response = await self.client.post(f"{self.server_url}/git/commit", json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def git_push(self, workspace_name: str, remote_name: str = "origin", 
                      branch_name: str = "main") -> Dict[str, Any]:
        """Push changes to remote"""
        response = await self.client.post(
            f"{self.server_url}/git/push",
            json={
                "workspace_name": workspace_name,
                "remote_name": remote_name,
                "branch_name": branch_name
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def git_pull(self, workspace_name: str, remote_name: str = "origin", 
                      branch_name: str = "main") -> Dict[str, Any]:
        """Pull changes from remote"""
        response = await self.client.post(
            f"{self.server_url}/git/pull",
            json={
                "workspace_name": workspace_name,
                "remote_name": remote_name,
                "branch_name": branch_name
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    # SBT Operations
    async def sbt_compile(self, workspace_name: str, timeout: int = 300) -> Dict[str, Any]:
        """Compile SBT project"""
        response = await self.client.post(
            f"{self.server_url}/sbt/compile",
            json={"workspace_name": workspace_name, "timeout": timeout}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def sbt_run(self, workspace_name: str, command: str, timeout: int = 300) -> Dict[str, Any]:
        """Run custom SBT command"""
        response = await self.client.post(
            f"{self.server_url}/sbt/run",
            json={
                "workspace_name": workspace_name,
                "command": command,
                "timeout": timeout
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {})
    
    async def sbt_test(self, workspace_name: str, timeout: int = 300) -> Dict[str, Any]:
        """Run SBT tests"""
        response = await self.client.post(
            f"{self.server_url}/sbt/test",
            json={"workspace_name": workspace_name, "timeout": timeout}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {}) 