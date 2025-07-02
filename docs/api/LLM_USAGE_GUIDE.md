# Scala Runner Tools - LLM Usage Guide

## Overview

The Scala Runner Tools provide a comprehensive API client for interacting with a Scala development environment service. These tools enable LLMs to perform workspace management, file operations, Git version control, SBT build operations, search functionality, and bash session management.

**⚠️ PATCH OPERATIONS ARE THE PREFERRED METHOD FOR FILE MODIFICATIONS** - Use patches for multi-file changes, refactoring, and complex modifications instead of individual file operations.

## Tool Call Format

All tools are called using JSON function calls with the following format:
- **Function Name**: The method name (e.g., `create_workspace`, `sbt_compile`, `apply_patch`)
- **Parameters**: A JSON object with the required parameters

Example:
```json
{
  "workspace_name": "my-project",
  "patch": "--- a/Main.scala\n+++ b/Main.scala\n@@ -1,1 +1,1 @@\n-old line\n+new line"
}
```

## Core Concepts

### Workspaces
- **Workspace**: A project container with its own file system, Git repository, and SBT configuration
- **Isolation**: Each workspace is isolated from others, allowing multiple projects simultaneously
- **Persistence**: Workspaces persist across sessions until explicitly deleted

### Patch-First Approach
- **Git Diff Format**: All patches use standard unified diff format (git diff output)
- **Multi-file Operations**: Single patch can modify multiple files simultaneously
- **Atomic Changes**: Patches are applied atomically - either all changes succeed or none do
- **Error Validation**: Comprehensive syntax validation with specific error codes

### Async Operations
- All operations are asynchronous and return either success data or error objects
- Success responses contain structured data with operation results
- Error responses contain `{"error": "description"}` format

## 🔥 PATCH OPERATIONS (PRIMARY FILE MODIFICATION METHOD)

### Understanding Git Diff Patch Format

**Basic Structure:**
```diff
--- a/path/to/old/file.scala    # Old file path (required)
+++ b/path/to/new/file.scala    # New file path (required)
@@ -old_start,old_count +new_start,new_count @@   # Hunk header (required)
 context line (unchanged)       # Lines starting with space = context
-removed line                   # Lines starting with minus = deleted
+added line                     # Lines starting with plus = added
```

**Critical Patch Syntax Rules:**
1. **File Headers are MANDATORY**: Every hunk must have `---` and `+++` headers
2. **Hunk Headers Must Match Pattern**: `@@ -old_start,old_count +new_start,new_count @@`
3. **Valid Line Prefixes Only**: ` ` (space), `+`, `-`, or `\` (special markers)
4. **No Invalid Prefixes**: Do not use `*`, `!`, `#`, or any other characters

### 🔍 MANDATORY PRE-PATCH WORKFLOW

**⚠️ CRITICAL REQUIREMENT: Always use get_file_content_by_lines before creating patches**

**🎯 SINGLE FILE, SINGLE LOCATION RULE:**
- **ONLY modify ONE file in ONE location per patch**
- **ALWAYS verify the result using get_file_content_by_lines after applying patches**
- **NEVER combine multiple files or multiple locations in a single patch**

Before applying any patch, you MUST:

#### Step 1: Search for Target Code (Optional but Recommended)
```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "target_function_or_pattern",
    "limit": 10
  }
}
```

#### Step 2: Get File Content by Lines (MANDATORY)
**You MUST use this function to get the exact content and line numbers before creating any patch:**

```json
{
  "function": "get_file_content_by_lines",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/MyFile.scala",
    "start_line": 1,
    "end_line": 50
  }
}
```

**Why this is critical:**
- Ensures you have the exact content that exists in the file
- Provides accurate line numbers for hunk headers
- Prevents patches from failing due to content mismatches
- Allows you to see the precise context around your target changes

#### Step 3: Create Patch with Exact Content (SINGLE CHANGE ONLY)
Only after getting the exact file content, create your patch using the **exact text** from the file:

```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/MyFile.scala\n+++ b/src/main/scala/MyFile.scala\n@@ -5,8 +5,10 @@\n  exact_context_from_file\n  exact_line_to_modify\n+  new_line_to_add\n  exact_context_after"
  }
}
```

#### Step 4: Verify Changes (MANDATORY)
**ALWAYS verify your patch was applied correctly:**

