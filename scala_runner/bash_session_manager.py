import os
import asyncio
import logging
import uuid
import signal
from pathlib import Path
from typing import Dict, List, Optional, Any
from .output_process import clean_subprocess_output
import time
import platform

logger = logging.getLogger(__name__)


class BashSession:
    """Represents a single bash session running in Docker"""
    
    def __init__(self, session_id: str, workspace_name: str, workspace_path: Path, docker_image: str = "sbtscala/scala-sbt:eclipse-temurin-alpine-21.0.7_6_1.11.2_3.7.1"):
        self.session_id = session_id
        self.workspace_name = workspace_name
        self.workspace_path = workspace_path
        self.docker_image = docker_image
        self.process: Optional[asyncio.subprocess.Process] = None
        self.created_at = time.time()
        self.last_used = time.time()
        self._is_active = False

    def _get_docker_platform_args(self):
        """Get appropriate Docker platform arguments based on the host architecture"""
        host_arch = platform.machine().lower()
        
        # Force linux/amd64 in CI or if explicitly requested
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or os.getenv("FORCE_AMD64"):
            return ["--platform", "linux/amd64"]
        
        # For ARM Macs, use ARM64 but fall back to amd64 if the image doesn't support it
        if host_arch in ("arm64", "aarch64") and platform.system() == "Darwin":
            # Try ARM64 first for better performance
            return ["--platform", "linux/arm64"]
        
        # For other architectures, use amd64 as default
        return ["--platform", "linux/amd64"]

    async def start(self) -> Dict:
        """Start the bash session in Docker container"""
        try:
            container_name = f"bash-session-{self.session_id}"
            
            # Get platform arguments
            platform_args = self._get_docker_platform_args()
            
            # Build Docker command with platform support and JVM stability options
            docker_cmd = [
                "docker", "run", "-dit",
                "--name", container_name,
                "-v", f"{self.workspace_path}:/workspace",
                "-v", "/tmp/sbt-cache:/root/.sbt",
                "-v", "/tmp/ivy-cache:/root/.ivy2", 
                "-v", "/tmp/coursier-cache:/root/.cache/coursier",
                "-w", "/workspace",
                # Add JVM options for stability and ARM compatibility
                "-e", "JAVA_OPTS=-Xmx2g -Xms512m -XX:+UseG1GC -XX:+UnlockExperimentalVMOptions -XX:+UseContainerSupport",
                "-e", "SBT_OPTS=-Xmx2g -Xms512m -XX:+UseG1GC",
            ] + platform_args + [
                self.docker_image,
                "/bin/bash"
            ]
            
            logger.info(f"Starting bash session with command: {' '.join(docker_cmd)}")
            
            # Start the container
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.process = process
            self._is_active = True
            
            # Wait a moment for container to start
            await asyncio.sleep(1)
            
            # Test the session with a simple command
            test_result = await self.execute_command("echo 'session_ready'", timeout=10)
            if not test_result.get("success", False):
                await self.close()
                return {
                    "session_id": self.session_id,
                    "workspace_name": self.workspace_name,
                    "status": "failed",
                    "error": "Failed to establish bash session"
                }
            
            logger.info(f"Started bash session {self.session_id}")
            
            return {
                "session_id": self.session_id,
                "workspace_name": self.workspace_name,
                "workspace_path": str(self.workspace_path),
                "status": "started"
            }
            
        except Exception as e:
            logger.error(f"Error starting bash session {self.session_id}: {e}")
            self._is_active = False
            return {
                "session_id": self.session_id,
                "workspace_name": self.workspace_name,
                "status": "error",
                "error": str(e)
            }

    async def execute_command(self, command: str, timeout: int = 30) -> Dict:
        """Execute a command in the bash session"""
        if not self._is_active:
            return {
                "session_id": self.session_id,
                "command": command,
                "status": "error",
                "output": "",
                "stderr": ["Session is not active"],
                "success": False,
                "error": "Session is not active"
            }
        
        try:
            self.last_used = time.time()
            
            container_name = f"bash-session-{self.session_id}"
            session_state_file = f"/tmp/.bash_session_state_{self.session_id}"
            
            # Create a script that sources previous session state and saves new state
            script_content = f'''#!/bin/bash
set -e

# Enable alias expansion in non-interactive shells
shopt -s expand_aliases

# Start in workspace directory
cd /workspace

# Source previous session state if it exists
if [ -f {session_state_file} ]; then
    source {session_state_file}
fi

# Change to the saved working directory if it exists
if [ ! -z "$SAVED_PWD" ] && [ -d "$SAVED_PWD" ]; then
    cd "$SAVED_PWD"
fi

# Execute the command
{command}

# Save current environment and shell state for next command
{{
    # Save current working directory
    echo "export SAVED_PWD=\"$(pwd)\""
    # Export all environment variables except PWD, OLDPWD, and SAVED_PWD (these are managed by our script)
    export -p | grep -v "declare -x PWD=" | grep -v "declare -x OLDPWD=" | grep -v "declare -x SAVED_PWD="
    # Export all shell functions
    declare -f
    # Export all aliases
    alias
}} > {session_state_file} 2>/dev/null || true
'''
            
            # Use docker exec with bash to run the script
            docker_exec_cmd = [
                "docker", "exec", "-i", container_name,
                "/bin/bash", "-c", script_content
            ]
            
            logger.info(f"Executing command in session {self.session_id}: {command}")
            
            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *docker_exec_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Wait for command completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                exit_code = process.returncode
                
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.terminate()
                try:
                    await process.wait()
                except:
                    pass
                    
                return {
                    "session_id": self.session_id,
                    "command": command,
                    "status": "timeout",
                    "output": f"Command timed out after {timeout} seconds",
                    "stderr": [],
                    "success": False,
                    "timeout": True
                }
            
            # Process output
            output_text = stdout.decode(errors="ignore").strip()
            stderr_lines = []
            if stderr:
                stderr_text = stderr.decode(errors="ignore").strip()
                if stderr_text:
                    stderr_lines = stderr_text.split('\n')
            
            success = exit_code == 0
            status = "success" if success else "failed"
            
            logger.info(f"Executed command '{command}' in session {self.session_id} - Status: {status}")
            
            return {
                "session_id": self.session_id,
                "command": command,
                "status": status,
                "output": output_text,
                "stderr": stderr_lines,
                "success": success,
                "workspace_name": self.workspace_name,
                "exit_code": exit_code
            }
            
        except Exception as e:
            logger.error(f"Error executing command '{command}' in session {self.session_id}: {e}")
            return {
                "session_id": self.session_id,
                "command": command,
                "status": "error",
                "output": "",
                "stderr": [str(e)],
                "success": False,
                "error": str(e)
            }

    async def close(self) -> Dict:
        """Close the bash session and Docker container"""
        try:
            if self._is_active:
                container_name = f"bash-session-{self.session_id}"
                session_state_file = f"/tmp/.bash_session_state_{self.session_id}"
                
                # Clean up session state file
                try:
                    cleanup_cmd = [
                        "docker", "exec", container_name,
                        "rm", "-f", session_state_file
                    ]
                    cleanup_process = await asyncio.create_subprocess_exec(
                        *cleanup_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await asyncio.wait_for(cleanup_process.wait(), timeout=5)
                except Exception:
                    pass  # File might not exist, that's fine
                
                # Stop and remove the Docker container
                try:
                    stop_process = await asyncio.create_subprocess_exec(
                        "docker", "stop", container_name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await asyncio.wait_for(stop_process.wait(), timeout=10)
                    
                    # Remove the container
                    rm_process = await asyncio.create_subprocess_exec(
                        "docker", "rm", container_name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await asyncio.wait_for(rm_process.wait(), timeout=5)
                    
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"Error cleaning up container {container_name}: {e}")
                    # Try force removal
                    try:
                        force_rm_process = await asyncio.create_subprocess_exec(
                            "docker", "rm", "-f", container_name,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        await asyncio.wait_for(force_rm_process.wait(), timeout=5)
                    except Exception:
                        pass  # Container might already be gone
                
                self._is_active = False
                logger.info(f"Closed bash session {self.session_id}")
                
                return {
                    "session_id": self.session_id,
                    "workspace_name": self.workspace_name,
                    "status": "closed"
                }
            else:
                return {
                    "session_id": self.session_id,
                    "workspace_name": self.workspace_name,
                    "status": "already_closed"
                }
                
        except Exception as e:
            logger.error(f"Error closing session {self.session_id}: {e}")
            return {
                "session_id": self.session_id,
                "workspace_name": self.workspace_name,
                "status": "error",
                "error": str(e)
            }

    @property
    def is_active(self) -> bool:
        """Check if the session is active"""
        return self._is_active

    def get_info(self) -> Dict:
        """Get session information"""
        return {
            "session_id": self.session_id,
            "workspace_name": self.workspace_name,
            "workspace_path": str(self.workspace_path),
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "uptime": time.time() - self.created_at if self.is_active else 0
        }


class BashSessionManager:
    """Manages multiple bash sessions across workspaces"""
    
    def __init__(self, 
                 workspace_manager, 
                 docker_image: str = "sbtscala/scala-sbt:eclipse-temurin-alpine-21.0.7_6_1.11.2_3.7.1",
                 session_timeout: int = 3600,  # 1 hour default timeout
                 cleanup_interval: int = 300,  # 5 minutes default cleanup interval
                 auto_cleanup_enabled: bool = True):
        self.workspace_manager = workspace_manager
        self.docker_image = docker_image
        self.sessions: Dict[str, BashSession] = {}
        self.sessions_by_workspace: Dict[str, List[str]] = {}
        self.max_sessions_per_workspace = 5
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        self.auto_cleanup_enabled = auto_cleanup_enabled
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event: Optional[asyncio.Event] = None
        
    async def create_session(self, workspace_name: str) -> Dict:
        """Create a new bash session for a workspace"""
        # Validate workspace exists
        workspace_path = self.workspace_manager.get_workspace_path(workspace_name)
        if not workspace_path.exists():
            raise ValueError(f"Workspace '{workspace_name}' not found")
        
        # Check session limits
        workspace_sessions = self.sessions_by_workspace.get(workspace_name, [])
        if len(workspace_sessions) >= self.max_sessions_per_workspace:
            raise ValueError(f"Maximum number of sessions ({self.max_sessions_per_workspace}) reached for workspace '{workspace_name}'")
        
        # Generate unique session ID
        session_id = f"bash_{workspace_name}_{uuid.uuid4().hex[:8]}"
        
        # Create session with Docker image
        session = BashSession(session_id, workspace_name, workspace_path, self.docker_image)
        result = await session.start()
        
        if result.get("status") == "started":
            # Store session
            self.sessions[session_id] = session
            if workspace_name not in self.sessions_by_workspace:
                self.sessions_by_workspace[workspace_name] = []
            self.sessions_by_workspace[workspace_name].append(session_id)
            
            logger.info(f"Created bash session {session_id} for workspace {workspace_name}")
        
        return result

    async def execute_command(self, session_id: str, command: str, timeout: int = 30) -> Dict:
        """Execute a command in an existing session"""
        # Validate command
        if not self._is_safe_command(command):
            raise ValueError(f"Unsafe command detected: {command}")
        
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        
        if not session.is_active:
            raise ValueError(f"Session '{session_id}' is not active")
        
        return await session.execute_command(command, timeout)

    async def close_session(self, session_id: str) -> Dict:
        """Close a specific session"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        
        result = await session.close()
        
        # Remove from tracking
        if session_id in self.sessions:
            workspace_name = session.workspace_name
            del self.sessions[session_id]
            
            if workspace_name in self.sessions_by_workspace:
                self.sessions_by_workspace[workspace_name].remove(session_id)
                if not self.sessions_by_workspace[workspace_name]:
                    del self.sessions_by_workspace[workspace_name]
        
        return result

    async def close_workspace_sessions(self, workspace_name: str) -> Dict:
        """Close all sessions for a workspace"""
        workspace_sessions = self.sessions_by_workspace.get(workspace_name, []).copy()
        results = []
        
        for session_id in workspace_sessions:
            try:
                result = await self.close_session(session_id)
                results.append(result)
            except Exception as e:
                results.append({
                    "session_id": session_id,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "workspace_name": workspace_name,
            "closed_sessions": len(results),
            "results": results
        }

    def list_sessions(self, workspace_name: Optional[str] = None) -> Dict:
        """List all sessions or sessions for a specific workspace"""
        if workspace_name:
            session_ids = self.sessions_by_workspace.get(workspace_name, [])
            sessions_info = [self.sessions[sid].get_info() for sid in session_ids if sid in self.sessions]
        else:
            sessions_info = [session.get_info() for session in self.sessions.values()]
        
        return {
            "workspace_name": workspace_name,
            "total_sessions": len(sessions_info),
            "sessions": sessions_info
        }

    def get_session_info(self, session_id: str) -> Dict:
        """Get detailed information about a specific session"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found")
        
        return session.get_info()

    async def cleanup_inactive_sessions(self) -> Dict:
        """Clean up inactive or timed-out sessions"""
        current_time = time.time()
        cleaned_sessions = []
        
        for session_id, session in list(self.sessions.items()):
            # Check if session is inactive or timed out
            inactive_time = current_time - session.last_used
            if (not session.is_active or inactive_time > self.session_timeout):
                try:
                    logger.info(f"Cleaning up inactive session {session_id} (inactive for {inactive_time:.1f}s)")
                    await self.close_session(session_id)
                    cleaned_sessions.append({
                        "session_id": session_id,
                        "workspace_name": session.workspace_name,
                        "inactive_time": inactive_time,
                        "reason": "inactive" if session.is_active else "not_active"
                    })
                except Exception as e:
                    logger.error(f"Error cleaning up session {session_id}: {e}")
        
        if cleaned_sessions:
            logger.info(f"Cleaned up {len(cleaned_sessions)} inactive sessions")
        
        return {
            "cleaned_sessions": len(cleaned_sessions),
            "sessions": cleaned_sessions,
            "cleanup_time": current_time,
            "session_timeout": self.session_timeout
        }

    async def start_auto_cleanup(self) -> Dict:
        """Start the automatic cleanup background task"""
        if self._cleanup_task and not self._cleanup_task.done():
            return {
                "status": "already_running",
                "message": "Auto-cleanup task is already running"
            }
        
        if not self.auto_cleanup_enabled:
            return {
                "status": "disabled",
                "message": "Auto-cleanup is disabled"
            }
        
        # Create a new event for this session
        self._shutdown_event = asyncio.Event()
        self._cleanup_task = asyncio.create_task(self._auto_cleanup_task())
        logger.info(f"Started auto-cleanup task (interval: {self.cleanup_interval}s, timeout: {self.session_timeout}s)")
        
        return {
            "status": "started",
            "cleanup_interval": self.cleanup_interval,
            "session_timeout": self.session_timeout,
            "message": "Auto-cleanup task started successfully"
        }

    async def stop_auto_cleanup(self) -> Dict:
        """Stop the automatic cleanup background task"""
        if not self._cleanup_task or self._cleanup_task.done():
            return {
                "status": "not_running",
                "message": "Auto-cleanup task is not running"
            }
        
        if self._shutdown_event:
            self._shutdown_event.set()
        
        try:
            # Wait for the task to finish gracefully
            await asyncio.wait_for(self._cleanup_task, timeout=5)
        except asyncio.TimeoutError:
            # Force cancel the task if it doesn't finish within timeout
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped auto-cleanup task")
        
        return {
            "status": "stopped",
            "message": "Auto-cleanup task stopped successfully"
        }

    async def _auto_cleanup_task(self) -> None:
        """Background task that periodically cleans up inactive sessions"""
        logger.info(f"Auto-cleanup task started (interval: {self.cleanup_interval}s)")
        
        # Ensure we have a shutdown event
        if not self._shutdown_event:
            self._shutdown_event = asyncio.Event()
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for the cleanup interval or shutdown event
                await asyncio.wait_for(
                    self._shutdown_event.wait(), 
                    timeout=self.cleanup_interval
                )
                # If we reach here, shutdown was requested
                break
                
            except asyncio.TimeoutError:
                # Timeout occurred, time to run cleanup
                try:
                    if self.sessions:  # Only run cleanup if there are sessions
                        logger.debug(f"Running auto-cleanup (current sessions: {len(self.sessions)})")
                        result = await self.cleanup_inactive_sessions()
                        
                        if result["cleaned_sessions"] > 0:
                            logger.info(f"Auto-cleanup completed: {result['cleaned_sessions']} sessions cleaned")
                    
                except Exception as e:
                    logger.error(f"Error during auto-cleanup: {e}")
                
            except Exception as e:
                logger.error(f"Unexpected error in auto-cleanup task: {e}")
                break
        
        logger.info("Auto-cleanup task finished")

    def configure_cleanup(self, 
                         session_timeout: Optional[int] = None,
                         cleanup_interval: Optional[int] = None,
                         auto_cleanup_enabled: Optional[bool] = None) -> Dict:
        """Configure cleanup settings"""
        old_settings = {
            "session_timeout": self.session_timeout,
            "cleanup_interval": self.cleanup_interval,
            "auto_cleanup_enabled": self.auto_cleanup_enabled
        }
        
        if session_timeout is not None:
            if session_timeout <= 0:
                raise ValueError("Session timeout must be positive")
            self.session_timeout = session_timeout
        
        if cleanup_interval is not None:
            if cleanup_interval <= 0:
                raise ValueError("Cleanup interval must be positive")
            self.cleanup_interval = cleanup_interval
        
        if auto_cleanup_enabled is not None:
            self.auto_cleanup_enabled = auto_cleanup_enabled
        
        new_settings = {
            "session_timeout": self.session_timeout,
            "cleanup_interval": self.cleanup_interval,
            "auto_cleanup_enabled": self.auto_cleanup_enabled
        }
        
        logger.info(f"Updated cleanup configuration: {new_settings}")
        
        return {
            "status": "updated",
            "old_settings": old_settings,
            "new_settings": new_settings,
            "message": "Cleanup configuration updated successfully"
        }

    def get_cleanup_stats(self) -> Dict:
        """Get cleanup configuration and statistics"""
        current_time = time.time()
        active_sessions = sum(1 for session in self.sessions.values() if session.is_active)
        inactive_sessions = len(self.sessions) - active_sessions
        
        # Calculate sessions that will be cleaned up soon
        sessions_to_cleanup = []
        for session_id, session in self.sessions.items():
            inactive_time = current_time - session.last_used
            if inactive_time > self.session_timeout or not session.is_active:
                sessions_to_cleanup.append({
                    "session_id": session_id,
                    "workspace_name": session.workspace_name,
                    "inactive_time": inactive_time,
                    "will_cleanup": True
                })
        
        return {
            "configuration": {
                "session_timeout": self.session_timeout,
                "cleanup_interval": self.cleanup_interval,
                "auto_cleanup_enabled": self.auto_cleanup_enabled,
                "max_sessions_per_workspace": self.max_sessions_per_workspace
            },
            "statistics": {
                "total_sessions": len(self.sessions),
                "active_sessions": active_sessions,
                "inactive_sessions": inactive_sessions,
                "sessions_to_cleanup": len(sessions_to_cleanup),
                "workspaces_with_sessions": len(self.sessions_by_workspace)
            },
            "auto_cleanup_task": {
                "running": self._cleanup_task is not None and not self._cleanup_task.done(),
                "task_status": "running" if (self._cleanup_task and not self._cleanup_task.done()) else "stopped"
            },
            "sessions_pending_cleanup": sessions_to_cleanup
        }

    def _is_safe_command(self, command: str) -> bool:
        """Check if a command is safe to execute"""
        # Prevent dangerous commands
        dangerous_patterns = [
            "rm -rf /",
            ":(){ :|:& };:",  # Fork bomb
            "sudo",
            "su ",
            "chmod 777",
            "mkfs",
            "dd if=",
            "shutdown",
            "reboot",
            "halt",
            "poweroff",
            "init 0",
            "init 6",
            "/dev/",
            ">/dev/",
            "curl.*|.*sh",
            "wget.*|.*sh",
        ]
        
        command_lower = command.lower().strip()
        
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return False
        
        # Additional checks for suspicious patterns
        if (command_lower.startswith("rm ") and ("-rf" in command_lower or "-fr" in command_lower)):
            return False
        
        return True 