# Scala Runner Tools - LLM Usage Guide

## Overview

The Scala Runner Tools provide a comprehensive API client for interacting with a Scala development environment service. These tools enable LLMs to perform workspace management, file operations, Git version control, SBT build operations, search functionality, and bash session management.

## Core Concepts

### Workspaces
- **Workspace**: A project container with its own file system, Git repository, and SBT configuration
- **Isolation**: Each workspace is isolated from others, allowing multiple projects simultaneously
- **Persistence**: Workspaces persist across sessions until explicitly deleted

### Async Operations
- All operations are asynchronous and return either success data or error objects
- Success responses contain structured data with operation results
- Error responses contain `{"error": "description"}` format

## Available Operations

### 1. Health Check
```python
# Check if the service is running
result = await tools.ping()
# Returns: "pong" or {"error": "..."}
```

### 2. Workspace Management

#### Create a New Workspace
```python
# Create a basic SBT project workspace
result = await tools.create_workspace("my-scala-project")
```

#### Clone from Git Repository
```python
# Clone existing repository into workspace
result = await tools.clone_workspace_from_git(
    name="external-project",
    git_url="https://github.com/user/scala-project.git",
    branch="main"  # optional
)
```

#### List All Workspaces
```python
result = await tools.list_workspaces()
# Returns: {"workspaces": [{"name": "workspace1", ...}, ...]}
```

#### Get Workspace File Tree
```python
result = await tools.get_workspace_tree("my-scala-project")
# Returns: {"tree": {"type": "directory", "children": {...}}}
```

#### Delete Workspace
```python
result = await tools.delete_workspace("my-scala-project")
```

### 3. File Operations

#### Create New File
```python
# Create a Scala source file
result = await tools.create_file(
    workspace_name="my-scala-project",
    file_path="src/main/scala/Main.scala",
    content="""object Main extends App {
  println("Hello, Scala!")
  
  def fibonacci(n: Int): Int = {
    if (n <= 1) n
    else fibonacci(n - 1) + fibonacci(n - 2)
  }
  
  println(s"Fibonacci(10) = ${fibonacci(10)}")
}"""
)
```

#### Read File Content
```python
result = await tools.get_file_content(
    workspace_name="my-scala-project",
    file_path="src/main/scala/Main.scala"
)
# Returns: {"content": "file content here", "file_path": "..."}
```

#### Update Existing File
```python
# Update the Main.scala file with new content
result = await tools.update_file(
    workspace_name="my-scala-project",
    file_path="src/main/scala/Main.scala",
    content="""object Main extends App {
  println("Hello, Updated Scala!")
  
  def factorial(n: Int): Long = {
    if (n <= 1) 1L
    else n * factorial(n - 1)
  }
  
  def fibonacci(n: Int): Int = {
    if (n <= 1) n
    else fibonacci(n - 1) + fibonacci(n - 2)
  }
  
  println(s"Factorial(5) = ${factorial(5)}")
  println(s"Fibonacci(10) = ${fibonacci(10)}")
}"""
)
```

#### Delete File
```python
result = await tools.delete_file(
    workspace_name="my-scala-project",
    file_path="src/main/scala/Main.scala"
)
```

#### Create Build Configuration
```python
# Create build.sbt file
result = await tools.create_file(
    workspace_name="my-scala-project",
    file_path="build.sbt",
    content="""ThisBuild / version := "0.1.0-SNAPSHOT"
ThisBuild / scalaVersion := "3.3.0"

lazy val root = (project in file("."))
  .settings(
    name := "my-scala-project",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-core" % "2.9.0",
      "org.scalatest" %% "scalatest" % "3.2.15" % Test
    )
  )"""
)
```

### 4. Advanced File Operations - Patch Functionality

The patch operation allows you to apply Git-style diff patches to multiple files simultaneously. This is powerful for making complex, multi-file changes.

#### Understanding Patch Format
Patches use standard Git diff format:
```diff
--- a/path/to/file.scala
+++ b/path/to/file.scala
@@ -line_start,line_count +line_start,line_count @@
-removed line
+added line
 unchanged line
```