```json
{
  "function": "get_file_content_by_lines",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/MyFile.scala",
    "start_line": 1,
    "end_line": 60
  }
}
```

**Check for:**
- [ ] Your changes are present in the exact location expected
- [ ] No unintended side effects or corrupted content
- [ ] Line numbers and content structure are correct
- [ ] The file compiles (run `sbt_compile` after verification)

### Apply Patch Operation
**Function:** `apply_patch`
```json
{
  "workspace_name": "my-scala-project",
  "patch": "PATCH_CONTENT_HERE"
}
```

### 🚨 PATCH CREATION BEST PRACTICES

#### ✅ DO:
1. **Always call `get_file_content_by_lines` first**
2. **Modify ONLY ONE file in ONE location per patch**
3. **Always verify result with `get_file_content_by_lines` after patch**
4. Use exact content from the file response
5. Include sufficient context (3-5 lines before and after changes)
6. Make one atomic change per patch
7. Verify line numbers match the file content
8. Use proper git diff format
9. **Compile after each verified patch** (`sbt_compile`)

#### ❌ DON'T:
1. Create patches without first reading the file content
2. **NEVER modify multiple files in one patch**
3. **NEVER modify multiple locations in one file without verification**
4. Guess at file content or line numbers
5. Skip verification step after applying patches
6. Mix multiple unrelated changes in one patch
7. Use invalid line prefixes
8. Omit required file headers
9. Create patches with incorrect hunk mathematics

### 🎯 RECOMMENDED WORKFLOW FOR FILE MODIFICATIONS

#### 🚨 CRITICAL: One File, One Location, One Change At A Time

**MANDATORY SINGLE FILE WORKFLOW:**
1. **Search** (optional): Find the target code location
2. **Read by lines** (mandatory): Get exact content around target area  
3. **Create patch**: Use exact content to build the patch for **ONE file ONLY**
4. **Apply patch**: Submit the patch
5. **Verify with get_file_content_by_lines** (mandatory): Confirm changes applied correctly
6. **Compile**: Run `sbt_compile` to ensure no syntax errors
7. **Repeat** for next file (if needed)

#### Multiple File Changes (Sequential Only):
**NEVER modify multiple files in one patch. Instead:**
1. Complete entire workflow for File 1:
   - Read by lines → Patch → Verify → Compile
2. Only then proceed to File 2:
   - Read by lines → Patch → Verify → Compile  
3. Continue sequentially for each file

#### Error Handling:
- If patch fails, read the error message and error code
- Use `get_file_content_by_lines` to re-examine the current file state
- Create a corrected patch with the actual current content
- **Always verify** the corrected patch with `get_file_content_by_lines`

### 🔍 VERIFICATION WORKFLOW - MANDATORY AFTER EACH PATCH

**After every successful patch application, you MUST verify:**

#### Step 1: Immediate Post-Patch Verification
```json
{
  "function": "get_file_content_by_lines",
  "params": {
    "workspace_name": "my-project", 
    "file_path": "src/main/scala/ModifiedFile.scala",
    "start_line": 1,
    "end_line": 100
  }
}
```

#### Step 2: Check Modified Content
**Verify that:**
- [ ] Your changes are present and correct
- [ ] No unexpected modifications occurred
- [ ] File structure remains intact
- [ ] Line numbers align with your expectations

#### Step 3: Compilation Check
```json
{
  "function": "sbt_compile",
  "params": {
    "workspace_name": "my-project",
    "timeout": 60
  }
}
```

#### Step 4: Handle Verification Results
- **✅ If verification passes**: Proceed to next file (if needed)
- **❌ If verification fails**: 
  1. Use `get_file_content_by_lines` to examine current state
  2. Create corrective patch with exact current content
  3. Apply corrective patch
  4. **Repeat verification workflow**

### 🔍 GET FILE CONTENT BY LINES - Usage Patterns

#### Pattern 1: Read Entire Small File
```json
{
  "function": "get_file_content_by_lines",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/Utils.scala",
    "start_line": 1,
    "end_line": 100
  }
}
```

#### Pattern 2: Read Around Target Area
```json
{
  "function": "get_file_content_by_lines",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/LargeFile.scala",
    "start_line": 45,
    "end_line": 65
  }
}
```

