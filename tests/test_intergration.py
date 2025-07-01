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
        json={"workspace_name": workspace_name, "main_class": "DirectIntegration"},
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
scalaVersion := "2.13.14"

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
        json={"workspace_name": workspace_name, "main_class": "CatsExample"},
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
scalaVersion := "2.13.14"

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

@pytest.mark.integration
def test_intensive_patch_api_integration():
    """
    Intensive integration test that utilizes the patch API to:
    1. Create new project with patched build.sbt
    2. Create and patch README.md to demonstrate patch functionality
    3. Create working Main.scala via PUT
    4. Run sbt compile and run
    5. Verify patches were applied correctly
    6. Clean up
    """
    workspace_name = f"test-patch-workspace-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    try:
        # Step 1: Create workspace
        resp = client.post(
            "/workspaces",
            json={"name": workspace_name}
        )
        assert resp.status_code == 200, f"Failed to create workspace: {resp.text}"
        
        # Step 2: Patch build.sbt for the Scala 3 project
        # This patch creates a new build.sbt with Scala 3
        build_sbt_patch = """--- /dev/null
+++ b/build.sbt
@@ -0,0 +1,3 @@
+name := "ParseProject"
+version := "0.1.0"
+scalaVersion := "3.6.4\""""
        
        resp = client.patch(
            "/files",
            json={
                "workspace_name": workspace_name,
                "patch": build_sbt_patch
            }
        )
        assert resp.status_code == 200, f"Failed to patch build.sbt: {resp.text}"
        build_result = resp.json()
        assert build_result["status"] == "success"
        assert build_result["data"]["patch_applied"] == True
        assert len(build_result["data"]["results"]["modified_files"]) == 1
        assert build_result["data"]["results"]["modified_files"][0]["file_path"] == "build.sbt"
        assert build_result["data"]["results"]["modified_files"][0]["status"] == "success"
        
        # Step 3: Create a simple Scala file and test PATCH API with README.md
        # Create a working Scala file using PUT to ensure compilation works
        main_scala_content = """object Main {
  def main(args: Array[String]): Unit = println("✅ Patch API integration test passed")
}"""
        
        resp = client.put(
            "/files",
            json={
                "workspace_name": workspace_name,
                "file_path": "src/main/scala/Main.scala",
                "content": main_scala_content
            }
        )
        assert resp.status_code == 200, f"Failed to create Main.scala: {resp.text}"
        
        # Test PATCH API functionality using README.md to avoid Scala syntax issues
        readme_patch = """--- /dev/null
+++ b/README.md
@@ -0,0 +1,3 @@
+# Test Project
+
+This project tests the patch API."""
        
        resp = client.patch(
            "/files",
            json={
                "workspace_name": workspace_name,
                "patch": readme_patch
            }
        )
        assert resp.status_code == 200, f"Failed to create README.md via patch: {resp.text}"
        
        # Now patch README.md to add more content - this tests the core patch functionality
        readme_update_patch = """--- a/README.md
+++ b/README.md
@@ -1,3 +1,5 @@
 # Test Project

 This project tests the patch API.
+
+✅ Patch API is working correctly!"""
        
        resp = client.patch(
            "/files",
            json={
                "workspace_name": workspace_name,
                "patch": readme_update_patch
            }
        )
        assert resp.status_code == 200, f"Failed to patch README.md: {resp.text}"
        patch_result = resp.json()
        assert patch_result["status"] == "success"
        assert patch_result["data"]["patch_applied"] == True
        assert len(patch_result["data"]["results"]["modified_files"]) == 1
        assert patch_result["data"]["results"]["modified_files"][0]["file_path"] == "README.md"
        assert patch_result["data"]["results"]["modified_files"][0]["status"] == "success"
        
        # Step 4: Run sbt compile to verify the patched project compiles successfully
        resp = client.post(
            "/sbt/compile",
            json={"workspace_name": workspace_name},
            timeout=180  # Increased timeout for dependency download and compilation
        )
        assert resp.status_code == 200, f"SBT compile failed: {resp.text}"
        compile_result = resp.json()
        assert compile_result["status"] == "success", f"Compilation failed: {compile_result}"
        
        # Step 5: Verify the result by running the project
        resp = client.post(
            "/sbt/run-project",
            json={"workspace_name": workspace_name, "main_class": "Main"},
            timeout=120
        )
        assert resp.status_code == 200, f"SBT run failed: {resp.text}"
        run_result = resp.json()
        assert run_result["status"] == "success", f"Run failed: {run_result}"
        
        # Verify the output contains expected results
        output = run_result["data"]["output"]
        assert "✅ Patch API integration test passed" in output, f"Expected patch API message not found in output: {output}"
        
        # Additional verification: Check that files were actually created and contain expected content
        resp = client.get(f"/files/{workspace_name}/build.sbt")
        assert resp.status_code == 200, "Failed to read build.sbt"
        build_content = resp.json()["data"]["content"]
        assert "ParseProject" in build_content, "Project name not found in build.sbt"
        assert "3.6.4" in build_content, "Scala 3.6.4 version not found in build.sbt"
        
        resp = client.get(f"/files/{workspace_name}/src/main/scala/Main.scala")
        assert resp.status_code == 200, "Failed to read Main.scala"
        main_content = resp.json()["data"]["content"]
        assert "object Main" in main_content, "Main object not found in Main.scala"
        assert "Patch API integration test passed" in main_content, "Main.scala content not found"
        
        # Verify README.md was created and updated via PATCH API
        resp = client.get(f"/files/{workspace_name}/README.md")
        assert resp.status_code == 200, "Failed to read README.md"
        readme_content = resp.json()["data"]["content"]
        assert "# Test Project" in readme_content, "README title not found"
        assert "This project tests the patch API." in readme_content, "Initial content not found in README.md"
        assert "✅ Patch API is working correctly!" in readme_content, "Patch update not found in README.md"
        
        # Test clean command
        resp = client.post(
            "/sbt/clean",
            json={"workspace_name": workspace_name},
            timeout=60
        )
        assert resp.status_code == 200, f"SBT clean failed: {resp.text}"
        clean_result = resp.json()
        assert clean_result["status"] == "success", f"Clean failed: {clean_result}"
        
        print(f"✅ Intensive patch API integration test completed successfully for workspace: {workspace_name}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        raise
    finally:
        # Step 6: Clean up - delete workspace
        try:
            resp = client.delete(f"/workspaces/{workspace_name}")
            if resp.status_code != 200:
                print(f"Warning: Failed to cleanup workspace {workspace_name}: {resp.text}")
        except Exception as cleanup_error:
            print(f"Warning: Cleanup failed: {cleanup_error}")

@pytest.mark.integration
def test_workspace_file_tree_filtering():
    """Test workspace file tree filtering functionality via API"""
    workspace_name = f"test-workspace-filter-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Create workspace
    resp = client.post(
        "/workspaces",
        json={"name": workspace_name}
    )
    assert resp.status_code == 200, resp.text
    
    # Create some files that should be filtered
    files = [
        ("src/main/scala/Main.scala", "object Main { def main(args: Array[String]): Unit = println(\"Hello\") }"),
        ("README.md", "# Test Project"),
        ("target/classes/Main.class", "compiled bytecode"),  # Should be filtered
        (".bsp/sbt.json", '{"name": "sbt"}'),  # Should be filtered
        ("build.log", "compilation log"),  # Should be filtered
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
    
    # Test with default filtering (show_all=False)
    resp = client.get(f"/workspaces/{workspace_name}/tree")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    
    # Helper function to collect all names in tree
    def collect_names(tree):
        names = {tree["name"]}
        if "children" in tree:
            for child in tree["children"]:
                names.update(collect_names(child))
        return names
    
    filtered_names = collect_names(body["data"]["tree"])
    
    # Should include regular files
    assert "Main.scala" in filtered_names
    assert "README.md" in filtered_names
    assert "src" in filtered_names
    
    # Should exclude filtered files/directories
    assert "target" not in filtered_names
    assert ".bsp" not in filtered_names
    assert "build.log" not in filtered_names
    assert "Main.class" not in filtered_names
    
    # Test with show_all=True
    resp = client.get(f"/workspaces/{workspace_name}/tree?show_all=true")
    assert resp.status_code == 200, resp.text
    body_all = resp.json()
    
    all_names = collect_names(body_all["data"]["tree"])
    
    # Should include everything
    assert "Main.scala" in all_names
    assert "README.md" in all_names
    assert "src" in all_names
    assert "target" in all_names
    assert ".bsp" in all_names
    assert "build.log" in all_names
    assert "Main.class" in all_names
    
    print(f"Filtered names: {filtered_names}")
    print(f"All names: {all_names}")
    print(f"Filtered count: {len(all_names) - len(filtered_names)}")
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")