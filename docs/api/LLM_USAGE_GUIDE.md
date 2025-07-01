# Scala Runner Tools - LLM Usage Guide

## Overview

The Scala Runner Tools provide a comprehensive API client for interacting with a Scala development environment service. These tools enable LLMs to perform workspace management, file operations, Git version control, SBT build operations, search functionality, and bash session management.

## Tool Call Format

All tools are called using JSON function calls with the following format:
- **Function Name**: The method name (e.g., `create_workspace`, `sbt_compile`)
- **Parameters**: A JSON object with the required parameters

Example:
```json
{
  "workspace_name": "my-project",
  "command": "compile"
}
```

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
**Function:** `ping`
```json
{}
```
**Returns:** `"pong"` or `{"error": "..."}`

### 2. Workspace Management

#### Create a New Workspace
**Function:** `create_workspace`
```json
{
  "name": "my-scala-project"
}
```

#### Clone from Git Repository
**Function:** `clone_workspace_from_git`
```json
{
  "name": "external-project",
  "git_url": "https://github.com/user/scala-project.git",
  "branch": "main"
}
```
Note: `branch` parameter is optional.

#### List All Workspaces
**Function:** `list_workspaces`
```json
{}
```
**Returns:** `{"workspaces": [{"name": "workspace1", ...}, ...]}`

#### Get Workspace File Tree
**Function:** `get_workspace_tree`
```json
{
  "workspace_name": "my-scala-project"
}
```
**Returns:** `{"tree": {"type": "directory", "children": {...}}}`

#### Delete Workspace
**Function:** `delete_workspace`
```json
{
  "workspace_name": "my-scala-project"
}
```

### 3. File Operations

#### Create New File
**Function:** `create_file`
```json
{
  "workspace_name": "my-scala-project",
  "file_path": "src/main/scala/Main.scala",
  "content": "object Main extends App {\n  println(\"Hello, Scala!\")\n  \n  def fibonacci(n: Int): Int = {\n    if (n <= 1) n\n    else fibonacci(n - 1) + fibonacci(n - 2)\n  }\n  \n  println(s\"Fibonacci(10) = ${fibonacci(10)}\")\n}"
}
```

#### Read File Content
**Function:** `get_file_content`
```json
{
  "workspace_name": "my-scala-project",
  "file_path": "src/main/scala/Main.scala"
}
```
**Returns:** `{"content": "file content here", "file_path": "..."}`

#### Update Existing File
**Function:** `update_file`
```json
{
  "workspace_name": "my-scala-project",
  "file_path": "src/main/scala/Main.scala",
  "content": "object Main extends App {\n  println(\"Hello, Updated Scala!\")\n  \n  def factorial(n: Int): Long = {\n    if (n <= 1) 1L\n    else n * factorial(n - 1)\n  }\n  \n  def fibonacci(n: Int): Int = {\n    if (n <= 1) n\n    else fibonacci(n - 1) + fibonacci(n - 2)\n  }\n  \n  println(s\"Factorial(5) = ${factorial(5)}\")\n  println(s\"Fibonacci(10) = ${fibonacci(10)}\")\n}"
}
```

#### Delete File
**Function:** `delete_file`
```json
{
  "workspace_name": "my-scala-project",
  "file_path": "src/main/scala/Main.scala"
}
```