#### Pattern 3: Read From Search Results
```json
// First, search to find location
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "def targetFunction",
    "limit": 5
  }
}

// Then read around that location (assuming function found at line 23)
{
  "function": "get_file_content_by_lines", 
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/Service.scala",
    "start_line": 18,
    "end_line": 35
  }
}
```

### ⚠️ PATCH VALIDATION

**Before applying any patch, ensure:**
- [ ] You called `get_file_content_by_lines` to get current file state
- [ ] **ONLY ONE file is being modified**
- [ ] **ONLY ONE location within that file is being changed**
- [ ] File headers are correct (`--- a/path` and `+++ b/path`)
- [ ] Hunk header mathematics are accurate (`@@ -old_start,old_count +new_start,new_count @@`)
- [ ] Context lines match exactly what's in the file
- [ ] Line prefixes are valid (space, `+`, `-`, `\`)
- [ ] Only one logical change per patch

**After applying any patch, ensure:**
- [ ] You called `get_file_content_by_lines` to verify the result
- [ ] Changes are present and correct
- [ ] No unintended side effects occurred
- [ ] File compiles successfully (`sbt_compile`)

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

### 3. File Operations (Use Patches When Possible)

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

#### Update Existing File (Consider using patches instead)
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

### 4. SBT Operations

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

### 5. Git Operations

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

### 6. Search Operations

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

### 7. Bash Session Management

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

2. **Create basic structure using patches** - `apply_patch`
   ```json
   {
     "workspace_name": "new-project",
     "patch": "--- /dev/null\n+++ b/build.sbt\n@@ -0,0 +1,10 @@\n+ThisBuild / version := \"0.1.0-SNAPSHOT\"\n+ThisBuild / scalaVersion := \"3.3.0\"\n+\n+lazy val root = (project in file(\".\"))\n+  .settings(\n+    name := \"new-project\",\n+    libraryDependencies ++= Seq(\n+      \"org.scalatest\" %% \"scalatest\" % \"3.2.15\" % Test\n+    )\n+  )\n\n--- /dev/null\n+++ b/src/main/scala/Main.scala\n@@ -0,0 +1,3 @@\n+object Main extends App {\n+  println(\"Hello, New Project!\")\n+}"
   }
   ```

3. **Compile to verify setup** - `sbt_compile`
   ```json
   {"workspace_name": "new-project"}
   ```

### 2. Development Workflow (Patch-Centric)
1. **Make code changes using patches** - `apply_patch`
2. **Check for patch errors** - Always verify `patch_applied: true` in response
3. **Compile to check for errors** - `sbt_compile`
4. **Run tests** - `sbt_test`
5. **If tests pass, commit changes** - `git_add` then `git_commit`

### 3. Code Exploration Workflow
1. **Get workspace structure** - `get_workspace_tree`
2. **Search for patterns of interest** - `search_files`
3. **Read relevant files** - `get_file_content`
4. **Apply changes with patches** - `apply_patch`

## Error Handling

### Patch Error Handling Pattern
```json
// Send patch
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "YOUR_PATCH_CONTENT"
  }
}

// Check response
{
  "status": "success|error",
  "data": {
    "patch_applied": true|false,
    "error_code": "ERROR_CODE_IF_FAILED", 
    "error_message": "Detailed message with line numbers"
  }
}
```

### General Error Handling
Always check for errors in responses:
- If response contains `"error"` key: `{"error": "compilation failed: ..."}`
- If successful: `{"success": true, "output": "operation output"}`

## Tips for LLMs

1. **🔥 PREFER PATCHES OVER INDIVIDUAL FILE OPERATIONS** - Especially for multi-file changes
2. **Always verify patch syntax** before sending - check headers, hunk format, line prefixes
3. **Use descriptive commit messages** when using Git operations
4. **Compile frequently** during development to catch errors early
5. **Handle patch errors gracefully** - check error codes and fix syntax issues
6. **Clean up bash sessions** when no longer needed to free resources
7. **Search before modifying** to understand existing code structure
8. **Use timeouts appropriately** - longer for compilation/tests, shorter for simple commands
9. **Check file tree structure** before creating files to ensure proper directory structure
10. **Group related changes** in single patches when possible

## Common Patterns

### Adding a New Feature (Patch-Based)
1. Search existing code to understand patterns
2. Create comprehensive patch with all necessary changes
3. Apply patch and check for syntax errors
4. Compile and test
5. Commit changes

### Debugging Issues
1. Check compilation errors via `sbt_compile`
2. Run specific tests via `sbt_test`
3. Use bash sessions for advanced debugging
4. Apply fixes via patches

### Refactoring Code (Patch-Preferred)
1. Use search to find all usages
2. Create comprehensive patch for multi-file changes
3. Verify patch syntax before applying
4. Compile to verify correctness
5. Run full test suite
6. Commit with descriptive message

## 🛠️ SYSTEMATIC DEVELOPMENT WORKFLOWS

### Planning → Implementation → Validation → Bug Fixing

This section provides step-by-step workflows for common development tasks, emphasizing the patch-first approach and systematic error handling.

### 🔍 **Phase 1: Planning and Analysis**

#### 1.1 Understand the Workspace
```json
// Step 1: Get workspace structure
{
  "function": "get_workspace_tree",
  "params": {"workspace_name": "my-project"}
}

