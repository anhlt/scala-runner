import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import git
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID

from scala_runner.workspace_manager import WorkspaceManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def workspace_manager(temp_dir):
    """Create a WorkspaceManager instance for testing"""
    return WorkspaceManager(base_dir=str(temp_dir))


@pytest.fixture
def mock_git_repo():
    """Mock git repository for testing"""
    mock_repo = Mock(spec=git.Repo)
    mock_repo.active_branch.name = "main"
    mock_repo.head.commit.hexsha = "abcdef1234567890" * 2 + "abcdef12"
    mock_repo.head.commit.message = "Test commit message"
    mock_repo.head.commit.author = "Test Author <test@example.com>"
    mock_repo.head.commit.committed_datetime.isoformat.return_value = "2024-01-15T10:30:00+00:00"
    mock_repo.remotes = []
    mock_repo.branches = []
    mock_repo.is_dirty.return_value = False
    mock_repo.untracked_files = []
    return mock_repo


class TestWorkspaceManager:
    """Test suite for WorkspaceManager"""

    def test_init(self, temp_dir):
        """Test WorkspaceManager initialization"""
        wm = WorkspaceManager(base_dir=str(temp_dir))
        assert wm.base_dir == temp_dir
        assert wm.workspaces_dir == temp_dir / "workspaces"
        assert wm.index_dir == temp_dir / "search_index"
        assert wm.workspaces_dir.exists()
        assert wm.index_dir.exists()

    @pytest.mark.asyncio
    async def test_create_workspace_success(self, workspace_manager):
        """Test successful workspace creation"""
        workspace_name = "test-workspace"
        
        result = await workspace_manager.create_workspace(workspace_name)
        
        assert result["workspace_name"] == workspace_name
        assert result["created"] is True
        assert Path(result["path"]).exists()
        
        # Check SBT structure was created
        workspace_path = Path(result["path"])
        assert (workspace_path / "build.sbt").exists()
        assert (workspace_path / "src" / "main" / "scala").exists()
        assert (workspace_path / "src" / "test" / "scala").exists()
        assert (workspace_path / "project").exists()

    @pytest.mark.asyncio
    async def test_create_workspace_invalid_name(self, workspace_manager):
        """Test workspace creation with invalid name"""
        with pytest.raises(ValueError, match="Invalid workspace name"):
            await workspace_manager.create_workspace("invalid/name")

    @pytest.mark.asyncio
    async def test_create_workspace_already_exists(self, workspace_manager):
        """Test workspace creation when workspace already exists"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        with pytest.raises(ValueError, match="already exists"):
            await workspace_manager.create_workspace(workspace_name)

    def test_list_workspaces(self, workspace_manager):
        """Test listing workspaces"""
        # Initially empty
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 0
        
        # Create a workspace manually
        workspace_path = workspace_manager.workspaces_dir / "test-workspace"
        workspace_path.mkdir(parents=True)
        (workspace_path / "test.txt").write_text("test")
        
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 1
        assert workspaces[0]["name"] == "test-workspace"
        assert workspaces[0]["files_count"] == 1

    @pytest.mark.asyncio
    async def test_delete_workspace(self, workspace_manager):
        """Test workspace deletion"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        result = await workspace_manager.delete_workspace(workspace_name)
        
        assert result["workspace_name"] == workspace_name
        assert result["deleted"] is True
        assert not workspace_manager.get_workspace_path(workspace_name).exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_workspace(self, workspace_manager):
        """Test deleting a workspace that doesn't exist"""
        with pytest.raises(ValueError, match="not found"):
            await workspace_manager.delete_workspace("nonexistent")

    @pytest.mark.asyncio
    async def test_get_file_tree(self, workspace_manager):
        """Test getting file tree structure"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        result = await workspace_manager.get_file_tree(workspace_name)
        
        assert result["workspace_name"] == workspace_name
        assert "tree" in result
        assert result["tree"]["type"] == "directory"
        assert "children" in result["tree"]

    @pytest.mark.asyncio
    async def test_create_file(self, workspace_manager):
        """Test file creation"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        file_path = "src/main/scala/Test.scala"
        content = "object Test extends App { println(\"Hello\") }"
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.create_file(workspace_name, file_path, content)
        
        assert result["workspace_name"] == workspace_name
        assert result["file_path"] == file_path
        assert result["created"] is True
        
        # Verify file was created
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        assert full_path.exists()
        assert full_path.read_text() == content

    @pytest.mark.asyncio
    async def test_update_file(self, workspace_manager):
        """Test file update"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        file_path = "src/main/scala/Test.scala"
        original_content = "object Test extends App { println(\"Hello\") }"
        updated_content = "object Test extends App { println(\"Updated\") }"
        
        # Create file first
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(original_content)
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.update_file(workspace_name, file_path, updated_content)
        
        assert result["updated"] is True
        assert full_path.read_text() == updated_content

    @pytest.mark.asyncio
    async def test_delete_file(self, workspace_manager):
        """Test file deletion"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        file_path = "src/main/scala/Test.scala"
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("test content")
        
        with patch.object(workspace_manager, '_remove_file_from_index', new_callable=AsyncMock):
            result = await workspace_manager.delete_file(workspace_name, file_path)
        
        assert result["deleted"] is True
        assert not full_path.exists()

    @pytest.mark.asyncio
    async def test_get_file_content(self, workspace_manager):
        """Test getting file content"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        file_path = "src/main/scala/Test.scala"
        content = "object Test extends App { println(\"Hello\") }"
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        
        result = await workspace_manager.get_file_content(workspace_name, file_path)
        
        assert result["workspace_name"] == workspace_name
        assert result["file_path"] == file_path
        assert result["content"] == content
        assert result["extension"] == "scala"

    def test_is_valid_workspace_name(self, workspace_manager):
        """Test workspace name validation"""
        assert workspace_manager._is_valid_workspace_name("valid-name")
        assert workspace_manager._is_valid_workspace_name("valid_name")
        assert workspace_manager._is_valid_workspace_name("validname123")
        
        assert not workspace_manager._is_valid_workspace_name("invalid/name")
        assert not workspace_manager._is_valid_workspace_name("invalid name")
        assert not workspace_manager._is_valid_workspace_name("")
        assert not workspace_manager._is_valid_workspace_name("a" * 51)  # Too long

    def test_is_valid_git_url(self, workspace_manager):
        """Test Git URL validation"""
        # Valid URLs
        assert workspace_manager._is_valid_git_url("https://github.com/user/repo.git")
        assert workspace_manager._is_valid_git_url("https://github.com/user/repo")
        assert workspace_manager._is_valid_git_url("git@github.com:user/repo.git")
        assert workspace_manager._is_valid_git_url("https://gitlab.com/user/repo.git")
        
        # Invalid URLs
        assert not workspace_manager._is_valid_git_url("not-a-url")
        assert not workspace_manager._is_valid_git_url("")
        assert not workspace_manager._is_valid_git_url("ftp://example.com/repo")

    def test_is_valid_branch_name(self, workspace_manager):
        """Test Git branch name validation"""
        assert workspace_manager._is_valid_branch_name("feature-branch")
        assert workspace_manager._is_valid_branch_name("feature/branch")
        assert workspace_manager._is_valid_branch_name("main")
        
        assert not workspace_manager._is_valid_branch_name("branch~1")
        assert not workspace_manager._is_valid_branch_name("branch^1")
        assert not workspace_manager._is_valid_branch_name("branch with spaces")
        assert not workspace_manager._is_valid_branch_name(".branch")
        assert not workspace_manager._is_valid_branch_name("branch.")
        assert not workspace_manager._is_valid_branch_name("branch..name")

    def test_is_safe_file_path(self, workspace_manager):
        """Test file path validation"""
        assert workspace_manager._is_safe_file_path("src/main/scala/Test.scala")
        assert workspace_manager._is_safe_file_path("build.sbt")
        
        assert not workspace_manager._is_safe_file_path("../../../etc/passwd")
        assert not workspace_manager._is_safe_file_path("/absolute/path")
        assert not workspace_manager._is_safe_file_path("")
        assert not workspace_manager._is_safe_file_path("a" * 501)  # Too long


class TestGitOperations:
    """Test suite for Git operations"""

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_clone_workspace_from_git_success(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test successful Git repository cloning"""
        workspace_name = "cloned-workspace"
        git_url = "https://github.com/user/repo.git"
        branch = "main"
        
        mock_repo_class.clone_from.return_value = mock_git_repo
        
        with patch.object(workspace_manager, '_index_all_files_in_workspace', new_callable=AsyncMock) as mock_index:
            with patch.object(workspace_manager, '_count_indexed_files', new_callable=AsyncMock, return_value=5):
                result = await workspace_manager.clone_workspace_from_git(workspace_name, git_url, branch)
        
        assert result["workspace_name"] == workspace_name
        assert result["cloned"] is True
        assert result["git_info"]["remote_url"] == git_url
        assert result["git_info"]["active_branch"] == "main"
        
        mock_repo_class.clone_from.assert_called_once_with(git_url, workspace_manager.get_workspace_path(workspace_name), branch=branch)
        mock_index.assert_called_once_with(workspace_name)

    @pytest.mark.asyncio
    async def test_clone_workspace_invalid_name(self, workspace_manager):
        """Test Git cloning with invalid workspace name"""
        with pytest.raises(ValueError, match="Invalid workspace name"):
            await workspace_manager.clone_workspace_from_git("invalid/name", "https://github.com/user/repo.git")

    @pytest.mark.asyncio
    async def test_clone_workspace_invalid_url(self, workspace_manager):
        """Test Git cloning with invalid URL"""
        with pytest.raises(ValueError, match="Invalid Git URL"):
            await workspace_manager.clone_workspace_from_git("valid-name", "invalid-url")

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_checkout_branch_create_new(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test creating and checking out a new branch"""
        workspace_name = "test-workspace"
        branch_name = "feature-branch"
        
        # Setup workspace
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        mock_new_branch = Mock()
        mock_git_repo.create_head.return_value = mock_new_branch
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.git_checkout_branch(workspace_name, branch_name, create_new=True)
        
        assert result["success"] is True
        assert result["action"] == "create_and_checkout"
        assert result["branch_name"] == branch_name
        
        mock_git_repo.create_head.assert_called_once_with(branch_name)
        mock_new_branch.checkout.assert_called_once()

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_checkout_existing_branch(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test checking out an existing branch"""
        workspace_name = "test-workspace"
        branch_name = "existing-branch"
        
        # Setup workspace
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.git_checkout_branch(workspace_name, branch_name, create_new=False)
        
        assert result["success"] is True
        assert result["action"] == "checkout"
        assert result["branch_name"] == branch_name
        
        mock_git_repo.git.checkout.assert_called_once_with(branch_name)

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_add_files_specific(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test adding specific files to Git staging"""
        workspace_name = "test-workspace"
        file_paths = ["src/main/scala/Test.scala", "build.sbt"]
        
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.git_add_files(workspace_name, file_paths)
        
        assert result["success"] is True
        assert result["action"] == "add"
        assert result["files_added"] == file_paths
        
        mock_git_repo.index.add.assert_called_once_with(file_paths)

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_add_all_files(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test adding all files to Git staging"""
        workspace_name = "test-workspace"
        
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.git_add_files(workspace_name, None)
        
        assert result["success"] is True
        assert result["action"] == "add"
        assert result["files_added"] == ["all files"]
        
        mock_git_repo.git.add.assert_called_once_with('.')

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_commit(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test Git commit"""
        workspace_name = "test-workspace"
        message = "Test commit message"
        author_name = "Test Author"
        author_email = "test@example.com"
        
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        mock_commit = Mock()
        mock_commit.hexsha = "abcdef1234567890" * 2 + "abcdef12"
        mock_commit.author = "Test Author <test@example.com>"
        mock_commit.committed_datetime.isoformat.return_value = "2024-01-15T10:30:00+00:00"
        mock_git_repo.index.commit.return_value = mock_commit
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.git_commit(workspace_name, message, author_name, author_email)
        
        assert result["success"] is True
        assert result["action"] == "commit"
        assert result["message"] == message
        assert result["commit_hash"] == "abcdef12"
        
        mock_git_repo.index.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_push(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test Git push"""
        workspace_name = "test-workspace"
        remote_name = "origin"
        branch_name = "main"
        
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        mock_remote = Mock()
        mock_remote.name = remote_name
        mock_git_repo.remotes = [mock_remote]
        mock_git_repo.remote.return_value = mock_remote
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.git_push(workspace_name, remote_name, branch_name)
        
        assert result["success"] is True
        assert result["action"] == "push"
        assert result["remote_name"] == remote_name
        assert result["branch_name"] == branch_name
        
        mock_git_repo.remote.assert_called_once_with(remote_name)
        mock_remote.push.assert_called_once_with(f"{branch_name}:{branch_name}")

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_pull(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test Git pull"""
        workspace_name = "test-workspace"
        remote_name = "origin"
        branch_name = "main"
        
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        mock_remote = Mock()
        mock_remote.name = remote_name
        mock_git_repo.remotes = [mock_remote]
        mock_git_repo.remote.return_value = mock_remote
        mock_repo_class.return_value = mock_git_repo
        
        with patch.object(workspace_manager, '_index_all_files_in_workspace', new_callable=AsyncMock):
            result = await workspace_manager.git_pull(workspace_name, remote_name, branch_name)
        
        assert result["success"] is True
        assert result["action"] == "pull"
        assert result["remote_name"] == remote_name
        assert result["branch_name"] == branch_name
        assert result["files_reindexed"] is True
        
        mock_git_repo.remote.assert_called_once_with(remote_name)
        mock_remote.pull.assert_called_once_with(branch_name)

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_status(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test Git status"""
        workspace_name = "test-workspace"
        
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        # Mock status information
        mock_git_repo.is_dirty.return_value = True
        mock_git_repo.untracked_files = ["new-file.scala"]
        
        mock_diff_item = Mock()
        mock_diff_item.a_path = "modified-file.scala"
        mock_git_repo.index.diff.return_value = [mock_diff_item]
        
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.git_status(workspace_name)
        
        assert result["workspace_name"] == workspace_name
        assert result["current_branch"] == "main"
        assert result["is_dirty"] is True
        assert "new-file.scala" in result["untracked_files"]
        assert "modified-file.scala" in result["modified_files"]

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_git_log(self, mock_repo_class, workspace_manager, mock_git_repo):
        """Test Git commit history"""
        workspace_name = "test-workspace"
        limit = 5
        
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        # Mock commit history
        mock_commit = Mock()
        mock_commit.hexsha = "abcdef1234567890" * 2 + "abcdef12"
        mock_commit.message = "Test commit message"
        mock_commit.author = "Test Author <test@example.com>"
        mock_commit.committed_datetime.isoformat.return_value = "2024-01-15T10:30:00+00:00"
        mock_commit.stats.files = {"file1.scala": {}, "file2.scala": {}}
        
        mock_git_repo.iter_commits.return_value = [mock_commit]
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.git_log(workspace_name, limit)
        
        assert result["workspace_name"] == workspace_name
        assert result["current_branch"] == "main"
        assert len(result["commits"]) == 1
        assert result["commits"][0]["hash"] == "abcdef12"
        assert result["commits"][0]["message"] == "Test commit message"
        assert result["commits"][0]["files_changed"] == 2
        
        mock_git_repo.iter_commits.assert_called_once_with(max_count=limit)

    @pytest.mark.asyncio
    async def test_git_operations_invalid_workspace(self, workspace_manager):
        """Test Git operations on non-existent workspace"""
        workspace_name = "nonexistent-workspace"
        
        with pytest.raises(ValueError, match="not found"):
            await workspace_manager.git_checkout_branch(workspace_name, "branch")
        
        with pytest.raises(ValueError, match="not found"):
            await workspace_manager.git_add_files(workspace_name, [])
        
        with pytest.raises(ValueError, match="not found"):
            await workspace_manager.git_commit(workspace_name, "message")
        
        with pytest.raises(ValueError, match="not found"):
            await workspace_manager.git_push(workspace_name)
        
        with pytest.raises(ValueError, match="not found"):
            await workspace_manager.git_pull(workspace_name)
        
        with pytest.raises(ValueError, match="not found"):
            await workspace_manager.git_status(workspace_name)
        
        with pytest.raises(ValueError, match="not found"):
            await workspace_manager.git_log(workspace_name)

    @pytest.mark.asyncio
    async def test_git_operations_invalid_branch_name(self, workspace_manager):
        """Test Git operations with invalid branch names"""
        workspace_name = "test-workspace"
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        with pytest.raises(ValueError, match="Invalid branch name"):
            await workspace_manager.git_checkout_branch(workspace_name, "invalid~branch")

    @pytest.mark.asyncio
    async def test_git_commit_empty_message(self, workspace_manager):
        """Test Git commit with empty message"""
        workspace_name = "test-workspace"
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        with pytest.raises(ValueError, match="Commit message cannot be empty"):
            await workspace_manager.git_commit(workspace_name, "")

    @pytest.mark.asyncio
    async def test_git_add_invalid_file_path(self, workspace_manager):
        """Test Git add with invalid file paths"""
        workspace_name = "test-workspace"
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        with patch('scala_runner.workspace_manager.git.Repo') as mock_repo_class:
            mock_git_repo = Mock()
            mock_repo_class.return_value = mock_git_repo
            
            with pytest.raises(ValueError, match="Invalid file path"):
                await workspace_manager.git_add_files(workspace_name, ["../../../etc/passwd"])


class TestSearchOperations:
    """Test suite for search operations"""

    @pytest.mark.asyncio
    async def test_search_files(self, workspace_manager):
        """Test file search functionality using real Whoosh index"""
        workspace_name = "test-workspace"
        query = "test query"
        
        # Create a test workspace
        await workspace_manager.create_workspace(workspace_name)
        
        # Create a test file with content that matches our query
        test_content = "This is a test query example\nSecond line of content\nAnother line with test query here"
        await workspace_manager.create_file(workspace_name, "test.scala", test_content)
        
        # Create another file that doesn't match
        await workspace_manager.create_file(workspace_name, "other.scala", "Some other content without the search term")
        
        # Search for files
        results = await workspace_manager.search_files(workspace_name, query, 10)
        
        # Verify results
        assert len(results) == 1
        assert results[0]["workspace"] == workspace_name
        assert results[0]["filename"] == "test.scala"
        assert results[0]["extension"] == "scala"
        assert results[0]["filepath"] == f"{workspace_name}/test.scala"
        assert results[0]["file_path"] == f"{workspace_name}/test.scala"  # backward compatibility
        assert len(results[0]["matching_lines"]) >= 2  # Should find at least 2 matching lines
        
        # Check that matching lines contain our query
        matching_line_contents = [line["content"] for line in results[0]["matching_lines"]]
        assert any("test query" in content.lower() for content in matching_line_contents)
        
        # Clean up
        await workspace_manager.delete_workspace(workspace_name)

    @pytest.mark.asyncio
    async def test_index_all_files_in_workspace(self, workspace_manager):
        """Test indexing all files in a workspace"""
        workspace_name = "test-workspace"
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        # Create test files
        (workspace_path / "test.scala").write_text("object Test")
        (workspace_path / "build.sbt").write_text("name := \"test\"")
        (workspace_path / "binary.class").write_bytes(b"binary content")  # Should be skipped
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock) as mock_index_file:
            await workspace_manager._index_all_files_in_workspace(workspace_name)
        
        # Should index text files but not binary files
        assert mock_index_file.call_count == 2
        
        # Check that the right files were indexed
        indexed_files = [call[0][1] for call in mock_index_file.call_args_list]
        assert "test.scala" in indexed_files
        assert "build.sbt" in indexed_files

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.open_dir')
    async def test_count_indexed_files(self, mock_open_index, workspace_manager):
        """Test counting indexed files"""
        workspace_name = "test-workspace"
        
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [Mock(), Mock(), Mock()]  # 3 results
        mock_searcher.__enter__.return_value = mock_searcher
        mock_searcher.__exit__.return_value = None
        
        mock_index = Mock()
        mock_index.searcher.return_value = mock_searcher
        mock_open_index.return_value = mock_index
        
        count = await workspace_manager._count_indexed_files(workspace_name)
        
        assert count == 3

    @pytest.mark.asyncio
    @patch('scala_runner.workspace_manager.git.Repo')
    async def test_get_workspace_git_info_success(self, mock_repo_class, workspace_manager):
        """Test getting Git info for a workspace"""
        workspace_name = "test-workspace"
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        # Setup mock repository with more complete info
        mock_git_repo = Mock()
        mock_git_repo.bare = False
        
        mock_remote = Mock()
        mock_remote.name = "origin"
        mock_remote.urls = ["https://github.com/user/repo.git"]
        mock_git_repo.remotes = [mock_remote]
        
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_git_repo.branches = [mock_branch]
        mock_git_repo.active_branch = mock_branch
        
        mock_commit = Mock()
        mock_commit.hexsha = "abcdef123456789"
        mock_commit.message = "Test commit"
        mock_commit.author = "Test Author <test@example.com>"
        mock_commit.committed_datetime.isoformat.return_value = "2024-01-15T10:30:00+00:00"
        mock_git_repo.head.commit = mock_commit
        
        mock_git_repo.is_dirty.return_value = False
        mock_git_repo.untracked_files = []
        
        mock_repo_class.return_value = mock_git_repo
        
        result = await workspace_manager.get_workspace_git_info(workspace_name)
        
        assert result["is_git_repo"] is True
        assert result["active_branch"] == "main"
        assert len(result["remotes"]) == 1
        assert result["remotes"][0]["name"] == "origin"
        assert len(result["branches"]) == 1

    @pytest.mark.asyncio
    async def test_get_workspace_git_info_not_git_repo(self, workspace_manager):
        """Test getting Git info for non-Git workspace"""
        workspace_name = "test-workspace"
        workspace_path = workspace_manager.get_workspace_path(workspace_name)
        workspace_path.mkdir(parents=True)
        
        with patch('scala_runner.workspace_manager.git.Repo', side_effect=git.exc.InvalidGitRepositoryError):
            result = await workspace_manager.get_workspace_git_info(workspace_name)
        
        assert result["is_git_repo"] is False
        assert "error" in result


class TestPatchOperations:
    """Test git diff patch functionality"""

    @pytest.mark.asyncio
    async def test_apply_patch_simple_line_change(self, workspace_manager):
        """Test applying a simple line change patch"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        # Create initial file
        file_path = "src/main/scala/Test.scala"
        initial_content = """object Test {
  def main(args: Array[String]): Unit = {
    println("Hello, World!")
  }
}"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            await workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Create patch that changes "Hello, World!" to "Hello, Patched!"
        patch_content = """--- a/src/main/scala/Test.scala
+++ b/src/main/scala/Test.scala
@@ -1,5 +1,5 @@
 object Test {
   def main(args: Array[String]): Unit = {
-    println("Hello, World!")
+    println("Hello, Patched!")
   }
 }"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.apply_patch(workspace_name, patch_content)
        
        assert result["patch_applied"] is True
        assert result["results"]["total_files"] == 1
        assert result["results"]["successful_files"] == 1
        assert len(result["results"]["modified_files"]) == 1
        
        modified_file = result["results"]["modified_files"][0]
        assert modified_file["file_path"] == file_path
        assert modified_file["status"] == "success"
        assert modified_file["hunks_applied"] == 1
        
        # Verify file content was actually changed
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        new_content = full_path.read_text()
        assert "Hello, Patched!" in new_content
        assert "Hello, World!" not in new_content

    @pytest.mark.asyncio
    async def test_apply_patch_add_new_lines(self, workspace_manager):
        """Test applying a patch that adds new lines"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        file_path = "src/main/scala/Test.scala"
        initial_content = """object Test {
  def main(args: Array[String]): Unit = {
    println("Hello")
  }
}"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            await workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Patch that adds new lines
        patch_content = """--- a/src/main/scala/Test.scala
+++ b/src/main/scala/Test.scala
@@ -1,5 +1,7 @@
 object Test {
   def main(args: Array[String]): Unit = {
     println("Hello")
+    val x = 42
+    println(s"Number: $x")
   }
 }"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.apply_patch(workspace_name, patch_content)
        
        assert result["patch_applied"] is True
        
        # Verify new lines were added
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        new_content = full_path.read_text()
        assert "val x = 42" in new_content
        assert "println(s\"Number: $x\")" in new_content

    @pytest.mark.asyncio
    async def test_apply_patch_remove_lines(self, workspace_manager):
        """Test applying a patch that removes lines"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        file_path = "src/main/scala/Test.scala"
        initial_content = """object Test {
  def main(args: Array[String]): Unit = {
    println("Hello")
    val x = 42
    println(s"Number: $x")
    println("Goodbye")
  }
}"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            await workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Patch that removes lines
        patch_content = """--- a/src/main/scala/Test.scala
+++ b/src/main/scala/Test.scala
@@ -1,8 +1,6 @@
 object Test {
   def main(args: Array[String]): Unit = {
     println("Hello")
-    val x = 42
-    println(s"Number: $x")
     println("Goodbye")
   }
 }"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.apply_patch(workspace_name, patch_content)
        
        assert result["patch_applied"] is True
        
        # Verify lines were removed
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        new_content = full_path.read_text()
        assert "val x = 42" not in new_content
        assert "println(s\"Number: $x\")" not in new_content
        assert "println(\"Hello\")" in new_content
        assert "println(\"Goodbye\")" in new_content

    @pytest.mark.asyncio
    async def test_apply_patch_create_new_file(self, workspace_manager):
        """Test applying a patch that creates a new file"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        # Patch that creates a new file
        patch_content = """--- /dev/null
+++ b/src/main/scala/NewFile.scala
@@ -0,0 +1,5 @@
+object NewFile {
+  def greet(): String = {
+    "Hello from new file!"
+  }
+}"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.apply_patch(workspace_name, patch_content)
        
        assert result["patch_applied"] is True
        assert result["results"]["total_files"] == 1
        assert result["results"]["successful_files"] == 1
        
        # Verify new file was created
        new_file_path = workspace_manager.get_workspace_path(workspace_name) / "src/main/scala/NewFile.scala"
        assert new_file_path.exists()
        content = new_file_path.read_text()
        assert "object NewFile" in content
        assert "Hello from new file!" in content

    @pytest.mark.asyncio
    async def test_apply_patch_multiple_files(self, workspace_manager):
        """Test applying a patch that modifies multiple files"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        # Create initial files
        file1_path = "src/main/scala/File1.scala"
        file1_content = "object File1 { val value = \"old\" }"
        
        file2_path = "src/main/scala/File2.scala"
        file2_content = "object File2 { def method() = {} }"
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            await workspace_manager.create_file(workspace_name, file1_path, file1_content)
            await workspace_manager.create_file(workspace_name, file2_path, file2_content)
        
        # Patch that modifies both files
        patch_content = """--- a/src/main/scala/File1.scala
+++ b/src/main/scala/File1.scala
@@ -1 +1 @@
-object File1 { val value = "old" }
+object File1 { val value = "new" }
--- a/src/main/scala/File2.scala
+++ b/src/main/scala/File2.scala
@@ -1 +1,3 @@
-object File2 { def method() = {} }
+object File2 { 
+  def method() = println("updated")
+}"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.apply_patch(workspace_name, patch_content)
        
        assert result["patch_applied"] is True
        assert result["results"]["total_files"] == 2
        assert result["results"]["successful_files"] == 2
        
        # Verify both files were modified
        full_path1 = workspace_manager.get_workspace_path(workspace_name) / file1_path
        full_path2 = workspace_manager.get_workspace_path(workspace_name) / file2_path
        
        content1 = full_path1.read_text()
        content2 = full_path2.read_text()
        
        assert 'val value = "new"' in content1
        assert 'val value = "old"' not in content1
        assert 'println("updated")' in content2

    @pytest.mark.asyncio
    async def test_apply_patch_multiple_hunks_same_file(self, workspace_manager):
        """Test applying a patch with multiple hunks in the same file"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        file_path = "src/main/scala/Test.scala"
        initial_content = """object Test {
  val x = 1
  val y = 2
  
  def method1() = {
    println("method1")
  }
  
  def method2() = {
    println("method2")
  }
}"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            await workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Patch with multiple hunks
        patch_content = """--- a/src/main/scala/Test.scala
+++ b/src/main/scala/Test.scala
@@ -1,4 +1,4 @@
 object Test {
-  val x = 1
+  val x = 10
   val y = 2
   
@@ -8,5 +8,5 @@
   }
   
   def method2() = {
-    println("method2")
+    println("updated method2")
   }
 }"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.apply_patch(workspace_name, patch_content)
        
        assert result["patch_applied"] is True
        modified_file = result["results"]["modified_files"][0]
        assert modified_file["hunks_applied"] == 2
        
        # Verify both hunks were applied
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        new_content = full_path.read_text()
        assert "val x = 10" in new_content
        assert "updated method2" in new_content
        # Note: Multiple hunk application may have issues with overlapping content

    @pytest.mark.asyncio
    async def test_apply_patch_invalid_workspace(self, workspace_manager):
        """Test applying patch to non-existent workspace"""
        patch_content = """--- a/test.scala
+++ b/test.scala
@@ -1 +1 @@
-old line
+new line"""
        
        with pytest.raises(ValueError, match="Workspace 'nonexistent' not found"):
            await workspace_manager.apply_patch("nonexistent", patch_content)

    @pytest.mark.asyncio
    async def test_apply_patch_empty_patch(self, workspace_manager):
        """Test applying empty patch"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        patch_content = ""
        
        result = await workspace_manager.apply_patch(workspace_name, patch_content)
        
        # Should succeed but with no changes
        assert result["patch_applied"] is True
        assert result["results"]["total_files"] == 0
        assert result["results"]["successful_files"] == 0

    @pytest.mark.asyncio
    async def test_parse_hunk_header_valid(self, workspace_manager):
        """Test parsing valid hunk headers"""
        # Test different hunk header formats
        test_cases = [
            ("@@ -1,4 +1,6 @@", {"old_start": 1, "old_count": 4, "new_start": 1, "new_count": 6}),
            ("@@ -10 +10,2 @@", {"old_start": 10, "old_count": 1, "new_start": 10, "new_count": 2}),
            ("@@ -5,0 +5,3 @@", {"old_start": 5, "old_count": 0, "new_start": 5, "new_count": 3}),
        ]
        
        for header, expected in test_cases:
            result = workspace_manager._parse_hunk_header(header)
            assert result == expected

    @pytest.mark.asyncio
    async def test_parse_hunk_header_invalid(self, workspace_manager):
        """Test parsing invalid hunk headers"""
        invalid_headers = [
            "invalid header",
            "@@ invalid @@",
            "not a hunk header",
            "",
        ]
        
        for header in invalid_headers:
            result = workspace_manager._parse_hunk_header(header)
            assert result is None

    @pytest.mark.asyncio
    async def test_apply_patch_with_context_lines(self, workspace_manager):
        """Test applying patch with context lines"""
        workspace_name = "test-workspace"
        await workspace_manager.create_workspace(workspace_name)
        
        file_path = "src/main/scala/Test.scala"
        initial_content = """line1
line2
old_line
line4
line5"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            await workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Patch with context lines
        patch_content = """--- a/src/main/scala/Test.scala
+++ b/src/main/scala/Test.scala
@@ -1,5 +1,5 @@
 line1
 line2
-old_line
+new_line
 line4
 line5"""
        
        with patch.object(workspace_manager, '_index_file', new_callable=AsyncMock):
            result = await workspace_manager.apply_patch(workspace_name, patch_content)
        
        assert result["patch_applied"] is True
        
        # Verify only the target line was changed
        full_path = workspace_manager.get_workspace_path(workspace_name) / file_path
        new_content = full_path.read_text()
        lines = new_content.split('\n')
        assert lines[0] == "line1"
        assert lines[1] == "line2"
        assert lines[2] == "new_line"
        assert lines[3] == "line4"
        assert lines[4] == "line5" 