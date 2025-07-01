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


class TestPatchFilesAPI:
    """Test the PATCH /files endpoint for git diff functionality"""

    def test_patch_files_success(self):
        """Test successful patch application"""
        workspace_name = "test-patch-workspace"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Create initial file
        initial_content = """object Test {
  def main(args: Array[String]): Unit = {
    println("Hello, World!")
  }
}"""
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/Test.scala",
            "content": initial_content
        })
        assert response.status_code == 200
        
        # Apply patch
        patch_content = """--- a/src/main/scala/Test.scala
+++ b/src/main/scala/Test.scala
@@ -1,5 +1,5 @@
 object Test {
   def main(args: Array[String]): Unit = {
-    println("Hello, World!")
+    println("Hello, Patched!")
   }
 }"""
        
        response = client.patch("/files", json={
            "workspace_name": workspace_name,
            "patch": patch_content
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["patch_applied"] is True
        assert data["data"]["results"]["total_files"] == 1
        assert data["data"]["results"]["successful_files"] == 1
        
        # Verify file was changed
        response = client.get(f"/files/{workspace_name}/src/main/scala/Test.scala")
        assert response.status_code == 200
        content = response.json()["data"]["content"]
        assert "Hello, Patched!" in content
        assert "Hello, World!" not in content
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")

    def test_patch_files_create_new_file(self):
        """Test patch that creates a new file"""
        workspace_name = "test-patch-new-file"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Apply patch that creates new file
        patch_content = """--- /dev/null
+++ b/src/main/scala/NewFile.scala
@@ -0,0 +1,5 @@
+object NewFile {
+  def greet(): String = {
+    "Hello from new file!"
+  }
+}"""
        
        response = client.patch("/files", json={
            "workspace_name": workspace_name,
            "patch": patch_content
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["patch_applied"] is True
        
        # Verify new file was created
        response = client.get(f"/files/{workspace_name}/src/main/scala/NewFile.scala")
        assert response.status_code == 200
        content = response.json()["data"]["content"]
        assert "object NewFile" in content
        assert "Hello from new file!" in content
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")

    def test_patch_files_multiple_files(self):
        """Test patch that modifies multiple files"""
        workspace_name = "test-patch-multiple"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Create initial files
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/File1.scala",
            "content": "object File1 { val value = \"old\" }"
        })
        assert response.status_code == 200
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/File2.scala", 
            "content": "object File2 { def method() = {} }"
        })
        assert response.status_code == 200
        
        # Apply patch to both files
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
        
        response = client.patch("/files", json={
            "workspace_name": workspace_name,
            "patch": patch_content
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["results"]["total_files"] == 2
        assert data["data"]["results"]["successful_files"] == 2
        
        # Verify both files were modified
        response = client.get(f"/files/{workspace_name}/src/main/scala/File1.scala")
        assert response.status_code == 200
        content1 = response.json()["data"]["content"]
        assert 'val value = "new"' in content1
        
        response = client.get(f"/files/{workspace_name}/src/main/scala/File2.scala")
        assert response.status_code == 200
        content2 = response.json()["data"]["content"]
        assert 'println("updated")' in content2
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")

    def test_patch_files_missing_workspace(self):
        """Test patch application with missing workspace"""
        patch_content = """--- a/test.scala
+++ b/test.scala
@@ -1 +1 @@
-old line
+new line"""
        
        response = client.patch("/files", json={
            "workspace_name": "nonexistent-workspace",
            "patch": patch_content
        })
        
        assert response.status_code == 400

    def test_patch_files_missing_parameters(self):
        """Test patch with missing parameters"""
        # Missing patch content
        response = client.patch("/files", json={
            "workspace_name": "test-workspace"
        })
        assert response.status_code == 422  # Validation error
        
        # Missing workspace name
        response = client.patch("/files", json={
            "patch": "some patch content"
        })
        assert response.status_code == 422  # Validation error

    def test_patch_files_empty_patch(self):
        """Test patch with empty content"""
        workspace_name = "test-empty-patch"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Apply empty patch
        response = client.patch("/files", json={
            "workspace_name": workspace_name,
            "patch": ""
        })
        
        assert response.status_code == 422  # Should fail validation for empty patch
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")

    def test_patch_files_whitespace_only_patch(self):
        """Test patch with whitespace-only content"""
        workspace_name = "test-whitespace-patch"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Apply whitespace-only patch
        response = client.patch("/files", json={
            "workspace_name": workspace_name,
            "patch": "   \n\t  "
        })
        
        assert response.status_code == 422  # Should fail validation for whitespace-only patch
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")

    def test_patch_files_multiple_hunks_same_file(self):
        """Test patch with multiple hunks in the same file"""
        workspace_name = "test-multi-hunk"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Create initial file
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
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/Test.scala",
            "content": initial_content
        })
        assert response.status_code == 200
        
        # Apply patch with multiple hunks
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
        
        response = client.patch("/files", json={
            "workspace_name": workspace_name,
            "patch": patch_content
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["results"]["modified_files"][0]["hunks_applied"] == 2
        
        # Verify both hunks were applied
        response = client.get(f"/files/{workspace_name}/src/main/scala/Test.scala")
        assert response.status_code == 200
        content = response.json()["data"]["content"]
        assert "val x = 10" in content
        assert "updated method2" in content
        # Note: Multiple hunk application may have issues with overlapping content
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")