// Step 2: Search for relevant existing code
{
  "function": "search_files", 
  "params": {
    "workspace_name": "my-project",
    "query": "relevant_pattern_or_keyword",
    "limit": 10
  }
}

// Step 3: Read key files to understand structure
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "my-project", 
    "file_path": "build.sbt"
  }
}
```

#### 1.2 Plan Your Changes
Before implementing, always:
- **Identify all files that need modification**
- **Determine dependencies and imports needed**
- **Plan the order of changes** (dependencies first, then implementations)
- **Consider test files** that will be needed

### 📝 **Phase 2: File Creation and Implementation**

#### 2.1 Create New Project Structure (Using Patches)
**For new projects or major additions:**

```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- /dev/null\n+++ b/build.sbt\n@@ -0,0 +1,12 @@\n+ThisBuild / version := \"0.1.0-SNAPSHOT\"\n+ThisBuild / scalaVersion := \"3.3.0\"\n+\n+lazy val root = (project in file(\".\"))\n+  .settings(\n+    name := \"my-project\",\n+    libraryDependencies ++= Seq(\n+      \"org.typelevel\" %% \"cats-core\" % \"2.9.0\",\n+      \"org.scalatest\" %% \"scalatest\" % \"3.2.15\" % Test,\n+      \"org.scalamock\" %% \"scalamock\" % \"5.2.0\" % Test\n+    )\n+  )\n\n--- /dev/null\n+++ b/src/main/scala/Main.scala\n@@ -0,0 +1,7 @@\n+object Main extends App {\n+  println(\"Starting application...\")\n+  \n+  // TODO: Implement main logic\n+  val result = processData(\"input\")\n+  println(s\"Result: $result\")\n+}\n\n--- /dev/null\n+++ b/src/main/scala/DataProcessor.scala\n@@ -0,0 +1,8 @@\n+object DataProcessor {\n+  def processData(input: String): String = {\n+    // TODO: Implement processing logic\n+    input.toUpperCase\n+  }\n+  \n+  // TODO: Add more processing methods\n+}"
  }
}
```

#### 2.2 Add Implementation Logic (Iterative Patches)
**Implement functionality step by step:**

```json
{
  "function": "apply_patch", 
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/DataProcessor.scala\n+++ b/src/main/scala/DataProcessor.scala\n@@ -1,8 +1,15 @@\n object DataProcessor {\n   def processData(input: String): String = {\n-    // TODO: Implement processing logic\n-    input.toUpperCase\n+    if (input.isEmpty) {\n+      throw new IllegalArgumentException(\"Input cannot be empty\")\n+    }\n+    \n+    val cleaned = cleanInput(input)\n+    val processed = transformData(cleaned)\n+    processed\n   }\n   \n-  // TODO: Add more processing methods\n+  private def cleanInput(input: String): String = input.trim.toLowerCase\n+  \n+  private def transformData(input: String): String = {\n+    input.split(\" \").map(_.capitalize).mkString(\" \")\n+  }\n }"
  }
}
```

#### 2.3 Update Main Class to Use New Implementation
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project", 
    "patch": "--- a/src/main/scala/Main.scala\n+++ b/src/main/scala/Main.scala\n@@ -1,7 +1,8 @@\n object Main extends App {\n   println(\"Starting application...\")\n   \n-  // TODO: Implement main logic\n-  val result = processData(\"input\")\n+  import DataProcessor._\n+  \n+  val result = processData(\"hello world scala\")\n   println(s\"Result: $result\")\n }"
  }
}
```

### ⚙️ **Phase 3: Compilation and Initial Validation**

#### 3.1 First Compilation Check
```json
{
  "function": "sbt_compile",
  "params": {
    "workspace_name": "my-project",
    "timeout": 60
  }
}
```

**Expected Response Patterns:**
- ✅ **Success**: `{"success": true, "output": "compilation successful"}`
- ❌ **Failure**: `{"success": false, "output": "compilation errors..."}`

#### 3.2 Handle Compilation Errors (Systematic Approach)

**Common Error Types and Solutions:**

**A) Import/Dependency Errors**
```bash
# Error: "object DataProcessor is not a member of package"
# Solution: Fix import or package declaration
```