#### Example: Add Dependencies and Update Code
```python
# Patch to add test dependencies and create test file
patch_content = """--- a/build.sbt
+++ b/build.sbt
@@ -4,7 +4,8 @@ ThisBuild / scalaVersion := "3.3.0"
 lazy val root = (project in file("."))
   .settings(
     name := "my-scala-project",
     libraryDependencies ++= Seq(
       "org.typelevel" %% "cats-core" % "2.9.0",
-      "org.scalatest" %% "scalatest" % "3.2.15" % Test
+      "org.scalatest" %% "scalatest" % "3.2.15" % Test,
+      "org.scalamock" %% "scalamock" % "5.2.0" % Test
     )
   )

--- /dev/null
+++ b/src/test/scala/MainTest.scala
@@ -0,0 +1,15 @@
+import org.scalatest.funsuite.AnyFunSuite
+
+class MainTest extends AnyFunSuite {
+  test("factorial should compute correctly") {
+    // Note: This assumes factorial method is accessible
+    assert(factorial(0) == 1)
+    assert(factorial(1) == 1)
+    assert(factorial(5) == 120)
+  }
+  
+  test("fibonacci should compute correctly") {
+    assert(fibonacci(0) == 0)
+    assert(fibonacci(1) == 1)
+    assert(fibonacci(10) == 55)
+  }
+}"""

result = await tools.apply_patch("my-scala-project", patch_content)
```

#### Example: Refactor Code Structure
```python
# Patch to split Main.scala into separate files
refactor_patch = """--- a/src/main/scala/Main.scala
+++ b/src/main/scala/Main.scala
@@ -1,12 +1,5 @@
 object Main extends App {
   println("Hello, Updated Scala!")
-  
-  def factorial(n: Int): Long = {
-    if (n <= 1) 1L
-    else n * factorial(n - 1)
-  }
-  
-  def fibonacci(n: Int): Int = {
-    if (n <= 1) n
-    else fibonacci(n - 1) + fibonacci(n - 2)
-  }
+
+  import MathUtils._
   
   println(s"Factorial(5) = ${factorial(5)}")

--- /dev/null
+++ b/src/main/scala/MathUtils.scala
@@ -0,0 +1,11 @@
+object MathUtils {
+  def factorial(n: Int): Long = {
+    if (n <= 1) 1L
+    else n * factorial(n - 1)
+  }
+  
+  def fibonacci(n: Int): Int = {
+    if (n <= 1) n
+    else fibonacci(n - 1) + fibonacci(n - 2)
+  }
+}"""

result = await tools.apply_patch("my-scala-project", refactor_patch)
```

### 5. SBT Operations

#### Compile Project
```python
result = await tools.sbt_compile("my-scala-project", timeout=60)
# Returns: {"success": true, "output": "compilation output"}
```

#### Run Main Class
```python
result = await tools.sbt_run(
    workspace_name="my-scala-project",
    main_class="Main",  # optional, auto-detected if not specified
    timeout=30
)
```

#### Run Tests
```python
# Run all tests
result = await tools.sbt_test("my-scala-project", timeout=60)

# Run specific test
result = await tools.sbt_test(
    workspace_name="my-scala-project",
    test_name="MainTest",
    timeout=30
)
```

#### Clean Build Artifacts
```python
result = await tools.sbt_clean("my-scala-project")
```

#### Custom SBT Commands
```python
# Run custom SBT command
result = await tools.sbt_custom_command(
    workspace_name="my-scala-project",
    command="dependencyTree",
    timeout=45
)

# Check for dependency updates
result = await tools.sbt_custom_command(
    workspace_name="my-scala-project",
    command="dependencyUpdates"
)
```

### 6. Git Operations

#### Check Repository Status
```python
result = await tools.git_status("my-scala-project")
# Returns: {"staged": [...], "unstaged": [...], "untracked": [...]}
```

#### Add Files to Staging
```python
# Add specific files
result = await tools.git_add(
    workspace_name="my-scala-project",
    file_paths=["src/main/scala/Main.scala", "build.sbt"]
)

# Add all files (omit file_paths)
result = await tools.git_add("my-scala-project")
```

