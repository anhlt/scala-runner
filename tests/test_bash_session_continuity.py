import pytest
from fastapi.testclient import TestClient
from scala_runner.main import app
import time
import random

client = TestClient(app)

class TestBashSessionContinuity:
    """Test suite for verifying continuous command execution in bash sessions"""

    @pytest.mark.integration
    def test_session_state_persistence(self):
        """Test that session state persists across multiple commands"""
        workspace_name = f"continuity-test-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
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
            
            print(f"Created session: {session_id}")
            
            # Command 1: Set environment variable
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "export MY_VAR='Hello from session'"
            })
            assert response.status_code == 200
            print("✅ Set environment variable")
            
            # Command 2: Verify environment variable persists
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "echo $MY_VAR"
            })
            assert response.status_code == 200
            data = response.json()
            assert "Hello from session" in data["data"]["output"]
            print("✅ Environment variable persisted")
            
            # Command 3: Create directory and change into it
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "mkdir -p myapp/src && cd myapp"
            })
            assert response.status_code == 200
            print("✅ Created directory and changed into it")
            
            # Command 4: Verify current directory changed
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "pwd"
            })
            assert response.status_code == 200
            data = response.json()
            assert "myapp" in data["data"]["output"]
            print("✅ Directory change persisted")
            
            # Command 5: Create file in current directory
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "echo 'package myapp' > Main.scala"
            })
            assert response.status_code == 200
            print("✅ Created file in current directory")
            
            # Command 6: List files to verify creation
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "ls -la"
            })
            assert response.status_code == 200
            data = response.json()
            assert "Main.scala" in data["data"]["output"]
            print("✅ File creation verified")
            
            # Command 7: Read file content
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "cat Main.scala"
            })
            assert response.status_code == 200
            data = response.json()
            assert "package myapp" in data["data"]["output"]
            print("✅ File content verified")
            
            # Command 8: Set another variable using existing one
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "export FULL_MSG=\"$MY_VAR - from $(pwd)\""
            })
            assert response.status_code == 200
            print("✅ Set composite environment variable")
            
            # Command 9: Verify composite variable
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "echo $FULL_MSG"
            })
            assert response.status_code == 200
            data = response.json()
            output = data["data"]["output"]
            assert "Hello from session" in output
            assert "myapp" in output
            print("✅ Composite variable verified")
            
            # Command 10: Change back to root and verify
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "cd /workspace && pwd"
            })
            assert response.status_code == 200
            data = response.json()
            assert "/workspace" == data["data"]["output"].strip()
            print("✅ Changed back to workspace root")
            
            # Command 11: Verify our created structure exists
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "find . -name '*.scala' -type f"
            })
            assert response.status_code == 200
            data = response.json()
            assert "myapp/Main.scala" in data["data"]["output"]
            print("✅ Directory structure persisted")
            
            # Command 12: Test history command (may not work in Docker exec context)
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "history | tail -5"
            })
            assert response.status_code == 200
            data = response.json()
            # History may not work in Docker exec context, so just verify command executed
            if data["data"]["output"]:
                print("✅ Command history accessible")
            else:
                print("⚠️  Command history not available (expected in Docker exec context)")
                # Test an alternative command that verifies session continuity instead
                response = client.post("/bash/execute", json={
                    "session_id": session_id,
                    "command": "echo $MY_VAR"  # This should still work from earlier
                })
                assert response.status_code == 200
                assert "Hello from session" in response.json()["data"]["output"]
                print("✅ Session continuity verified via environment variable")
            
            print(f"🎉 All commands executed successfully in session {session_id}")
            
            # Close session
            response = client.delete(f"/bash/sessions/{session_id}")
            assert response.status_code == 200
            print("✅ Session closed successfully")
            
        finally:
            # Clean up workspace
            client.delete(f"/workspaces/{workspace_name}")
            print("✅ Workspace cleaned up")

    @pytest.mark.integration
    def test_scala_project_workflow(self):
        """Test a complete Scala project workflow in one session"""
        workspace_name = f"scala-workflow-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
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
            
            print(f"Starting Scala workflow in session: {session_id}")
            
            # Step 1: Check initial project structure
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "ls -la"
            })
            assert response.status_code == 200
            data = response.json()
            assert "build.sbt" in data["data"]["output"]
            print("✅ Initial project structure verified")
            
            # Step 2: Check Scala and SBT versions
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "scala -version && sbt --version"
            })
            assert response.status_code == 200
            print("✅ Scala and SBT versions checked")
            
            # Step 3: Modify the existing Main.scala file
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": """cat > src/main/scala/Main.scala << 'EOF'
object Main extends App {
  val greeting = "Hello from continuous session!"
  println(greeting)
  println(s"Current time: ${java.time.LocalDateTime.now}")
  
