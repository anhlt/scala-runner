import os
import shutil
import json
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from whoosh.writing import AsyncWriter
import logging
import git
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)

# Whoosh schema for file indexing
file_schema = Schema(
    workspace=ID(stored=True),
    filepath=ID(stored=True),
    filename=TEXT(stored=True),
    content=TEXT(stored=True),
    extension=TEXT(stored=True)
)


class WorkspaceManager:
    def __init__(self, base_dir: str = "/tmp"):
        self.base_dir = Path(base_dir)
        self.workspaces_dir = self.base_dir / "workspaces"
        self.index_dir = self.base_dir / "search_index"
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._init_search_index()

    def _init_search_index(self):
        """Initialize the search index"""
        if not exists_in(str(self.index_dir)):
            create_in(str(self.index_dir), file_schema)

    async def create_workspace(self, workspace_name: str) -> Dict:
        """Create a new workspace directory"""
        if not self._is_valid_workspace_name(workspace_name):
            raise ValueError("Invalid workspace name. Use alphanumeric characters, hyphens, and underscores only.")
        
        workspace_path = self.workspaces_dir / workspace_name
        
        if workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' already exists")
        
        workspace_path.mkdir(parents=True)
        
        # Create basic SBT project structure
        await self._create_sbt_structure(workspace_path)
        
        logger.info(f"Created workspace: {workspace_name}")
        return {
            "workspace_name": workspace_name,
            "path": str(workspace_path),
            "created": True
        }

    async def _create_sbt_structure(self, workspace_path: Path):
        """Create basic SBT project structure"""
        # Create directories
        (workspace_path / "src" / "main" / "scala").mkdir(parents=True)
        (workspace_path / "src" / "test" / "scala").mkdir(parents=True)
        (workspace_path / "project").mkdir(parents=True)
        
        # Create build.sbt with stable Scala 2.13 and Java 21 compatibility
        build_sbt_content = '''ThisBuild / version := "0.1.0-SNAPSHOT"
ThisBuild / scalaVersion := "2.13.14"

lazy val root = (project in file("."))
  .settings(
    name := "scala-project",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-core" % "2.12.0",
      "org.scalatest" %% "scalatest" % "3.2.17" % Test
    ),
    // Ensure Java 21 compatibility
    javacOptions ++= Seq("-source", "11", "-target", "11"),
    scalacOptions ++= Seq("-release", "11")
  )
'''
        async with aiofiles.open(workspace_path / "build.sbt", "w") as f:
            await f.write(build_sbt_content)
        
        # Create plugins.sbt
        plugins_content = 'addSbtPlugin("com.github.sbt" % "sbt-native-packager" % "1.9.16")\n'
        async with aiofiles.open(workspace_path / "project" / "plugins.sbt", "w") as f:
            await f.write(plugins_content)
            
        # Create a sample Main.scala
        main_scala_content = '''object Main extends App {
  println("Hello, SBT World!")
  println("Scala version: " + scala.util.Properties.versionString)
}
'''
        async with aiofiles.open(workspace_path / "src" / "main" / "scala" / "Main.scala", "w") as f:
            await f.write(main_scala_content)

    def list_workspaces(self) -> List[Dict]:
        """List all workspaces"""
        workspaces = []
        if self.workspaces_dir.exists():
            for workspace_dir in self.workspaces_dir.iterdir():
                if workspace_dir.is_dir():
                    workspaces.append({
                        "name": workspace_dir.name,
                        "path": str(workspace_dir),
                        "files_count": self._count_files(workspace_dir)
                    })
        return workspaces

    async def delete_workspace(self, workspace_name: str) -> Dict:
        """Delete a workspace and remove it from index"""
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        # Remove from search index
        await self._remove_workspace_from_index(workspace_name)
        
        # Delete directory
        shutil.rmtree(workspace_path)
        
        logger.info(f"Deleted workspace: {workspace_name}")
        return {"workspace_name": workspace_name, "deleted": True}

    async def get_file_tree(self, workspace_name: str) -> Dict:
        """Get file tree structure for a workspace"""
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        return {
            "workspace_name": workspace_name,
            "tree": self._build_tree(workspace_path, workspace_path)
        }

    def _build_tree(self, path: Path, root_path: Path) -> Dict:
        """Build a tree structure recursively"""
        relative_path = path.relative_to(root_path) if path != root_path else Path(".")
        
        result = {
            "name": path.name if path.name else ".",
            "path": str(relative_path),
            "type": "directory" if path.is_dir() else "file"
        }
        
        if path.is_dir():
            children = []
            try:
                for child in sorted(path.iterdir()):
                    children.append(self._build_tree(child, root_path))
                result["children"] = children
            except PermissionError:
                result["error"] = "Permission denied"
        else:
            result["size"] = path.stat().st_size
            result["extension"] = path.suffix.lstrip('.')
        
        return result

    async def create_file(self, workspace_name: str, file_path: str, content: str) -> Dict:
        """Create a new file in the workspace"""
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        full_file_path = workspace_path / file_path
        
        # Create parent directories if they don't exist
        full_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(full_file_path, "w") as f:
            await f.write(content)
        
        # Index the file
        await self._index_file(workspace_name, file_path, content)
        
        logger.info(f"Created file: {workspace_name}/{file_path}")
        return {
            "workspace_name": workspace_name,
            "file_path": file_path,
            "created": True,
            "size": len(content)
        }

    async def update_file(self, workspace_name: str, file_path: str, content: str) -> Dict:
        """Update an existing file or create if it doesn't exist (upsert)"""
        workspace_path = self.workspaces_dir / workspace_name
        full_file_path = workspace_path / file_path
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        # Create parent directories if they don't exist
        full_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_existed = full_file_path.exists()
        
        async with aiofiles.open(full_file_path, "w") as f:
            await f.write(content)
        
        # Re-index the file
        await self._index_file(workspace_name, file_path, content)
        
        action = "updated" if file_existed else "created"
        logger.info(f"{action.capitalize()} file: {workspace_name}/{file_path}")
        return {
            "workspace_name": workspace_name,
            "file_path": file_path,
            "updated": file_existed,
            "created": not file_existed,
            "size": len(content)
        }

    async def delete_file(self, workspace_name: str, file_path: str) -> Dict:
        """Delete a file from the workspace"""
        workspace_path = self.workspaces_dir / workspace_name
        full_file_path = workspace_path / file_path
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        if not full_file_path.exists():
            raise ValueError(f"File '{file_path}' not found")
        
        full_file_path.unlink()
        
        # Remove from index
        await self._remove_file_from_index(workspace_name, file_path)
        
        logger.info(f"Deleted file: {workspace_name}/{file_path}")
        return {
            "workspace_name": workspace_name,
            "file_path": file_path,
            "deleted": True
        }

    async def get_file_content(self, workspace_name: str, file_path: str) -> Dict:
        """Get file content"""
        workspace_path = self.workspaces_dir / workspace_name
        full_file_path = workspace_path / file_path
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        if not full_file_path.exists():
            raise ValueError(f"File '{file_path}' not found")
        
        async with aiofiles.open(full_file_path, "r") as f:
            content = await f.read()
        
        return {
            "workspace_name": workspace_name,
            "file_path": file_path,
            "content": content,
            "size": len(content),
            "extension": full_file_path.suffix.lstrip('.')
        }

    async def search_files(self, workspace_name: str, query: str, limit: int = 10) -> List[Dict]:
        """Search for files containing the query"""
        try:
            index = open_dir(str(self.index_dir))
            
            with index.searcher() as searcher:
                query_parser = QueryParser("content", index.schema)
                parsed_query = query_parser.parse(query)
                
                # Filter by workspace if specified
                if workspace_name and workspace_name != "all":
                    from whoosh.query import And, Term
                    workspace_filter = Term("workspace", workspace_name)
                    parsed_query = And([parsed_query, workspace_filter])
                
                results = searcher.search(parsed_query, limit=limit)
                
                search_results = []
                for result in results:
                    # Get line numbers where matches occur
                    content_lines = result["content"].split('\n')
                    matching_lines = []
                    
                    for i, line in enumerate(content_lines, 1):
                        if query.lower() in line.lower():
                            matching_lines.append({
                                "line_number": i,
                                "content": line.strip()
                            })
                    
                    search_results.append({
                        "workspace": result["workspace"],
                        "filepath": result["filepath"],
                        "file_path": result["filepath"],  # For backward compatibility 
                        "filename": result["filename"],
                        "extension": result["extension"],
                        "score": result.score,
                        "matching_lines": matching_lines[:5]  # Limit to first 5 matches per file
                    })
                
                return search_results
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def _index_file(self, workspace_name: str, file_path: str, content: str):
        """Index a file for search"""
        try:
            index = open_dir(str(self.index_dir))
            writer = index.writer()
            
            # Remove existing entry for this file
            writer.delete_by_term("filepath", f"{workspace_name}/{file_path}")
            
            # Add new entry
            path_obj = Path(file_path)
            writer.add_document(
                workspace=workspace_name,
                filepath=f"{workspace_name}/{file_path}",
                filename=path_obj.name,
                content=content,
                extension=path_obj.suffix.lstrip('.')
            )
            
            writer.commit()
            
        except Exception as e:
            logger.error(f"Indexing error: {e}")

    async def _remove_file_from_index(self, workspace_name: str, file_path: str):
        """Remove a file from the search index"""
        try:
            index = open_dir(str(self.index_dir))
            writer = index.writer()
            writer.delete_by_term("filepath", f"{workspace_name}/{file_path}")
            writer.commit()
        except Exception as e:
            logger.error(f"Index removal error: {e}")

    async def _remove_workspace_from_index(self, workspace_name: str):
        """Remove all files from a workspace from the search index"""
        try:
            index = open_dir(str(self.index_dir))
            writer = index.writer()
            writer.delete_by_term("workspace", workspace_name)
            writer.commit()
        except Exception as e:
            logger.error(f"Workspace index removal error: {e}")

    def _count_files(self, path: Path) -> int:
        """Count files in a directory recursively"""
        count = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    count += 1
        except PermissionError:
            pass
        return count

    def _is_valid_workspace_name(self, name: str) -> bool:
        """Check if workspace name is valid"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name)) and len(name) <= 50

    def get_workspace_path(self, workspace_name: str) -> Path:
        """Get the full path to a workspace"""
        return self.workspaces_dir / workspace_name

    async def clone_workspace_from_git(self, workspace_name: str, git_url: str, branch: Optional[str] = None) -> Dict:
        """
        Clone a Git repository into a new workspace
        
        Args:
            workspace_name: Name for the new workspace
            git_url: Git repository URL to clone
            branch: Optional branch to checkout (defaults to main/master)
            
        Returns:
            Dict with operation results
        """
        if not self._is_valid_workspace_name(workspace_name):
            raise ValueError("Invalid workspace name. Use alphanumeric characters, hyphens, and underscores only.")
        
        if not self._is_valid_git_url(git_url):
            raise ValueError("Invalid Git URL format")
        
        workspace_path = self.workspaces_dir / workspace_name
        
        if workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' already exists")
        
        try:
            logger.info(f"Cloning repository {git_url} into workspace {workspace_name}")
            
            # Clone the repository
            if branch:
                repo = git.Repo.clone_from(git_url, workspace_path, branch=branch)
                logger.info(f"Cloned repository on branch: {branch}")
            else:
                repo = git.Repo.clone_from(git_url, workspace_path)
                logger.info(f"Cloned repository on default branch")
            
            # Get repository information
            repo_info = {
                "remote_url": git_url,
                "active_branch": repo.active_branch.name,
                "latest_commit": {
                    "hash": repo.head.commit.hexsha[:8],
                    "message": repo.head.commit.message.strip(),
                    "author": str(repo.head.commit.author),
                    "date": repo.head.commit.committed_datetime.isoformat()
                }
            }
            
            # Check if it's an SBT project
            build_sbt_exists = (workspace_path / "build.sbt").exists()
            
            # If not an SBT project, we can optionally create basic SBT structure
            # but let's keep the cloned project as-is for now
            
            # Index all cloned files for search
            await self._index_all_files_in_workspace(workspace_name)
            
            logger.info(f"Successfully cloned workspace: {workspace_name}")
            
            return {
                "workspace_name": workspace_name,
                "path": str(workspace_path),
                "cloned": True,
                "git_info": repo_info,
                "is_sbt_project": build_sbt_exists,
                "files_indexed": await self._count_indexed_files(workspace_name)
            }
            
        except git.exc.GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            # Clean up partial clone if it exists
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            raise ValueError(f"Git clone failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error cloning workspace: {e}")
            # Clean up partial clone if it exists
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            raise ValueError(f"Failed to clone workspace: {str(e)}")

    def _is_valid_git_url(self, url: str) -> bool:
        """
        Validate Git repository URL
        
        Args:
            url: Git URL to validate
            
        Returns:
            True if URL appears to be a valid Git repository URL
        """
        try:
            parsed = urlparse(url)
            
            # Check for common Git URL patterns
            git_patterns = [
                # HTTPS Git URLs
                r'^https://[^/]+/[^/]+/[^/]+\.git$',
                r'^https://[^/]+/[^/]+/[^/]+/?$',
                # SSH Git URLs
                r'^git@[^:]+:[^/]+/[^/]+\.git$',
                r'^ssh://git@[^/]+/[^/]+/[^/]+\.git$',
                # Git protocol
                r'^git://[^/]+/[^/]+/[^/]+\.git$'
            ]
            
            for pattern in git_patterns:
                if re.match(pattern, url):
                    return True
            
            # Additional validation for common Git hosting services
            common_hosts = ['github.com', 'gitlab.com', 'bitbucket.org', 'codecommit']
            if parsed.netloc and any(host in parsed.netloc for host in common_hosts):
                return True
            
            return False
            
        except Exception:
            return False

    async def _index_all_files_in_workspace(self, workspace_name: str):
        """
        Index all files in a workspace for search
        
        Args:
            workspace_name: Name of the workspace to index
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            return
        
        # Define file extensions to index (text files)
        indexable_extensions = {
            '.scala', '.java', '.sbt', '.sc', '.py', '.js', '.ts', '.html', '.css',
            '.md', '.txt', '.yml', '.yaml', '.json', '.xml', '.properties', '.conf',
            '.sh', '.sql', '.dockerfile', '.gradle', '.kt', '.rs', '.go', '.rb'
        }
        
        indexed_count = 0
        
        try:
            for file_path in workspace_path.rglob("*"):
                if file_path.is_file():
                    # Skip hidden files and directories, and binary files
                    if (file_path.name.startswith('.') or 
                        file_path.suffix.lower() not in indexable_extensions):
                        continue
                    
                    try:
                        # Read file content
                        async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = await f.read()
                        
                        # Index the file
                        relative_path = file_path.relative_to(workspace_path)
                        await self._index_file(workspace_name, str(relative_path), content)
                        indexed_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to index file {file_path}: {e}")
                        continue
            
            logger.info(f"Indexed {indexed_count} files in workspace {workspace_name}")
            
        except Exception as e:
            logger.error(f"Error indexing workspace files: {e}")

    async def _count_indexed_files(self, workspace_name: str) -> int:
        """
        Count indexed files for a workspace
        
        Args:
            workspace_name: Name of the workspace
            
        Returns:
            Number of indexed files
        """
        try:
            index = open_dir(str(self.index_dir))
            
            with index.searcher() as searcher:
                from whoosh.query import Term
                query = Term("workspace", workspace_name)
                results = searcher.search(query, limit=None)
                return len(results)
                
        except Exception as e:
            logger.error(f"Error counting indexed files: {e}")
            return 0

    async def get_workspace_git_info(self, workspace_name: str) -> Dict:
        """
        Get Git information for a workspace if it's a Git repository
        
        Args:
            workspace_name: Name of the workspace
            
        Returns:
            Dict with Git information or error
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        try:
            repo = git.Repo(workspace_path)
            
            # Check if it's a Git repository
            if repo.bare:
                return {"error": "Workspace is not a valid Git repository"}
            
            git_info = {
                "is_git_repo": True,
                "active_branch": repo.active_branch.name,
                "latest_commit": {
                    "hash": repo.head.commit.hexsha[:8],
                    "full_hash": repo.head.commit.hexsha,
                    "message": repo.head.commit.message.strip(),
                    "author": str(repo.head.commit.author),
                    "date": repo.head.commit.committed_datetime.isoformat()
                },
                "remotes": []
            }
            
            # Get remote information
            for remote in repo.remotes:
                git_info["remotes"].append({
                    "name": remote.name,
                    "url": list(remote.urls)[0] if remote.urls else None
                })
            
            # Get branch information
            branches = []
            for branch in repo.branches:
                branches.append({
                    "name": branch.name,
                    "is_active": branch == repo.active_branch
                })
            git_info["branches"] = branches
            
            # Check for uncommitted changes
            git_info["has_uncommitted_changes"] = repo.is_dirty()
            git_info["untracked_files"] = repo.untracked_files
            
            return git_info
            
        except git.exc.InvalidGitRepositoryError:
            return {
                "is_git_repo": False,
                "error": "Workspace is not a Git repository"
            }
        except Exception as e:
            logger.error(f"Error getting Git info: {e}")
            return {
                "is_git_repo": False,
                "error": f"Failed to get Git information: {str(e)}"
            }

    async def git_checkout_branch(self, workspace_name: str, branch_name: str, create_new: bool = False) -> Dict:
        """
        Checkout a Git branch (optionally create new branch)
        
        Args:
            workspace_name: Name of the workspace
            branch_name: Name of the branch to checkout
            create_new: Whether to create a new branch
            
        Returns:
            Dict with operation results
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        if not self._is_valid_branch_name(branch_name):
            raise ValueError("Invalid branch name")
        
        try:
            repo = git.Repo(workspace_path)
            
            if create_new:
                # Create and checkout new branch
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                logger.info(f"Created and checked out new branch: {branch_name}")
                
                return {
                    "workspace_name": workspace_name,
                    "action": "create_and_checkout",
                    "branch_name": branch_name,
                    "success": True,
                    "message": f"Created and checked out new branch '{branch_name}'"
                }
            else:
                # Checkout existing branch
                repo.git.checkout(branch_name)
                logger.info(f"Checked out existing branch: {branch_name}")
                
                return {
                    "workspace_name": workspace_name,
                    "action": "checkout",
                    "branch_name": branch_name,
                    "success": True,
                    "message": f"Checked out branch '{branch_name}'"
                }
                
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("Workspace is not a Git repository")
        except git.exc.GitCommandError as e:
            logger.error(f"Git checkout failed: {e}")
            raise ValueError(f"Git checkout failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error during Git checkout: {e}")
            raise ValueError(f"Git operation failed: {str(e)}")

    async def git_add_files(self, workspace_name: str, file_paths: List[str] = None) -> Dict:
        """
        Add files to Git staging area
        
        Args:
            workspace_name: Name of the workspace
            file_paths: List of file paths to add (None for all files)
            
        Returns:
            Dict with operation results
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        try:
            repo = git.Repo(workspace_path)
            
            if file_paths:
                # Add specific files
                for file_path in file_paths:
                    if not self._is_safe_file_path(file_path):
                        raise ValueError(f"Invalid file path: {file_path}")
                repo.index.add(file_paths)
                added_files = file_paths
            else:
                # Add all files
                repo.git.add('.')
                added_files = ["all files"]
            
            logger.info(f"Added files to staging: {added_files}")
            
            return {
                "workspace_name": workspace_name,
                "action": "add",
                "files_added": added_files,
                "success": True,
                "message": f"Added {len(added_files)} file(s) to staging area"
            }
            
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("Workspace is not a Git repository")
        except git.exc.GitCommandError as e:
            logger.error(f"Git add failed: {e}")
            raise ValueError(f"Git add failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error during Git add: {e}")
            raise ValueError(f"Git operation failed: {str(e)}")

    async def git_commit(self, workspace_name: str, message: str, author_name: str = None, author_email: str = None) -> Dict:
        """
        Commit staged changes
        
        Args:
            workspace_name: Name of the workspace
            message: Commit message
            author_name: Optional author name
            author_email: Optional author email
            
        Returns:
            Dict with operation results
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        if not message or len(message.strip()) == 0:
            raise ValueError("Commit message cannot be empty")
        
        try:
            repo = git.Repo(workspace_path)
            
            # Set author if provided
            if author_name and author_email:
                author = git.Actor(author_name, author_email)
                commit = repo.index.commit(message, author=author)
            else:
                commit = repo.index.commit(message)
            
            logger.info(f"Created commit: {commit.hexsha[:8]}")
            
            return {
                "workspace_name": workspace_name,
                "action": "commit",
                "commit_hash": commit.hexsha[:8],
                "full_commit_hash": commit.hexsha,
                "message": message,
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "success": True
            }
            
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("Workspace is not a Git repository")
        except git.exc.GitCommandError as e:
            logger.error(f"Git commit failed: {e}")
            raise ValueError(f"Git commit failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error during Git commit: {e}")
            raise ValueError(f"Git operation failed: {str(e)}")

    async def git_push(self, workspace_name: str, remote_name: str = "origin", branch_name: str = None) -> Dict:
        """
        Push changes to remote repository
        
        Args:
            workspace_name: Name of the workspace
            remote_name: Name of the remote (default: origin)
            branch_name: Name of the branch to push (default: current branch)
            
        Returns:
            Dict with operation results
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        try:
            repo = git.Repo(workspace_path)
            
            # Get the remote
            if remote_name not in [r.name for r in repo.remotes]:
                raise ValueError(f"Remote '{remote_name}' not found")
            
            remote = repo.remote(remote_name)
            
            # Determine branch to push
            if not branch_name:
                branch_name = repo.active_branch.name
            
            # Push the branch
            push_info = remote.push(f"{branch_name}:{branch_name}")
            
            logger.info(f"Pushed branch {branch_name} to {remote_name}")
            
            return {
                "workspace_name": workspace_name,
                "action": "push",
                "remote_name": remote_name,
                "branch_name": branch_name,
                "success": True,
                "message": f"Successfully pushed '{branch_name}' to '{remote_name}'"
            }
            
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("Workspace is not a Git repository")
        except git.exc.GitCommandError as e:
            logger.error(f"Git push failed: {e}")
            raise ValueError(f"Git push failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error during Git push: {e}")
            raise ValueError(f"Git operation failed: {str(e)}")

    async def git_pull(self, workspace_name: str, remote_name: str = "origin", branch_name: str = None) -> Dict:
        """
        Pull changes from remote repository
        
        Args:
            workspace_name: Name of the workspace
            remote_name: Name of the remote (default: origin)
            branch_name: Name of the branch to pull (default: current branch)
            
        Returns:
            Dict with operation results
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        try:
            repo = git.Repo(workspace_path)
            
            # Get the remote
            if remote_name not in [r.name for r in repo.remotes]:
                raise ValueError(f"Remote '{remote_name}' not found")
            
            remote = repo.remote(remote_name)
            
            # Determine branch to pull
            if not branch_name:
                branch_name = repo.active_branch.name
            
            # Pull the branch
            pull_info = remote.pull(branch_name)
            
            logger.info(f"Pulled branch {branch_name} from {remote_name}")
            
            # Re-index files after pull (new/modified files)
            await self._index_all_files_in_workspace(workspace_name)
            
            return {
                "workspace_name": workspace_name,
                "action": "pull",
                "remote_name": remote_name,
                "branch_name": branch_name,
                "success": True,
                "message": f"Successfully pulled '{branch_name}' from '{remote_name}'",
                "files_reindexed": True
            }
            
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("Workspace is not a Git repository")
        except git.exc.GitCommandError as e:
            logger.error(f"Git pull failed: {e}")
            raise ValueError(f"Git pull failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error during Git pull: {e}")
            raise ValueError(f"Git operation failed: {str(e)}")

    async def git_status(self, workspace_name: str) -> Dict:
        """
        Get Git status of the workspace
        
        Args:
            workspace_name: Name of the workspace
            
        Returns:
            Dict with Git status information
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        try:
            repo = git.Repo(workspace_path)
            
            # Get status information
            status_info = {
                "workspace_name": workspace_name,
                "current_branch": repo.active_branch.name,
                "is_dirty": repo.is_dirty(),
                "untracked_files": repo.untracked_files,
                "modified_files": [item.a_path for item in repo.index.diff(None)],
                "staged_files": [item.a_path for item in repo.index.diff("HEAD")],
                "ahead_behind": {}
            }
            
            # Check if branch is ahead/behind remote
            try:
                remote_branch = f"origin/{repo.active_branch.name}"
                if remote_branch in [str(ref) for ref in repo.refs]:
                    commits_ahead = list(repo.iter_commits(f"{remote_branch}..HEAD"))
                    commits_behind = list(repo.iter_commits(f"HEAD..{remote_branch}"))
                    status_info["ahead_behind"] = {
                        "ahead": len(commits_ahead),
                        "behind": len(commits_behind)
                    }
            except:
                # Remote tracking info not available
                pass
            
            return status_info
            
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("Workspace is not a Git repository")
        except Exception as e:
            logger.error(f"Error getting Git status: {e}")
            raise ValueError(f"Git operation failed: {str(e)}")

    async def git_log(self, workspace_name: str, limit: int = 10) -> Dict:
        """
        Get Git commit history
        
        Args:
            workspace_name: Name of the workspace
            limit: Number of commits to retrieve
            
        Returns:
            Dict with commit history
        """
        workspace_path = self.workspaces_dir / workspace_name
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        try:
            repo = git.Repo(workspace_path)
            
            commits = []
            for commit in repo.iter_commits(max_count=limit):
                commits.append({
                    "hash": commit.hexsha[:8],
                    "full_hash": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                    "files_changed": len(commit.stats.files)
                })
            
            return {
                "workspace_name": workspace_name,
                "current_branch": repo.active_branch.name,
                "commits": commits,
                "total_commits_shown": len(commits)
            }
            
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("Workspace is not a Git repository")
        except Exception as e:
            logger.error(f"Error getting Git log: {e}")
            raise ValueError(f"Git operation failed: {str(e)}")

    def _is_valid_branch_name(self, branch_name: str) -> bool:
        """Validate Git branch name"""
        if not branch_name or len(branch_name) > 100:
            return False
        
        # Git branch name restrictions
        invalid_chars = ['~', '^', ':', '?', '*', '[', '\\', ' ', '\t', '\n']
        if any(char in branch_name for char in invalid_chars):
            return False
        
        # Cannot start/end with slash or dot
        if branch_name.startswith('/') or branch_name.endswith('/'):
            return False
        if branch_name.startswith('.') or branch_name.endswith('.'):
            return False
        
        # Cannot contain consecutive dots or slashes
        if '..' in branch_name or '//' in branch_name:
            return False
        
        return True

    def _is_safe_file_path(self, file_path: str) -> bool:
        """Validate file path for Git operations"""
        if not file_path:
            return False
        
        # Prevent directory traversal
        if '..' in file_path or file_path.startswith('/'):
            return False
        
        # Basic length check
        if len(file_path) > 500:
            return False
        
        return True 