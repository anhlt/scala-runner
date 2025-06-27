import os
import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from .output_process import clean_subprocess_output

logger = logging.getLogger(__name__)


class SBTRunner:
    def __init__(self, docker_image: str = "sbtscala/scala-sbt:eclipse-temurin-alpine-21.0.7_6_1.11.2_3.7.1"):
        self.docker_image = docker_image
        self.timeout = 120  # 2 minutes default timeout

    async def run_sbt_command(
        self, 
        workspace_path, 
        command: str, 
        timeout: Optional[int] = None
    ) -> Dict:
        """
        Run an SBT command in the workspace using Docker
        
        Args:
            workspace_path: Path to the workspace directory (string or Path)
            command: SBT command to run (e.g., "compile", "run", "test")
            timeout: Timeout in seconds (defaults to class timeout)
            
        Returns:
            Dict with execution results
        """
        # Convert to Path if string
        if isinstance(workspace_path, str):
            workspace_path = Path(workspace_path)
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {workspace_path}")
        
        # Validate SBT command
        if not self._is_valid_sbt_command(command):
            raise ValueError(f"Invalid or potentially dangerous SBT command: {command}")
        
        # Build Docker command
        # Split compound commands like "clean compile" into separate arguments
        sbt_commands = command.split()
        
        docker_cmd = [
            "docker", "run", "--rm",
            "--platform", "linux/amd64",
            f"-v{workspace_path}:/workspace",
            f"-v/tmp/sbt-cache:/root/.sbt",
            f"-v/tmp/ivy-cache:/root/.ivy2",
            f"-v/tmp/coursier-cache:/root/.cache/coursier",
            "-w", "/workspace",
            self.docker_image,
            "sbt"
        ] + sbt_commands
        
        logger.info(f"Running SBT command: {' '.join(docker_cmd)}")
        
        try:
            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                # Read stdout and stderr separately for better test compatibility
                stdout = await process.stdout.read() if process.stdout else b""
                stderr = await process.stderr.read() if process.stderr else b""
                
                # Wait for process to complete with timeout
                exit_code = await asyncio.wait_for(process.wait(), timeout=timeout or self.timeout)
                
            except asyncio.TimeoutError:
                # Kill the process if it's still running
                process.terminate()
                try:
                    await process.wait()
                except:
                    pass
                
                return {
                    "command": command,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": [f"Command timed out after {timeout or self.timeout} seconds"],
                    "output": f"Command timed out after {timeout or self.timeout} seconds",
                    "success": False,
                    "timeout": True,
                    "status": "timeout"
                }
            
            # Process output
            out_text = stdout.decode(errors="ignore")
            err_lines = clean_subprocess_output(stderr.decode(errors="ignore"))
            
            result = {
                "command": command,
                "exit_code": exit_code,
                "stdout": out_text,
                "stderr": err_lines,
                "output": out_text,  # For test compatibility
                "success": exit_code == 0,
                "status": "success" if exit_code == 0 else "failed"
            }
            
            if exit_code == 0:
                logger.info(f"SBT command '{command}' completed successfully")
            else:
                logger.error(f"SBT command '{command}' failed with exit code {exit_code}")
                logger.error(f"STDOUT: {out_text}")
                logger.error(f"STDERR: {err_lines}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error running SBT command '{command}': {e}")
            return {
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": [f"Error: {str(e)}"],
                "success": False,
                "error": str(e),
                "status": "error"
            }

    async def compile_project(self, workspace_path: Path) -> Dict:
        """Compile the SBT project"""
        return await self.run_sbt_command(workspace_path, "compile")

    async def run_project(self, workspace_path: Path, main_class: Optional[str] = None) -> Dict:
        """Run the SBT project"""
        command = "run"
        if main_class:
            command = f'runMain {main_class}'
        return await self.run_sbt_command(workspace_path, command)

    async def test_project(self, workspace_path: Path, test_name: Optional[str] = None) -> Dict:
        """Run tests in the SBT project"""
        command = "test"
        if test_name:
            command = f'testOnly {test_name}'
        return await self.run_sbt_command(workspace_path, command)

    async def clean_project(self, workspace_path: Path) -> Dict:
        """Clean the SBT project"""
        return await self.run_sbt_command(workspace_path, "clean")

    async def package_project(self, workspace_path: Path) -> Dict:
        """Package the SBT project"""
        return await self.run_sbt_command(workspace_path, "package")

    async def show_dependencies(self, workspace_path: Path) -> Dict:
        """Show project dependencies"""
        return await self.run_sbt_command(workspace_path, "dependencyTree")

    async def reload_project(self, workspace_path: Path) -> Dict:
        """Reload the SBT project (useful after build.sbt changes)"""
        return await self.run_sbt_command(workspace_path, "reload")

    async def console(self, workspace_path: Path) -> Dict:
        """Start SBT console (interactive mode not supported in this context)"""
        return {
            "command": "console",
            "exit_code": -1,
            "stdout": "",
            "stderr": ["Interactive console mode is not supported in this API"],
            "success": False,
            "error": "Interactive mode not supported"
        }

    def _is_valid_sbt_command(self, command: str) -> bool:
        """
        Validate SBT command to prevent dangerous operations
        
        Args:
            command: The SBT command to validate
            
        Returns:
            True if command is safe, False otherwise
        """
        # List of allowed SBT commands and patterns
        allowed_commands = {
            "compile", "run", "test", "clean", "package", "reload", "update",
            "dependencyTree", "dependencies", "projects", "project", "help",
            "console", "assembly", "publishLocal", "doc", "scaladoc", "about", 
            "evicted", "dist", "stage", "docker", "dockerize"
        }
        
        # Allow runMain with class name
        if command.startswith("runMain "):
            class_name = command.split(" ", 1)[1].strip()
            # Basic validation for class name (should not contain dangerous characters)
            if self._is_valid_class_name(class_name):
                return True
        
        # Allow testOnly with test name
        if command.startswith("testOnly "):
            test_name = command.split(" ", 1)[1].strip()
            if self._is_valid_class_name(test_name):
                return True
        
        # Allow project switching
        if command.startswith("project "):
            project_name = command.split(" ", 1)[1].strip()
            if self._is_valid_project_name(project_name):
                return True
        
        # Check if command is in allowed list
        base_command = command.split()[0] if command.split() else ""
        
        # Prevent dangerous commands
        dangerous_patterns = [
            "!", "shell", "exit", "quit", "; rm", "; delete", "rm -", "del ",
            "format", "shutdown", "eval System.exit"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                return False
        
        return base_command in allowed_commands

    def _is_valid_class_name(self, class_name: str) -> bool:
        """Validate Java/Scala class name"""
        import re
        # Allow qualified class names with dots, but no dangerous characters
        pattern = r'^[a-zA-Z][a-zA-Z0-9_.]*[a-zA-Z0-9]$'
        return bool(re.match(pattern, class_name)) and len(class_name) <= 200

    def _is_valid_project_name(self, project_name: str) -> bool:
        """Validate SBT project name"""
        import re
        pattern = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
        return bool(re.match(pattern, project_name)) and len(project_name) <= 50

    async def get_project_info(self, workspace_path) -> Dict:
        """Get basic project information"""
        try:
            # Convert to Path if string
            if isinstance(workspace_path, str):
                workspace_path = Path(workspace_path)
            
            # Check if build.sbt exists
            build_sbt = workspace_path / "build.sbt"
            if not build_sbt.exists():
                            return {
                "error": "No build.sbt file found",
                "is_sbt_project": False,
                "status": "error"
            }
            
            # Get project structure info
            src_main_scala = workspace_path / "src" / "main" / "scala"
            src_test_scala = workspace_path / "src" / "test" / "scala"
            
            info = {
                "is_sbt_project": True,
                "has_build_sbt": True,
                "src_main_scala_exists": src_main_scala.exists(),
                "src_test_scala_exists": src_test_scala.exists(),
                "scala_files": [],
                "status": "success"
            }
            
            # Count Scala files
            if src_main_scala.exists():
                scala_files = list(src_main_scala.rglob("*.scala"))
                info["scala_files"] = [str(f.relative_to(workspace_path)) for f in scala_files]
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting project info: {e}")
            return {
                "error": str(e),
                "is_sbt_project": False,
                "status": "error"
            }

    # Test-expected method aliases
    async def run_sbt_compile(self, workspace_path) -> Dict:
        """Compile the SBT project (test alias)"""
        return await self.run_sbt_command(workspace_path, "compile")

    async def run_sbt_test(self, workspace_path) -> Dict:
        """Run tests in the SBT project (test alias)"""
        return await self.run_sbt_command(workspace_path, "test")

    async def run_sbt_clean(self, workspace_path) -> Dict:
        """Clean the SBT project (test alias)"""
        return await self.run_sbt_command(workspace_path, "clean")

    async def run_sbt_run(self, workspace_path, main_class: Optional[str] = None) -> Dict:
        """Run the SBT project (test alias)"""
        command = "run"
        if main_class:
            command = f'runMain {main_class}'
        return await self.run_sbt_command(workspace_path, command)

    async def get_sbt_project_info(self, workspace_path) -> Dict:
        """Get SBT project information (test alias)"""
        return await self.get_project_info(workspace_path)

    @property
    def image(self) -> str:
        """Docker image property (for test compatibility)"""
        return self.docker_image