import asyncio
import pytest # type: ignore
from fastapi.testclient import TestClient
from scala_runner.main import app  # adjust import path if needed
from unittest.mock import AsyncMock, patch, Mock

client = TestClient(app)

class DummyProcess:
    def __init__(self, stdout=b"", stderr=b"", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self.stdout, self.stderr

async def fake_success_create(*args, **kwargs):
    # Simulate a successful Docker run
    return DummyProcess(stdout=b"Hello, Scala!", returncode=0)

async def fake_fail_create(*args, **kwargs):
    # Simulate a failed Docker run
    return DummyProcess(stderr=b"Docker error!", returncode=1)

@pytest.fixture(autouse=True)
def patch_async_subprocess(monkeypatch):
    # By default, patch asyncio.create_subprocess_exec to succeed
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_success_create)

# Old /run endpoint tests removed as that endpoint no longer exists

def test_ping():
    """Test the ping endpoint"""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "pong"}

def test_openapi_alias():
    """Test the openapi alias endpoint"""
    response = client.get("/openapi")
    assert response.status_code == 200
    assert "openapi" in response.json()

def test_list_workspaces_empty():
    """Test listing workspaces when none exist"""
    response = client.get("/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["data"], list)

def test_create_workspace():
    """Test creating a workspace"""
    workspace_name = "test-create-workspace"
    
    # Clean up first in case it exists
    client.delete(f"/workspaces/{workspace_name}")
    
    response = client.post("/workspaces", json={"name": workspace_name})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["workspace_name"] == workspace_name
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")

def test_create_workspace_invalid_name():
    """Test creating workspace with invalid name"""
    response = client.post("/workspaces", json={"name": "invalid@name"})
    assert response.status_code == 400

def test_delete_nonexistent_workspace():
    """Test deleting a workspace that doesn't exist"""
    response = client.delete("/workspaces/nonexistent")
    assert response.status_code == 404

@patch('scala_runner.sbt_runner.SBTRunner.compile_project')
def test_sbt_compile_workspace_not_found(mock_compile):
    """Test SBT compile with non-existent workspace"""
    response = client.post("/sbt/compile", json={"workspace_name": "nonexistent"})
    assert response.status_code == 404

@patch('scala_runner.sbt_runner.SBTRunner.clean_project')  
def test_sbt_clean_workspace_not_found(mock_clean):
    """Test SBT clean with non-existent workspace"""
    response = client.post("/sbt/clean", json={"workspace_name": "nonexistent"})
    assert response.status_code == 404

def test_search_files_missing_workspace():
    """Test search with missing workspace parameter"""
    response = client.post("/search", json={"query": "test"})
    assert response.status_code == 422  # Validation error

def test_create_file_missing_parameters():
    """Test creating file with missing parameters"""
    response = client.post("/files", json={"workspace_name": "test"})
    assert response.status_code == 422  # Validation error

def test_update_file_missing_parameters():
    """Test updating file with missing parameters"""
    response = client.put("/files", json={"workspace_name": "test"})
    assert response.status_code == 422  # Validation error