```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/DataProcessor.scala\n+++ b/src/main/scala/DataProcessor.scala\n@@ -1,4 +1,6 @@\n+package com.example\n+\n object DataProcessor {\n   def processData(input: String): String = {"
  }
}
```

**B) Type Mismatch Errors**
```bash
# Error: "type mismatch; found: Unit, required: String"
# Solution: Fix return types
```

```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/DataProcessor.scala\n+++ b/src/main/scala/DataProcessor.scala\n@@ -10,6 +10,7 @@\n   private def transformData(input: String): String = {\n     input.split(\" \").map(_.capitalize).mkString(\" \")\n+    // Fixed: removed implicit Unit return\n   }"
  }
}
```

#### 3.3 Run Application After Successful Compilation
```json
{
  "function": "sbt_run",
  "params": {
    "workspace_name": "my-project",
    "main_class": "Main",
    "timeout": 30
  }
}
```

### 🧪 **Phase 4: Testing Implementation**

#### 4.1 Create Comprehensive Tests
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- /dev/null\n+++ b/src/test/scala/DataProcessorTest.scala\n@@ -0,0 +1,25 @@\n+import org.scalatest.funsuite.AnyFunSuite\n+import org.scalatest.matchers.should.Matchers\n+import DataProcessor._\n+\n+class DataProcessorTest extends AnyFunSuite with Matchers {\n+  \n+  test(\"processData should handle normal input\") {\n+    val result = processData(\"hello world\")\n+    result shouldBe \"Hello World\"\n+  }\n+  \n+  test(\"processData should handle single word\") {\n+    val result = processData(\"scala\")\n+    result shouldBe \"Scala\"\n+  }\n+  \n+  test(\"processData should handle whitespace\") {\n+    val result = processData(\"  hello   world  \")\n+    result shouldBe \"Hello World\"\n+  }\n+  \n+  test(\"processData should throw exception for empty input\") {\n+    assertThrows[IllegalArgumentException] {\n+      processData(\"\")\n+    }\n+  }\n+}"
  }
}
```

#### 4.2 Run Tests
```json
{
  "function": "sbt_test",
  "params": {
    "workspace_name": "my-project",
    "timeout": 60
  }
}
```

### 🐛 **Phase 5: Bug Fixing and Refinement**

#### 5.1 Systematic Bug Investigation

**When tests fail or compilation errors occur:**

1. **Analyze the Error Message**
   ```bash
   # Example error: "java.lang.IllegalArgumentException: Input cannot be empty"
   # Location: DataProcessorTest.scala:23
   # Cause: Expected exception not thrown
   ```

2. **Search for Related Code**
   ```json
   {
     "function": "search_files",
     "params": {
       "workspace_name": "my-project",
       "query": "IllegalArgumentException",
       "limit": 5
     }
   }
   ```

3. **Read the Failing Code**
   ```json
   {
     "function": "get_file_content", 
     "params": {
       "workspace_name": "my-project",
       "file_path": "src/main/scala/DataProcessor.scala"
     }
   }
   ```

#### 5.2 Apply Bug Fixes (Using Patches)

**Example: Fix empty string handling**
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/DataProcessor.scala\n+++ b/src/main/scala/DataProcessor.scala\n@@ -1,8 +1,8 @@\n object DataProcessor {\n   def processData(input: String): String = {\n-    if (input.isEmpty) {\n+    if (input == null || input.trim.isEmpty) {\n       throw new IllegalArgumentException(\"Input cannot be empty\")\n     }\n     \n     val cleaned = cleanInput(input)\n     val processed = transformData(cleaned)"
  }
}
```

