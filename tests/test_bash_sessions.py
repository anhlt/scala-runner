import pytest
from fastapi.testclient import TestClient
from scala_runner.main import app
import time
import random

client = TestClient(app)

class TestBashSessions:
    """Test suite for bash session functionality"""

    @pytest.mark.integration 
    def test_bash_session_lifecycle(self):
        """Test creating, using, and closing a bash session"""
        workspace_name = f"bash-test-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        try:
            # Create bash session
            response = client.post("/bash/sessions", json={"workspace_name": workspace_name})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "session_id" in data["data"]
            
            session_id = data["data"]["session_id"]
            
            # Execute simple command
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "echo 'Hello World'"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Hello World" in data["data"]["output"]
            
            # Execute pwd command to verify we're in workspace
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "pwd"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "/workspace" in data["data"]["output"]
            
            # List directory contents
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "ls -la"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "build.sbt" in data["data"]["output"]
            
            # Get session info
            response = client.get(f"/bash/sessions/{session_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["session_id"] == session_id
            assert data["data"]["workspace_name"] == workspace_name
            assert data["data"]["is_active"] == True
            
            # List all sessions
            response = client.get("/bash/sessions")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["total_sessions"] >= 1
            
            # Close session
            response = client.delete(f"/bash/sessions/{session_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["status"] == "closed"
            
        finally:
            # Clean up workspace
            client.delete(f"/workspaces/{workspace_name}")

    @pytest.mark.integration
    def test_bash_session_file_operations(self):
        """Test file operations in bash session"""
        workspace_name = f"bash-files-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        try:
            # Create bash session
            response = client.post("/bash/sessions", json={"workspace_name": workspace_name})
            assert response.status_code == 200
            session_id = response.json()["data"]["session_id"]
            
            # Create a file using bash
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "echo 'Hello from bash' > test.txt"
            })
            assert response.status_code == 200
            
            # Read the file
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "cat test.txt"
            })
            assert response.status_code == 200
            data = response.json()
            assert "Hello from bash" in data["data"]["output"]
            
            # Verify file exists via API
            response = client.get(f"/files/{workspace_name}/test.txt")
            assert response.status_code == 200
            data = response.json()
            assert "Hello from bash" in data["data"]["content"]
            
            # Close session
            client.delete(f"/bash/sessions/{session_id}")
            
        finally:
            # Clean up workspace
            client.delete(f"/workspaces/{workspace_name}")

    @pytest.mark.integration
    def test_bash_session_scala_compilation(self):
        """Test using bash session to compile Scala code"""
        workspace_name = f"bash-scala-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        try:
            # Create bash session
            response = client.post("/bash/sessions", json={"workspace_name": workspace_name})
            assert response.status_code == 200
            session_id = response.json()["data"]["session_id"]
            
            # Check Java version (should be available in the Docker container)
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "java -version"
            })
            assert response.status_code == 200
            
            # Check SBT version
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "sbt --version"
            })
            assert response.status_code == 200
            
            # Try to compile the default project
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "sbt compile",
                "timeout": 120
            })
            assert response.status_code == 200
            data = response.json()
            # Note: compilation might succeed or fail depending on environment,
            # but the command should execute without error
            assert data["status"] == "success"
            
            # Close session
            client.delete(f"/bash/sessions/{session_id}")
            
        finally:
            # Clean up workspace
            client.delete(f"/workspaces/{workspace_name}")

    @pytest.mark.integration
    def test_bash_session_error_handling(self):
        """Test error handling in bash sessions"""
        workspace_name = f"bash-error-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        try:
            # Create bash session
            response = client.post("/bash/sessions", json={"workspace_name": workspace_name})
            assert response.status_code == 200
            session_id = response.json()["data"]["session_id"]
            
            # Try to execute command that doesn't exist
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "nonexistent_command_12345"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"  # Command executed but might have failed
            
            # Try to execute dangerous command (should be blocked)
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "rm -rf /"
            })
            assert response.status_code == 400  # Should be blocked by safety check
            
            # Try to execute command in non-existent session
            response = client.post("/bash/execute", json={
                "session_id": "invalid_session_id",
                "command": "echo 'test'"
            })
            assert response.status_code == 400
            
            # Close session
            client.delete(f"/bash/sessions/{session_id}")
            
        finally:
            # Clean up workspace
            client.delete(f"/workspaces/{workspace_name}")

    @pytest.mark.integration
    def test_bash_session_multiple_sessions(self):
        """Test multiple bash sessions in same workspace"""
        workspace_name = f"bash-multi-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        try:
            session_ids = []
            
            # Create multiple bash sessions
            for i in range(3):
                response = client.post("/bash/sessions", json={"workspace_name": workspace_name})
                assert response.status_code == 200
                session_id = response.json()["data"]["session_id"]
                session_ids.append(session_id)
            
            # Execute different commands in each session
            for i, session_id in enumerate(session_ids):
                response = client.post("/bash/execute", json={
                    "session_id": session_id,
                    "command": f"echo 'Session {i+1}' > session_{i+1}.txt"
                })
                assert response.status_code == 200
            
            # Verify files were created
            for i in range(3):
                response = client.get(f"/files/{workspace_name}/session_{i+1}.txt")
                assert response.status_code == 200
                data = response.json()
                assert f"Session {i+1}" in data["data"]["content"]
            
            # List sessions - should show all 3
            response = client.get(f"/bash/sessions?workspace_name={workspace_name}")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["total_sessions"] == 3
            
            # Close all sessions for workspace
            response = client.delete(f"/bash/workspaces/{workspace_name}/sessions")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["closed_sessions"] == 3
            
        finally:
            # Clean up workspace
            client.delete(f"/workspaces/{workspace_name}") 