import pytest # type: ignore
from fastapi.testclient import TestClient
from scala_runner.main import app  # adjust import path if needed
import time
import random

client = TestClient(app)

@pytest.mark.integration
def test_create_workspace_and_run_sbt_compile():
    """Test creating a workspace and running SBT compile"""
    workspace_name = f"test-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Create a simple Scala file
    scala_code = '''
object HelloWorld {
  def main(args: Array[String]): Unit = {
    println("Integration Test")
  }
}
'''
    
    resp = client.put(
        "/files",
        json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/HelloWorld.scala",
            "content": scala_code
        }
    )
    assert resp.status_code == 200, resp.text
    
    # Run SBT compile
    resp = client.post(
        "/sbt/compile",
        json={"workspace_name": workspace_name},
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")

@pytest.mark.integration
def test_create_workspace_and_run_sbt_run():
    """Test creating a workspace and running SBT run"""
    workspace_name = f"test-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Create a simple Scala file
    scala_code = '''
object DirectIntegration {
  def main(args: Array[String]): Unit = {
    println("Direct Integration")
  }
}
'''
    
    resp = client.put(
        "/files",
        json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/DirectIntegration.scala",
            "content": scala_code
        }
    )
    assert resp.status_code == 200, resp.text
    
    # Run SBT run
    resp = client.post(
        "/sbt/run-project",
        json={"workspace_name": workspace_name},
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Direct Integration" in body["data"]["output"]
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")

@pytest.mark.integration
def test_workspace_with_dependencies():
    """Test workspace with external dependencies"""
    workspace_name = f"test-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Update build.sbt with dependencies
    build_sbt = '''
name := "Test Project"
version := "0.1.0"
scalaVersion := "2.13.12"

libraryDependencies ++= Seq(
  "org.typelevel" %% "cats-core" % "2.12.0"
)
'''
    
    resp = client.put(
        "/files",
        json={
            "workspace_name": workspace_name,
            "file_path": "build.sbt",
            "content": build_sbt
        }
    )
    assert resp.status_code == 200, resp.text
    
    # Create Scala file using cats
    scala_code = '''
import cats.implicits._

object CatsExample {
  def main(args: Array[String]): Unit = {
    val result = Option("Multiple Deps Test")
      .map(_.toUpperCase)
      .getOrElse("Nothing parsed")
    println("Output from multiple dependencies: " + result)
  }
}
'''
    
    resp = client.put(
        "/files",
        json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/CatsExample.scala",
            "content": scala_code
        }
    )
    assert resp.status_code == 200, resp.text
    
    # Run SBT compile and run
    resp = client.post(
        "/sbt/compile",
        json={"workspace_name": workspace_name},
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    
    resp = client.post(
        "/sbt/run-project",
        json={"workspace_name": workspace_name},
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Output from multiple dependencies: MULTIPLE DEPS TEST" in body["data"]["output"]
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")

@pytest.mark.integration
def test_workspace_file_tree():
    """Test workspace file tree functionality"""
    workspace_name = f"test-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Create some files
    files = [
        ("src/main/scala/Main.scala", "object Main { def main(args: Array[String]): Unit = println(\"Hello\") }"),
        ("src/test/scala/MainTest.scala", "class MainTest"),
        ("project/plugins.sbt", "// plugins")
    ]
    
    for path, content in files:
        resp = client.put(
            "/files",
            json={
                "workspace_name": workspace_name,
                "file_path": path,
                "content": content
            }
        )
        assert resp.status_code == 200, resp.text
    
    # Get file tree
    resp = client.get(f"/workspaces/{workspace_name}/tree")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    
    # Check that src and project directories exist in the tree structure
    tree = body["data"]["tree"]
    child_names = [child["name"] for child in tree["children"]]
    assert "src" in child_names
    assert "project" in child_names
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")

@pytest.mark.integration
def test_workspace_search():
    """Test workspace search functionality"""
    workspace_name = f"test-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Create a file with searchable content
    scala_code = '''
object SearchableExample {
  def main(args: Array[String]): Unit = {
    println("This is a searchable example")
  }
}
'''
    
    resp = client.put(
        "/files",
        json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/SearchableExample.scala",
            "content": scala_code
        }
    )
    assert resp.status_code == 200, resp.text
    
    # Search for content
    resp = client.post(
        "/search",
        json={
            "query": "searchable example",
            "workspace_name": workspace_name
        }
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["data"]["results"]) > 0
    assert "SearchableExample.scala" in body["data"]["results"][0]["file_path"]
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")

@pytest.mark.integration
def test_sbt_test_command():
    """Test SBT test command"""
    workspace_name = f"test-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Create main class
    main_code = '''
object Calculator {
  def add(x: Int, y: Int): Int = x + y
}
'''
    
    resp = client.put(
        "/files",
        json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/Calculator.scala",
            "content": main_code
        }
    )
    assert resp.status_code == 200, resp.text
    
    # Create test class
    test_code = '''
import org.scalatest.funsuite.AnyFunSuite

class CalculatorTest extends AnyFunSuite {
  test("Calculator.add") {
    assert(Calculator.add(1, 2) == 3)
  }
}
'''
    
    resp = client.put(
        "/files",
        json={
            "workspace_name": workspace_name,
            "file_path": "src/test/scala/CalculatorTest.scala",
            "content": test_code
        }
    )
    assert resp.status_code == 200, resp.text
    
    # Update build.sbt to include ScalaTest
    build_sbt = '''
name := "Test Project"
version := "0.1.0"
scalaVersion := "2.13.12"

libraryDependencies ++= Seq(
  "org.scalatest" %% "scalatest" % "3.2.18" % Test
)
'''
    
    resp = client.put(
        "/files",
        json={
            "workspace_name": workspace_name,
            "file_path": "build.sbt",
            "content": build_sbt
        }
    )
    assert resp.status_code == 200, resp.text
    
    # Run tests
    resp = client.post(
        "/sbt/test",
        json={"workspace_name": workspace_name},
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")

@pytest.mark.integration
def test_sbt_clean_command():
    """Test SBT clean command"""
    workspace_name = f"test-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Run clean command
    resp = client.post(
        "/sbt/clean",
        json={"workspace_name": workspace_name},
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")

@pytest.mark.integration
def test_complex_scala_project():
    """Test complex Scala project structure"""
    workspace_name = f"test-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Read the complex test file
    try:
        with open("./tests/scala_files/parse.scala") as f:
            scala_code = f.read()
        
        resp = client.put(
            "/files",
            json={
                "workspace_name": workspace_name,
                "file_path": "src/main/scala/ParseExample.scala",
                "content": scala_code
            }
        )
        assert resp.status_code == 200, resp.text
        
        # Try to compile (may need dependencies)
        resp = client.post(
            "/sbt/compile",
            json={"workspace_name": workspace_name},
            timeout=120
        )
        assert resp.status_code == 200, resp.text
    except FileNotFoundError:
        # Skip if test file doesn't exist
        pass
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")