#### Commit Changes
```python
result = await tools.git_commit(
    workspace_name="my-scala-project",
    message="Add factorial and fibonacci functions",
    author_name="AI Assistant",
    author_email="ai@assistant.com"
)
```

### 7. Search Operations

```python
# Search for specific code patterns
result = await tools.search_files(
    workspace_name="my-scala-project",
    query="def factorial",
    limit=10
)
# Returns: {"data": {"results": [{"file": "...", "line": 123, "content": "..."}], "count": 1}}

# Search for imports
result = await tools.search_files(
    workspace_name="my-scala-project",
    query="import cats",
    limit=5
)
```

### 8. Bash Session Management

#### Create and Use Bash Session
```python
# Create session
session_result = await tools.create_bash_session("my-scala-project")
session_id = session_result["session_id"]

# Execute commands in session
result = await tools.execute_bash_command(
    session_id=session_id,
    command="ls -la src/",
    timeout=10
)

# Commands maintain context within session
result = await tools.execute_bash_command(
    session_id=session_id,
    command="cd src/main/scala && grep -n 'def ' *.scala",
    timeout=15
)

# Close session when done
result = await tools.close_bash_session(session_id)
```

#### List Active Sessions
```python
# List all sessions
result = await tools.list_bash_sessions()

# List sessions for specific workspace
result = await tools.list_bash_sessions("my-scala-project")
```

## Best Practices and Workflows

### 1. Project Setup Workflow
```python
# 1. Create workspace
await tools.create_workspace("new-project")

# 2. Create basic structure
await tools.create_file("new-project", "build.sbt", build_sbt_content)
await tools.create_file("new-project", "src/main/scala/Main.scala", main_scala_content)

# 3. Compile to verify setup
compile_result = await tools.sbt_compile("new-project")

# 4. Initialize git if needed
bash_session = await tools.create_bash_session("new-project")
await tools.execute_bash_command(bash_session["session_id"], "git init")
```

### 2. Development Workflow
```python
# 1. Make code changes (create/update files or apply patches)
# 2. Compile to check for errors
compile_result = await tools.sbt_compile("my-project")

# 3. Run tests
test_result = await tools.sbt_test("my-project")

# 4. If tests pass, commit changes
if test_result.get("success"):
    await tools.git_add("my-project")
    await tools.git_commit("my-project", "Add new feature")
```

### 3. Code Exploration Workflow
```python
# 1. Get workspace structure
tree = await tools.get_workspace_tree("existing-project")

# 2. Search for patterns of interest
search_results = await tools.search_files("existing-project", "class.*extends")

# 3. Read relevant files
for result in search_results["data"]["results"]:
    content = await tools.get_file_content("existing-project", result["file"])
    # analyze content...
```

## Error Handling

Always check for errors in responses:

```python
result = await tools.sbt_compile("my-project")
if "error" in result:
    print(f"Compilation failed: {result['error']}")
    # Handle error appropriately
else:
    print("Compilation successful!")
    # Continue with next steps
```

## Tips for LLMs

1. **Always verify workspace exists** before performing operations
2. **Use descriptive commit messages** when using Git operations
3. **Compile frequently** during development to catch errors early
4. **Use patches for complex multi-file changes** rather than individual file operations
5. **Clean up bash sessions** when no longer needed to free resources
6. **Search before modifying** to understand existing code structure
7. **Use timeouts appropriately** - longer for compilation/tests, shorter for simple commands
8. **Check file tree structure** before creating files to ensure proper directory structure

## Common Patterns

### Adding a New Feature
1. Search existing code to understand patterns
2. Create/update necessary files
3. Update build configuration if needed
4. Compile and test
5. Commit changes

### Debugging Issues
1. Check compilation errors via `sbt_compile`
2. Run specific tests via `sbt_test`
3. Use bash sessions for advanced debugging
4. Search for similar patterns in codebase

### Refactoring Code
1. Use search to find all usages
2. Create patch for multi-file changes
3. Compile to verify correctness
4. Run full test suite
5. Commit with descriptive message 