#### 5.3 Iterative Testing and Refinement

**The Fix-Test-Verify Loop:**

1. **Apply fix via patch**
2. **Compile to check syntax**
   ```json
   {"function": "sbt_compile", "params": {"workspace_name": "my-project"}}
   ```
3. **Run specific failing test**
   ```json
   {
     "function": "sbt_test",
     "params": {
       "workspace_name": "my-project", 
       "test_name": "DataProcessorTest",
       "timeout": 30
     }
   }
   ```
4. **If test passes, run full test suite**
   ```json
   {"function": "sbt_test", "params": {"workspace_name": "my-project"}}
   ```

### 🔄 **Phase 6: Final Validation and Cleanup**

#### 6.1 Complete Validation Checklist
- ✅ All files compile without errors
- ✅ All tests pass
- ✅ Application runs successfully
- ✅ Code follows Scala best practices
- ✅ Dependencies are properly declared

#### 6.2 Git Workflow Integration
```json
// Check current status
{
  "function": "git_status",
  "params": {"workspace_name": "my-project"}
}

// Add all changes
{
  "function": "git_add", 
  "params": {"workspace_name": "my-project"}
}

// Commit with descriptive message
{
  "function": "git_commit",
  "params": {
    "workspace_name": "my-project",
    "message": "Implement DataProcessor with input validation and comprehensive tests",
    "author_name": "AI Assistant",
    "author_email": "ai@assistant.com"
  }
}
```

### 🚨 **Emergency Debugging Workflow**

**When Things Go Wrong:**

1. **Check Compilation First**
   ```json
   {"function": "sbt_compile", "params": {"workspace_name": "my-project"}}
   ```

2. **If Compilation Fails, Use Bash Session for Detailed Investigation**
   ```json
   {
     "function": "create_bash_session",
     "params": {"workspace_name": "my-project"}
   }
   
   {
     "function": "execute_bash_command",
     "params": {
       "session_id": "session_id_from_create",
       "command": "find . -name '*.scala' -exec grep -l 'problematic_pattern' {} \\;",
       "timeout": 10
     }
   }
   ```

3. **Clean and Rebuild**
   ```json
   {"function": "sbt_clean", "params": {"workspace_name": "my-project"}}
   {"function": "sbt_compile", "params": {"workspace_name": "my-project"}}
   ```

4. **Use Search to Find Examples**
   ```json
   {
     "function": "search_files",
     "params": {
       "workspace_name": "my-project",
       "query": "working_pattern_similar_to_broken_code",
       "limit": 5
     }
   }
   ```

### 📋 **Development Workflow Checklist for LLMs**

**Before Starting:**
- [ ] Understand the requirements
- [ ] Check workspace structure
- [ ] Search for existing similar implementations
- [ ] Plan file modifications and dependencies

**During Implementation:**
- [ ] Use patches for all file modifications
- [ ] Validate patch syntax before applying
- [ ] Check `patch_applied: true` in responses
- [ ] Compile after each significant change
- [ ] Handle compilation errors immediately

**Testing Phase:**
- [ ] Create comprehensive test cases
- [ ] Test normal cases, edge cases, and error conditions
- [ ] Run tests frequently during development
- [ ] Fix failing tests immediately

**Final Validation:**
- [ ] Full compilation passes
- [ ] All tests pass
- [ ] Application runs successfully
- [ ] Code is clean and well-structured
- [ ] Changes are committed to Git

**Error Recovery:**
- [ ] Read error messages carefully
- [ ] Search codebase for similar patterns
- [ ] Use bash sessions for complex debugging
- [ ] Apply targeted fixes via patches
- [ ] Verify fixes with immediate testing

## ⚠️ CRITICAL REMINDERS FOR LLMs

1. **PATCHES ARE THE PRIMARY FILE MODIFICATION METHOD** - Use them for most changes
2. **ALWAYS CHECK PATCH SYNTAX** - Headers, hunk format, line prefixes must be correct
3. **HANDLE PATCH ERRORS** - Check `patch_applied` field and `error_code` in responses
4. **USE ATOMIC CHANGES** - Group related modifications in single patches
5. **VALIDATE WITH COMPILATION** - Always compile after significant changes 