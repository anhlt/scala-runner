"""
File synchronization manager for Scala Runner client.
"""

import asyncio
import logging
import aiofiles
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import hashlib
import json

from .api_client import ScalaRunnerAPIClient

logger = logging.getLogger(__name__)

class FileSynchronizer:
    def __init__(self, api_client: ScalaRunnerAPIClient, workspace_name: str, local_dir: Optional[Path] = None):
        self.api_client = api_client
        self.workspace_name = workspace_name
        self.local_dir = local_dir or Path.cwd() / "local_workspace" / workspace_name
        self.file_cache: Dict[str, Dict[str, Any]] = {}
        self.sync_metadata_file = self.local_dir / ".sync_metadata.json"
        
        # Ensure local directory exists
        self.local_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing sync metadata
        self._load_sync_metadata()
    
    def _load_sync_metadata(self):
        """Load sync metadata from file"""
        try:
            if self.sync_metadata_file.exists():
                with open(self.sync_metadata_file, 'r') as f:
                    self.file_cache = json.load(f)
            else:
                self.file_cache = {}
        except Exception as e:
            logger.error(f"Error loading sync metadata: {e}")
            self.file_cache = {}
    
    def _save_sync_metadata(self):
        """Save sync metadata to file"""
        try:
            with open(self.sync_metadata_file, 'w') as f:
                json.dump(self.file_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving sync metadata: {e}")
    
    def _get_file_hash(self, content: str) -> str:
        """Get SHA256 hash of file content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def sync_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Sync a specific file with the server"""
        try:
            # Get server file content
            server_data = await self.api_client.get_file_content(self.workspace_name, file_path)
            server_content = server_data.get("content", "")
            server_hash = self._get_file_hash(server_content)
            
            # Get local file info
            local_file_path = self.local_dir / file_path
            local_content = ""
            local_hash = ""
            
            if local_file_path.exists():
                async with aiofiles.open(local_file_path, 'r', encoding='utf-8') as f:
                    local_content = await f.read()
                local_hash = self._get_file_hash(local_content)
            
            # Get cached info
            cached_info = self.file_cache.get(file_path, {})
            cached_hash = cached_info.get("hash", "")
            
            # Determine sync action needed
            if server_hash == local_hash:
                # Files are identical
                logger.debug(f"File {file_path} is already in sync")
                return None
            
            elif server_hash == cached_hash:
                # Server hasn't changed, local has changed
                logger.info(f"Local file {file_path} has changes, consider uploading")
                return {
                    "action": "local_changed",
                    "file_path": file_path,
                    "local_content": local_content,
                    "server_content": server_content
                }
            
            else:
                # Server has changed, need to update local
                logger.info(f"Server file {file_path} has changes, updating local")
                await self._update_local_file(file_path, server_content)
                
                # Update cache
                self.file_cache[file_path] = {
                    "hash": server_hash,
                    "last_sync": datetime.now().isoformat(),
                    "size": len(server_content)
                }
                self._save_sync_metadata()
                
                return {
                    "action": "updated_from_server",
                    "file_path": file_path,
                    "content": server_content,
                    "changes_detected": True
                }
                
        except Exception as e:
            logger.error(f"Error syncing file {file_path}: {e}")
            raise
    
    async def _update_local_file(self, file_path: str, content: str):
        """Update local file with server content"""
        local_file_path = self.local_dir / file_path
        
        # Ensure parent directories exist
        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        async with aiofiles.open(local_file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        logger.info(f"Updated local file: {local_file_path}")
    
    async def upload_file(self, file_path: str) -> Dict[str, Any]:
        """Upload local file to server"""
        local_file_path = self.local_dir / file_path
        
        if not local_file_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_file_path}")
        
        # Read local content
        async with aiofiles.open(local_file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        # Upload to server
        result = await self.api_client.update_file(self.workspace_name, file_path, content)
        
        # Update cache
        file_hash = self._get_file_hash(content)
        self.file_cache[file_path] = {
            "hash": file_hash,
            "last_sync": datetime.now().isoformat(),
            "size": len(content)
        }
        self._save_sync_metadata()
        
        logger.info(f"Uploaded file to server: {file_path}")
        return result
    
    async def sync_workspace(self) -> Dict[str, Any]:
        """Sync entire workspace with server"""
        try:
            # Get server file tree
            tree_data = await self.api_client.get_file_tree(self.workspace_name)
            server_files = self._extract_files_from_tree(tree_data.get("tree", {}))
            
            sync_results = {
                "synced_files": [],
                "local_changes": [],
                "server_changes": [],
                "errors": []
            }
            
            # Sync each file
            for file_path in server_files:
                try:
                    result = await self.sync_file(file_path)
                    if result:
                        if result["action"] == "updated_from_server":
                            sync_results["server_changes"].append(file_path)
                        elif result["action"] == "local_changed":
                            sync_results["local_changes"].append(file_path)
                        sync_results["synced_files"].append(file_path)
                except Exception as e:
                    sync_results["errors"].append({"file": file_path, "error": str(e)})
            
            logger.info(f"Workspace sync completed: {len(sync_results['synced_files'])} files processed")
            return sync_results
            
        except Exception as e:
            logger.error(f"Error syncing workspace: {e}")
            raise
    
    def _extract_files_from_tree(self, tree_node: Dict, files: Optional[List[str]] = None, path_prefix: str = "") -> List[str]:
        """Extract file paths from tree structure"""
        if files is None:
            files = []
        
        if tree_node.get("type") == "file":
            file_path = f"{path_prefix}{tree_node['name']}" if path_prefix else tree_node["name"]
            files.append(file_path)
        elif tree_node.get("type") == "directory":
            current_prefix = f"{path_prefix}{tree_node['name']}/" if tree_node["name"] != "." else path_prefix
            for child in tree_node.get("children", []):
                self._extract_files_from_tree(child, files, current_prefix)
        
        return files
    
    async def download_file(self, file_path: str, force: bool = False) -> str:
        """Download a file from server to local"""
        try:
            server_data = await self.api_client.get_file_content(self.workspace_name, file_path)
            content = server_data.get("content", "")
            
            local_file_path = self.local_dir / file_path
            
            # Check if local file exists and force flag
            if local_file_path.exists() and not force:
                raise FileExistsError(f"Local file exists: {local_file_path}. Use force=True to overwrite.")
            
            await self._update_local_file(file_path, content)
            
            # Update cache
            file_hash = self._get_file_hash(content)
            self.file_cache[file_path] = {
                "hash": file_hash,
                "last_sync": datetime.now().isoformat(),
                "size": len(content)
            }
            self._save_sync_metadata()
            
            return content
            
        except Exception as e:
            logger.error(f"Error downloading file {file_path}: {e}")
            raise
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get sync status for all tracked files"""
        try:
            tree_data = await self.api_client.get_file_tree(self.workspace_name)
            server_files = self._extract_files_from_tree(tree_data.get("tree", {}))
            
            status = {
                "in_sync": [],
                "local_changes": [],
                "server_changes": [],
                "new_on_server": [],
                "local_only": []
            }
            
            # Check each server file
            for file_path in server_files:
                local_file_path = self.local_dir / file_path
                
                if not local_file_path.exists():
                    status["new_on_server"].append(file_path)
                    continue
                
                # Get file hashes
                server_data = await self.api_client.get_file_content(self.workspace_name, file_path)
                server_content = server_data.get("content", "")
                server_hash = self._get_file_hash(server_content)
                
                async with aiofiles.open(local_file_path, 'r', encoding='utf-8') as f:
                    local_content = await f.read()
                local_hash = self._get_file_hash(local_content)
                
                cached_info = self.file_cache.get(file_path, {})
                cached_hash = cached_info.get("hash", "")
                
                if server_hash == local_hash:
                    status["in_sync"].append(file_path)
                elif server_hash == cached_hash:
                    status["local_changes"].append(file_path)
                else:
                    status["server_changes"].append(file_path)
            
            # Check for local-only files
            if self.local_dir.exists():
                for local_file in self.local_dir.rglob("*"):
                    if local_file.is_file() and local_file.name != ".sync_metadata.json":
                        relative_path = local_file.relative_to(self.local_dir)
                        file_path = str(relative_path).replace("\\", "/")  # Normalize path separators
                        if file_path not in server_files:
                            status["local_only"].append(file_path)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            raise
    
    def get_local_file_path(self, file_path: str) -> Path:
        """Get local file path for a server file path"""
        return self.local_dir / file_path
    
    def cleanup(self):
        """Cleanup resources"""
        self._save_sync_metadata() 