#### Create Build Configuration
**Function:** `create_file`
```json
{
  "workspace_name": "my-scala-project",
  "file_path": "build.sbt",
  "content": "ThisBuild / version := \"0.1.0-SNAPSHOT\"\nThisBuild / scalaVersion := \"3.3.0\"\n\nlazy val root = (project in file(\".\"))\n  .settings(\n    name := \"my-scala-project\",\n    libraryDependencies ++= Seq(\n      \"org.typelevel\" %% \"cats-core\" % \"2.9.0\",\n      \"org.scalatest\" %% \"scalatest\" % \"3.2.15\" % Test\n    )\n  )"
}
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
**Function:** `apply_patch`
```json
{
  "workspace_name": "my-scala-project",
  "patch": "--- a/build.sbt\n+++ b/build.sbt\n@@ -4,7 +4,8 @@ ThisBuild / scalaVersion := \"3.3.0\"\n lazy val root = (project in file(\".\"))\n   .settings(\n     name := \"my-scala-project\",\n     libraryDependencies ++= Seq(\n       \"org.typelevel\" %% \"cats-core\" % \"2.9.0\",\n-      \"org.scalatest\" %% \"scalatest\" % \"3.2.15\" % Test\n+      \"org.scalatest\" %% \"scalatest\" % \"3.2.15\" % Test,\n+      \"org.scalamock\" %% \"scalamock\" % \"5.2.0\" % Test\n     )\n   )\n\n--- /dev/null\n+++ b/src/test/scala/MainTest.scala\n@@ -0,0 +1,15 @@\n+import org.scalatest.funsuite.AnyFunSuite\n+\n+class MainTest extends AnyFunSuite {\n+  test(\"factorial should compute correctly\") {\n+    // Note: This assumes factorial method is accessible\n+    assert(factorial(0) == 1)\n+    assert(factorial(1) == 1)\n+    assert(factorial(5) == 120)\n+  }\n+  \n+  test(\"fibonacci should compute correctly\") {\n+    assert(fibonacci(0) == 0)\n+    assert(fibonacci(1) == 1)\n+    assert(fibonacci(10) == 55)\n+  }\n+}"
}
```

#### Example: Refactor Code Structure
**Function:** `apply_patch`
```json
{
  "workspace_name": "my-scala-project",
  "patch": "--- a/src/main/scala/Main.scala\n+++ b/src/main/scala/Main.scala\n@@ -1,12 +1,5 @@\n object Main extends App {\n   println(\"Hello, Updated Scala!\")\n-  \n-  def factorial(n: Int): Long = {\n-    if (n <= 1) 1L\n-    else n * factorial(n - 1)\n-  }\n-  \n-  def fibonacci(n: Int): Int = {\n-    if (n <= 1) n\n-    else fibonacci(n - 1) + fibonacci(n - 2)\n-  }\n+\n+  import MathUtils._\n   \n   println(s\"Factorial(5) = ${factorial(5)}\")\n\n--- /dev/null\n+++ b/src/main/scala/MathUtils.scala\n@@ -0,0 +1,11 @@\n+object MathUtils {\n+  def factorial(n: Int): Long = {\n+    if (n <= 1) 1L\n+    else n * factorial(n - 1)\n+  }\n+  \n+  def fibonacci(n: Int): Int = {\n+    if (n <= 1) n\n+    else fibonacci(n - 1) + fibonacci(n - 2)\n+  }\n+}"
}
```

### 5. SBT Operations

#### Compile Project
**Function:** `sbt_compile`
```json
{
  "workspace_name": "my-scala-project",
  "timeout": 60
}
```
**Returns:** `{"success": true, "output": "compilation output"}`

#### Run Main Class
**Function:** `sbt_run`
```json
{
  "workspace_name": "my-scala-project",
  "main_class": "Main",
  "timeout": 30
}
```
Note: `main_class` parameter is optional (auto-detected if not specified).

#### Run Tests
**Function:** `sbt_test`
```json
{
  "workspace_name": "my-scala-project",
  "timeout": 60
}
```

**Run specific test:**
```json
{
  "workspace_name": "my-scala-project",
  "test_name": "MainTest",
  "timeout": 30
}
```

#### Clean Build Artifacts
**Function:** `sbt_clean`
```json
{
  "workspace_name": "my-scala-project"
}
```

#### Custom SBT Commands
**Function:** `sbt_custom_command`
```json
{
  "workspace_name": "my-scala-project",
  "command": "dependencyTree",
  "timeout": 45
}
```

**Check for dependency updates:**
```json
{
  "workspace_name": "my-scala-project",
  "command": "dependencyUpdates"
}
```

### 6. Git Operations

#### Check Repository Status
**Function:** `git_status`
```json
{
  "workspace_name": "my-scala-project"
}
```
**Returns:** `{"staged": [...], "unstaged": [...], "untracked": [...]}`

#### Add Files to Staging
**Function:** `git_add`
```json
{
  "workspace_name": "my-scala-project",
  "file_paths": ["src/main/scala/Main.scala", "build.sbt"]
}
```

**Add all files (omit file_paths):**
```json
{
  "workspace_name": "my-scala-project"
}
```

#### Commit Changes
**Function:** `git_commit`
```json
{
  "workspace_name": "my-scala-project",
  "message": "Add factorial and fibonacci functions",
  "author_name": "AI Assistant",
  "author_email": "ai@assistant.com"
}
```

### 7. Search Operations

**Function:** `search_files`
```json
{
  "workspace_name": "my-scala-project",
  "query": "def factorial",
  "limit": 10
}
```
**Returns:** `{"data": {"results": [{"file": "...", "line": 123, "content": "..."}], "count": 1}}`

**Search for imports:**
```json
{
  "workspace_name": "my-scala-project",
  "query": "import cats",
  "limit": 5
}
```

### 8. Bash Session Management

#### Create and Use Bash Session
**Create session - Function:** `create_bash_session`
```json
{
  "workspace_name": "my-scala-project"
}
```

**Execute commands in session - Function:** `execute_bash_command`
```json
{
  "session_id": "session_id_from_create_response",
  "command": "ls -la src/",
  "timeout": 10
}
```

**Commands maintain context within session:**
```json
{
  "session_id": "session_id_from_create_response",
  "command": "cd src/main/scala && grep -n 'def ' *.scala",
  "timeout": 15
}
```

**Close session when done - Function:** `close_bash_session`
```json
{
  "session_id": "session_id_from_create_response"
}
```

#### List Active Sessions
**Function:** `list_bash_sessions`
```json
{}
```

**List sessions for specific workspace:**
```json
{
  "workspace_name": "my-scala-project"
}
```

## Best Practices and Workflows

### 1. Project Setup Workflow
1. **Create workspace** - `create_workspace`
   ```json
   {"name": "new-project"}
   ```

2. **Create basic structure** - `create_file`
   ```json
   {"workspace_name": "new-project", "file_path": "build.sbt", "content": "build_sbt_content"}
   ```
   ```json
   {"workspace_name": "new-project", "file_path": "src/main/scala/Main.scala", "content": "main_scala_content"}
   ```

3. **Compile to verify setup** - `sbt_compile`
   ```json
   {"workspace_name": "new-project"}
   ```

4. **Initialize git if needed** - `create_bash_session` then `execute_bash_command`
   ```json
   {"workspace_name": "new-project"}
   ```
   ```json
   {"session_id": "session_id", "command": "git init"}
   ```

### 2. Development Workflow
1. **Make code changes** (create/update files or apply patches)
2. **Compile to check for errors** - `sbt_compile`
   ```json
   {"workspace_name": "my-project"}
   ```

3. **Run tests** - `sbt_test`
   ```json
   {"workspace_name": "my-project"}
   ```

4. **If tests pass, commit changes** - `git_add` then `git_commit`
   ```json
   {"workspace_name": "my-project"}
   ```
   ```json
   {"workspace_name": "my-project", "message": "Add new feature"}
   ```

### 3. Code Exploration Workflow
1. **Get workspace structure** - `get_workspace_tree`
   ```json
   {"workspace_name": "existing-project"}
   ```

2. **Search for patterns of interest** - `search_files`
   ```json
   {"workspace_name": "existing-project", "query": "class.*extends"}
   ```

3. **Read relevant files** - `get_file_content`
   ```json
   {"workspace_name": "existing-project", "file_path": "path/from/search/results"}
   ```

## Error Handling

Always check for errors in responses:

**Function call:**
```json
{"workspace_name": "my-project"}
```

**Response handling:**
- If response contains `"error"` key: `{"error": "compilation failed: ..."}`
- If successful: `{"success": true, "output": "compilation output"}`

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