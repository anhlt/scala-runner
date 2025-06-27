import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from scala_runner.sbt_runner import SBTRunner


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        import shutil
        shutil.rmtree(temp_path)


@pytest.fixture
def sbt_runner():
    """Create an SBTRunner instance for testing"""
    return SBTRunner()


class TestSBTRunner:
    """Test suite for SBTRunner"""

    def test_init(self, sbt_runner):
        """Test SBTRunner initialization"""
        assert sbt_runner.image == "sbtscala/scala-sbt:eclipse-temurin-alpine-21.0.7_6_1.11.2_3.7.1"
        assert sbt_runner.timeout == 120

    def test_is_valid_sbt_command(self, sbt_runner):
        """Test SBT command validation"""
        # Valid commands
        assert sbt_runner._is_valid_sbt_command("compile")
        assert sbt_runner._is_valid_sbt_command("run")
        assert sbt_runner._is_valid_sbt_command("test")
        assert sbt_runner._is_valid_sbt_command("clean")
        assert sbt_runner._is_valid_sbt_command("package")
        assert sbt_runner._is_valid_sbt_command("reload")
        assert sbt_runner._is_valid_sbt_command("publishLocal")
        assert sbt_runner._is_valid_sbt_command("console")
        assert sbt_runner._is_valid_sbt_command("help")
        assert sbt_runner._is_valid_sbt_command("projects")
        assert sbt_runner._is_valid_sbt_command("about")
        assert sbt_runner._is_valid_sbt_command("update")
        assert sbt_runner._is_valid_sbt_command("evicted")
        assert sbt_runner._is_valid_sbt_command("dependencyTree")
        assert sbt_runner._is_valid_sbt_command("assembly")
        assert sbt_runner._is_valid_sbt_command("dist")
        assert sbt_runner._is_valid_sbt_command("stage")
        assert sbt_runner._is_valid_sbt_command("docker")
        assert sbt_runner._is_valid_sbt_command("dockerize")
        
        # Invalid commands
        assert not sbt_runner._is_valid_sbt_command("rm -rf /")
        assert not sbt_runner._is_valid_sbt_command("cat /etc/passwd")
        assert not sbt_runner._is_valid_sbt_command("ls -la")
        assert not sbt_runner._is_valid_sbt_command("")
        assert not sbt_runner._is_valid_sbt_command("invalid_command")

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_sbt_command_success(self, mock_subprocess, sbt_runner, temp_dir):
        """Test successful SBT command execution"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock successful process
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"[success] Total time: 2 s")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        result = await sbt_runner.run_sbt_command(str(workspace_path), "compile")
        
        assert result["status"] == "success"
        assert result["command"] == "compile"
        assert "[success] Total time: 2 s" in result["output"]
        
        # Verify Docker command was called correctly
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        assert args[0] == "docker"
        assert args[1] == "run"
        assert "--rm" in args
        assert f"-v{workspace_path}:/workspace" in args  # Volume mapping with -v prefix
        assert sbt_runner.image in args

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_sbt_command_failure(self, mock_subprocess, sbt_runner, temp_dir):
        """Test SBT command execution failure"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock failed process
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"[error] Compilation failed")
        mock_process.stderr.read = AsyncMock(return_value=b"Error: missing semicolon")
        mock_process.wait = AsyncMock(return_value=1)
        mock_subprocess.return_value = mock_process
        
        result = await sbt_runner.run_sbt_command(str(workspace_path), "compile")
        
        assert result["status"] == "failed"
        assert result["command"] == "compile"
        assert "[error] Compilation failed" in result["output"]
        assert "Error: missing semicolon" in result["stderr"]

    @pytest.mark.asyncio
    async def test_run_sbt_command_invalid_command(self, sbt_runner, temp_dir):
        """Test SBT command execution with invalid command"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        with pytest.raises(ValueError, match="Invalid or potentially dangerous SBT command"):
            await sbt_runner.run_sbt_command(str(workspace_path), "rm -rf /")

    @pytest.mark.asyncio
    async def test_run_sbt_command_nonexistent_workspace(self, sbt_runner):
        """Test SBT command execution with non-existent workspace"""
        with pytest.raises(ValueError, match="Workspace path does not exist"):
            await sbt_runner.run_sbt_command("/nonexistent/path", "compile")

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_sbt_command_timeout(self, mock_subprocess, sbt_runner, temp_dir):
        """Test SBT command execution timeout"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock process that hangs
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.terminate = Mock()
        mock_subprocess.return_value = mock_process
        
        # Set a short timeout for testing
        sbt_runner.timeout = 1
        
        result = await sbt_runner.run_sbt_command(str(workspace_path), "compile")
        
        assert result["status"] == "timeout"
        assert result["command"] == "compile"
        assert "Command timed out" in result["output"]
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_sbt_compile(self, mock_subprocess, sbt_runner, temp_dir):
        """Test SBT compile command"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock successful compilation
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"[info] Compiling 1 Scala source to target/scala-3.3.1/classes...")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        result = await sbt_runner.run_sbt_compile(str(workspace_path))
        
        assert result["status"] == "success"
        assert result["command"] == "compile"

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_sbt_test(self, mock_subprocess, sbt_runner, temp_dir):
        """Test SBT test command"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock successful test run
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"[info] All tests passed")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        result = await sbt_runner.run_sbt_test(str(workspace_path))
        
        assert result["status"] == "success"
        assert result["command"] == "test"

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_sbt_clean(self, mock_subprocess, sbt_runner, temp_dir):
        """Test SBT clean command"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock successful clean
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"[success] Total time: 0 s")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        result = await sbt_runner.run_sbt_clean(str(workspace_path))
        
        assert result["status"] == "success"
        assert result["command"] == "clean"

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_sbt_run_with_main_class(self, mock_subprocess, sbt_runner, temp_dir):
        """Test SBT run command with main class"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock successful run
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"Hello, World!")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        result = await sbt_runner.run_sbt_run(str(workspace_path), main_class="com.example.Main")
        
        assert result["status"] == "success"
        assert result["command"] == 'runMain com.example.Main'

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_run_sbt_run_default(self, mock_subprocess, sbt_runner, temp_dir):
        """Test SBT run command without main class"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock successful run
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"Hello, World!")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        result = await sbt_runner.run_sbt_run(str(workspace_path))
        
        assert result["status"] == "success"
        assert result["command"] == "run"

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_get_sbt_project_info(self, mock_subprocess, sbt_runner, temp_dir):
        """Test getting SBT project information"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Create build.sbt file that the method expects
        build_sbt = workspace_path / "build.sbt"
        build_sbt.write_text('name := "Test Project"')
        
        # Mock project info output
        project_info = """[info] * root
[info]   Description: Test Project
[info]   Provided by: /workspace/build.sbt
[info]   Dependencies:
[info]     - org.scala-lang:scala3-library_3:3.3.1
[info]   Plugins:
[info]     - sbt.plugins.IvyPlugin
[info]     - sbt.plugins.JvmPlugin"""
        
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=project_info.encode())
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        result = await sbt_runner.get_project_info(str(workspace_path))
        
        assert result["status"] == "success"
        assert result["is_sbt_project"] is True
        assert result["has_build_sbt"] is True

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_docker_command_construction(self, mock_subprocess, sbt_runner, temp_dir):
        """Test Docker command construction"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock successful process
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"success")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        await sbt_runner.run_sbt_command(str(workspace_path), "compile")
        
        # Verify Docker command structure
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        
        expected_args = [
            "docker", "run", "--rm", "-it",
            f"-v{workspace_path}:/workspace",
            "-w", "/workspace",
            "--user", f"{os.getuid()}:{os.getgid()}",
            sbt_runner.image,
            "sbt", "compile"
        ]
        
        # Check key components are present
        assert "docker" in args
        assert "run" in args
        assert "--rm" in args
        assert f"-v{workspace_path}:/workspace" in args
        assert sbt_runner.image in args
        assert "sbt" in args
        assert "compile" in args

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_custom_timeout(self, mock_subprocess, sbt_runner, temp_dir):
        """Test custom timeout for SBT commands"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock process that hangs
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.terminate = Mock()
        mock_subprocess.return_value = mock_process
        
        # Test with custom timeout
        result = await sbt_runner.run_sbt_command(str(workspace_path), "compile", timeout=2)
        
        assert result["status"] == "timeout"
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_sbt_command_with_arguments(self, mock_subprocess, sbt_runner, temp_dir):
        """Test SBT command with additional arguments"""
        workspace_path = temp_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        
        # Mock successful process
        mock_process = Mock()
        mock_process.stdout.read = AsyncMock(return_value=b"Success")
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        
        # Test compound command
        result = await sbt_runner.run_sbt_command(str(workspace_path), "clean compile")
        
        assert result["status"] == "success"
        
        # Verify command construction
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        assert "clean" in args
        assert "compile" in args


# Import os for testing user/group ID
import os 