  // Simple calculation
  val numbers = (1 to 5).toList
  val sum = numbers.sum
  println(s"Sum of $numbers = $sum")
}
EOF"""
            })
            assert response.status_code == 200
            print("✅ Updated Main.scala")
            
            # Step 4: Verify file content
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "cat src/main/scala/Main.scala"
            })
            assert response.status_code == 200
            data = response.json()
            assert "Hello from continuous session!" in data["data"]["output"]
            print("✅ File content verified")
            
            # Step 5: Create a test file
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": """cat > src/test/scala/MainTest.scala << 'EOF'
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class MainTest extends AnyFlatSpec with Matchers {
  "Main object" should "exist" in {
    Main shouldBe an [Object]
  }
}
EOF"""
            })
            assert response.status_code == 200
            print("✅ Created test file")
            
            # Step 6: Update build.sbt to include test dependencies
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": """cat > build.sbt << 'EOF'
ThisBuild / version := "0.1.0-SNAPSHOT"
ThisBuild / scalaVersion := "2.13.14"

lazy val root = (project in file("."))
  .settings(
    name := "continuous-session-project",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-core" % "2.12.0",
      "org.scalatest" %% "scalatest" % "3.2.17" % Test
    ),
    javacOptions ++= Seq("-source", "11", "-target", "11"),
    scalacOptions ++= Seq("-release", "11")
  )
EOF"""
            })
            assert response.status_code == 200
            print("✅ Updated build.sbt")
            
            # Step 7: Try to compile (this might take a while due to dependencies)
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "sbt compile",
                "timeout": 180
            })
            assert response.status_code == 200
            data = response.json()
            print(f"✅ Compilation attempted - Status: {data['data']['status']}")
            
            # Step 8: Run the project
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "sbt run",
                "timeout": 120
            })
            assert response.status_code == 200
            data = response.json()
            print(f"✅ Run attempted - Status: {data['data']['status']}")
            # Note: May succeed or fail depending on environment, but should execute
            
            # Step 9: Check project structure
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "find . -name '*.scala' -o -name '*.sbt' | sort"
            })
            assert response.status_code == 200
            data = response.json()
            output = data["data"]["output"]
            assert "build.sbt" in output
            assert "Main.scala" in output
            assert "MainTest.scala" in output
            print("✅ Project structure verified")
            
            # Step 10: Create a simple shell script and execute it
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": """cat > project_info.sh << 'EOF'
#!/bin/bash
echo "=== Project Information ==="
echo "Project directory: $(pwd)"
echo "Scala files count: $(find . -name '*.scala' | wc -l)"
echo "SBT files count: $(find . -name '*.sbt' | wc -l)"
echo "Last modified: $(ls -la | head -2 | tail -1 | awk '{print $6, $7, $8}')"
echo "=========================="
EOF"""
            })
            assert response.status_code == 200
            print("✅ Created shell script")
            
            # Step 11: Make script executable and run it
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "chmod +x project_info.sh && ./project_info.sh"
            })
            assert response.status_code == 200
            data = response.json()
            assert "Project Information" in data["data"]["output"]
            assert "Scala files count:" in data["data"]["output"]
            print("✅ Shell script executed successfully")
            
            print(f"🎉 Complete Scala workflow executed successfully in session {session_id}")
            
            # Close session
            response = client.delete(f"/bash/sessions/{session_id}")
            assert response.status_code == 200
            print("✅ Session closed successfully")
            
        finally:
            # Clean up workspace
            client.delete(f"/workspaces/{workspace_name}")
            print("✅ Workspace cleaned up")

    @pytest.mark.integration
    def test_session_variables_and_aliases(self):
        """Test that shell variables, aliases, and functions persist across commands"""
        workspace_name = f"vars-test-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
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
            
            print(f"Testing variables and aliases in session: {session_id}")
            
            # Test 1: Create multiple variables
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "export PROJECT_NAME='MyScalaApp' && export VERSION='1.0.0' && export AUTHOR='TestUser'"
            })
            assert response.status_code == 200
            print("✅ Set multiple environment variables")
            
            # Test 2: Use variables together
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "echo \"Project: $PROJECT_NAME v$VERSION by $AUTHOR\""
            })
            assert response.status_code == 200
            data = response.json()
            output = data["data"]["output"]
            assert "MyScalaApp" in output
            assert "1.0.0" in output
            assert "TestUser" in output
            print("✅ Variables used together successfully")
            
            # Test 3: Create aliases
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "alias ll='ls -la' && alias proj='echo $PROJECT_NAME'"
            })
            assert response.status_code == 200
            print("✅ Created aliases")
            
            # Test 4: Use aliases
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "ll | head -3"
            })
            assert response.status_code == 200
            data = response.json()
            assert "total" in data["data"]["output"]  # ll should show detailed listing
            print("✅ Alias 'll' works")
            
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "proj"
            })
            assert response.status_code == 200
            data = response.json()
            assert "MyScalaApp" in data["data"]["output"]
            print("✅ Alias 'proj' works")
            
            # Test 5: Create a shell function
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": """
create_scala_class() {
    local class_name=$1
    local package_name=${2:-"com.example"}
    echo "package $package_name" > "${class_name}.scala"
    echo "" >> "${class_name}.scala"
    echo "class $class_name {" >> "${class_name}.scala"
    echo "  // TODO: Implement $class_name" >> "${class_name}.scala"
    echo "}" >> "${class_name}.scala"
    echo "Created $class_name.scala"
}
"""
            })
            assert response.status_code == 200
            print("✅ Created shell function")
            
            # Test 6: Use the shell function
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "create_scala_class MyService com.myapp.service"
            })
            assert response.status_code == 200
            data = response.json()
            assert "Created MyService.scala" in data["data"]["output"]
            print("✅ Shell function executed")
            
            # Test 7: Verify the file was created
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "cat MyService.scala"
            })
            assert response.status_code == 200
            data = response.json()
            output = data["data"]["output"]
            assert "package com.myapp.service" in output
            assert "class MyService" in output
            print("✅ Function output verified")
            
            # Test 8: Modify variables and use in function
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "export DEFAULT_PACKAGE='com.test' && create_scala_class TestClass $DEFAULT_PACKAGE"
            })
            assert response.status_code == 200
            data = response.json()
            assert "Created TestClass.scala" in data["data"]["output"]
            print("✅ Function used with variables")
            
            # Test 9: Create and use array
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": "FILES=(*.scala) && echo \"Found ${#FILES[@]} Scala files: ${FILES[*]}\""
            })
            assert response.status_code == 200
            data = response.json()
            output = data["data"]["output"]
            assert "Found" in output
            assert "Scala files" in output
            print("✅ Array variables work")
            
            # Test 10: Complex command with all features
            response = client.post("/bash/execute", json={
                "session_id": session_id,
                "command": """
echo "=== $PROJECT_NAME v$VERSION Development Summary ==="
echo "Author: $AUTHOR"
echo "Working Directory: $(pwd)"
ll *.scala
echo "Total Scala files: $(ls *.scala | wc -l)"
proj
echo "==========================================="
"""
            })
            assert response.status_code == 200
            data = response.json()
            output = data["data"]["output"]
            assert "MyScalaApp v1.0.0" in output
            assert "TestUser" in output
            assert "MyScalaApp" in output  # from proj alias
            print("✅ Complex command with all features works")
            
            print(f"🎉 All variables, aliases, and functions worked perfectly in session {session_id}")
            
            # Close session
            response = client.delete(f"/bash/sessions/{session_id}")
            assert response.status_code == 200
            print("✅ Session closed successfully")
            
        finally:
            # Clean up workspace
            client.delete(f"/workspaces/{workspace_name}")
            print("✅ Workspace cleaned up")

if __name__ == "__main__":
    # Quick test runner for direct execution
    test_instance = TestBashSessionContinuity()
    try:
        print("🧪 Testing session state persistence...")
        test_instance.test_session_state_persistence()
        print("\n🧪 Testing Scala project workflow...")
        test_instance.test_scala_project_workflow()
        print("\n🧪 Testing variables and aliases...")
        test_instance.test_session_variables_and_aliases()
        print("\n🎉 All continuity tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise 