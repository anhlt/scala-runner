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

### 🔍 SEARCH-FIRST PATCH WORKFLOW (CRITICAL FOR SUCCESS)

**⚠️ NEVER create patches blindly! Always search first to get exact context.**

#### Step 1: Search for Target Code
Before creating any patch, search for the exact code you want to modify:

```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "def processData",
    "limit": 10
  }
}
```

**Response Analysis:**
```json
{
  "data": {
    "results": [
      {
        "file": "src/main/scala/DataProcessor.scala",
        "line": 5,
        "content": "  def processData(input: String): String = {"
      }
    ]
  }
}
```

#### Step 2: Read the Exact File Content
Get the complete context around your target:

```json
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/DataProcessor.scala"
  }
}
```

**Response Analysis:**
```json
{
  "content": "object DataProcessor {\n  val config = \"default\"\n  \n  def processData(input: String): String = {\n    input.toUpperCase\n  }\n  \n  def helper(): Unit = println(\"help\")\n}"
}
```

#### Step 3: Create Accurate Patch with Exact Context
Now use the **exact content** from the file to create your patch:

```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/DataProcessor.scala\n+++ b/src/main/scala/DataProcessor.scala\n@@ -3,7 +3,10 @@\n   val config = \"default\"\n   \n   def processData(input: String): String = {\n-    input.toUpperCase\n+    if (input.isEmpty) throw new IllegalArgumentException(\"Empty input\")\n+    val cleaned = input.trim.toLowerCase\n+    val processed = cleaned.split(\" \").map(_.capitalize).mkString(\" \")\n+    processed\n   }\n   \n   def helper(): Unit = println(\"help\")"
  }
}
```

### Apply Patch Operation
**Function:** `apply_patch`
```json
{
  "workspace_name": "my-scala-project",
  "patch": "PATCH_CONTENT_HERE"
}
```

### 📋 SEARCH-FIRST PATCH EXAMPLES

#### 1. Simple Line Modification (Search-First Approach)

**Step 1: Search for target**
```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "println(\"Hello, World!\")",
    "limit": 5
  }
}
```

**Step 2: Read file for context**
```json
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/Main.scala"
  }
}
```

**Step 3: Create patch with exact context**
```json
{
  "workspace_name": "my-project",
  "patch": "--- a/src/main/scala/Main.scala\n+++ b/src/main/scala/Main.scala\n@@ -1,3 +1,3 @@\n object Main {\n-  println(\"Hello, World!\")\n+  println(\"Hello, Scala!\")\n }"
}
```

#### 2. Add New Methods (Search-First Approach)

**Step 1: Search for insertion point**
```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "object Utils",
    "limit": 5
  }
}
```

**Step 2: Read file to understand structure**
```json
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/Utils.scala"
  }
}
```

**Discovered content:**
```scala
object Utils {
  def existingMethod(): String = "existing"
  
  // End of object
}
```

**Step 3: Create patch at correct position**
```json
{
  "workspace_name": "my-project",
  "patch": "--- a/src/main/scala/Utils.scala\n+++ b/src/main/scala/Utils.scala\n@@ -2,4 +2,10 @@\n object Utils {\n   def existingMethod(): String = \"existing\"\n   \n+  def newUtilityMethod(input: String): String = {\n+    input.trim.toLowerCase\n+  }\n+\n+  def anotherMethod(): Unit = {\n+    println(\"Added via patch\")\n+  }\n+\n   // End of object\n }"
}
```

#### 3. Modify Existing Function (Search-First Approach)

**Step 1: Search for function signature**
```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "def calculateTotal",
    "limit": 5
  }
}
```

**Step 2: Read surrounding context**
```json
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/Calculator.scala"
  }
}
```

**Discovered content:**
```scala
class Calculator {
  private val taxRate = 0.08
  
  def calculateTotal(amount: Double): Double = {
    amount + (amount * taxRate)
  }
  
  def formatResult(value: Double): String = f"$value%.2f"
}
```

**Step 3: Create patch with exact context**
```json
{
  "workspace_name": "my-project",
  "patch": "--- a/src/main/scala/Calculator.scala\n+++ b/src/main/scala/Calculator.scala\n@@ -2,7 +2,11 @@\n class Calculator {\n   private val taxRate = 0.08\n   \n   def calculateTotal(amount: Double): Double = {\n-    amount + (amount * taxRate)\n+    if (amount < 0) {\n+      throw new IllegalArgumentException(\"Amount cannot be negative\")\n+    }\n+    val tax = amount * taxRate\n+    amount + tax\n   }\n   \n   def formatResult(value: Double): String = f\"$value%.2f\""
}
```

#### 4. Multi-File Refactoring (Search-First for Each File)

**Step 1: Search in main file**
```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "def factorial",
    "limit": 10
  }
}
```

**Step 2: Read main file**
```json
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "my-project",
    "file_path": "src/main/scala/Main.scala"
  }
}
```

**Step 3: Search for import patterns**
```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "import",
    "limit": 10
  }
}
```

**Step 4: Create multi-file patch with exact context**
```json
{
  "workspace_name": "my-project",
  "patch": "--- a/src/main/scala/Main.scala\n+++ b/src/main/scala/Main.scala\n@@ -1,12 +1,5 @@\n object Main extends App {\n   println(\"Hello, Updated Scala!\")\n-  \n-  def factorial(n: Int): Long = {\n-    if (n <= 1) 1L\n-    else n * factorial(n - 1)\n-  }\n-  \n-  def fibonacci(n: Int): Int = {\n-    if (n <= 1) n\n-    else fibonacci(n - 1) + fibonacci(n - 2)\n-  }\n+\n+  import MathUtils._\n   \n   println(s\"Factorial(5) = ${factorial(5)}\")\n\n--- /dev/null\n+++ b/src/main/scala/MathUtils.scala\n@@ -0,0 +1,11 @@\n+object MathUtils {\n+  def factorial(n: Int): Long = {\n+    if (n <= 1) 1L\n+    else n * factorial(n - 1)\n+  }\n+  \n+  def fibonacci(n: Int): Int = {\n+    if (n <= 1) n\n+    else fibonacci(n - 1) + fibonacci(n - 2)\n+  }\n+}"
}
```

#### 5. Add Dependencies (Search build.sbt First)

**Step 1: Search for dependency section**
```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "libraryDependencies",
    "limit": 5
  }
}
```

**Step 2: Read build.sbt content**
```json
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "my-project",
    "file_path": "build.sbt"
  }
}
```

**Discovered content:**
```scala
ThisBuild / version := "0.1.0-SNAPSHOT"
ThisBuild / scalaVersion := "3.3.0"

lazy val root = (project in file("."))
  .settings(
    name := "my-project",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-core" % "2.9.0",
      "org.scalatest" %% "scalatest" % "3.2.15" % Test
    )
  )
```

**Step 3: Create patch with exact context**
```json
{
  "workspace_name": "my-project",
  "patch": "--- a/build.sbt\n+++ b/build.sbt\n@@ -5,8 +5,10 @@\n lazy val root = (project in file(\".\"))\n   .settings(\n     name := \"my-project\",\n     libraryDependencies ++= Seq(\n       \"org.typelevel\" %% \"cats-core\" % \"2.9.0\",\n-      \"org.scalatest\" %% \"scalatest\" % \"3.2.15\" % Test\n+      \"org.scalatest\" %% \"scalatest\" % \"3.2.15\" % Test,\n+      \"org.scalamock\" %% \"scalamock\" % \"5.2.0\" % Test,\n+      \"io.circe\" %% \"circe-core\" % \"0.14.5\"\n     )\n   )"
}
```

### 🎯 SEARCH-FIRST BEST PRACTICES

#### 1. Multiple Search Strategies
Use different search terms to find your target:

```json
// Search for function name
{"function": "search_files", "params": {"workspace_name": "project", "query": "def processUser"}}

// Search for class name  
{"function": "search_files", "params": {"workspace_name": "project", "query": "class UserService"}}

// Search for specific text
{"function": "search_files", "params": {"workspace_name": "project", "query": "println(\"Starting\")"}}

// Search for patterns
{"function": "search_files", "params": {"workspace_name": "project", "query": "extends App"}}
```

#### 2. Verify Context Before Patching
Always read the file after searching:

```json
// Found target in search results
{
  "file": "src/main/scala/UserService.scala",
  "line": 15,
  "content": "  def updateUser(id: String, data: UserData): Future[User] = {"
}

// Read the file to get full context
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "project",
    "file_path": "src/main/scala/UserService.scala"
  }
}
```

#### 3. Use Exact Content in Patches
Copy the **exact text** from the file content into your patch:

```diff
# ✅ CORRECT - Uses exact content from file
--- a/src/main/scala/UserService.scala
+++ b/src/main/scala/UserService.scala
@@ -14,6 +14,9 @@
   
   def updateUser(id: String, data: UserData): Future[User] = {
+    if (id.isEmpty) {
+      throw new IllegalArgumentException("User ID cannot be empty")
+    }
     repository.update(id, data)
   }

# ❌ INCORRECT - Guessed content that doesn't match file
--- a/src/main/scala/UserService.scala
+++ b/src/main/scala/UserService.scala
@@ -1,3 +1,6 @@
 def updateUser(id: String, data: UserData): Future[User] = {
+  if (id.isEmpty) {
+    throw new IllegalArgumentException("User ID cannot be empty")
+  }
   repository.update(id, data)
 }
```

#### 4. Search for Import Locations
When adding imports, search for existing import statements:

```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "import",
    "limit": 10
  }
}
```

#### 5. Search for Package Declarations
When adding package statements, search for existing ones:

```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project", 
    "query": "package",
    "limit": 10
  }
}
```

### 🚨 COMMON SEARCH-FIRST PATTERNS

#### Pattern 1: Adding Method to Existing Class
```bash
1. Search: "class ClassName" or "object ObjectName"
2. Read: Get full file content
3. Identify: Exact insertion point
4. Patch: Add method with proper context
```

#### Pattern 2: Modifying Function Implementation
```bash
1. Search: "def functionName" 
2. Read: Get surrounding code
3. Identify: Function body boundaries
4. Patch: Replace implementation with exact context
```

#### Pattern 3: Adding Dependencies
```bash
1. Search: "libraryDependencies" in build.sbt
2. Read: Get current dependency list
3. Identify: Exact format and indentation
4. Patch: Add new dependencies maintaining format
```

#### Pattern 4: Import Management
```bash
1. Search: "import" statements in target file
2. Read: Understand existing import structure
3. Identify: Correct location for new imports
4. Patch: Add imports in proper order
```

### ⚠️ PATCH CREATION FAILURES TO AVOID

#### ❌ Creating Patches Without Context
```diff
# This will likely fail - no context verification
--- a/SomeFile.scala
+++ b/SomeFile.scala
@@ -1,1 +1,2 @@
+new line
 existing line
```

#### ✅ Search-First Approach
```json
// Step 1: Search first
{"function": "search_files", "params": {"query": "existing line"}}

// Step 2: Read file  
{"function": "get_file_content", "params": {"file_path": "SomeFile.scala"}}

// Step 3: Create patch with exact context
{
  "patch": "--- a/SomeFile.scala\n+++ b/SomeFile.scala\n@@ -5,7 +5,8 @@\n   // surrounding context\n   existing line\n+  new line\n   // more context"
}
```

## 📝 PATCH TEMPLATES - ONE CHANGE AT A TIME

### 🚨 CRITICAL RULE: PATCH ONE LOCATION AT A TIME

**⚠️ NEVER create patches with multiple hunks or changes to different parts of the same file in one patch. Always make ONE atomic change per patch.**

### Template Categories

#### 🔧 **Template 1: Add Single Line**
```diff
--- a/path/to/file.scala
+++ b/path/to/file.scala
@@ -LINE_NUMBER,CONTEXT_SIZE +LINE_NUMBER,CONTEXT_SIZE+1 @@
 context_line_before
 existing_line
+NEW_LINE_TO_ADD
 context_line_after
```

**Example Usage:**
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/Utils.scala\n+++ b/src/main/scala/Utils.scala\n@@ -3,5 +3,6 @@\n object Utils {\n   def existingMethod(): String = \"existing\"\n   \n+  def newMethod(): String = \"new\"\n+\n   // End of object\n }"
  }
}
```

#### 🔧 **Template 2: Replace Single Line**
```diff
--- a/path/to/file.scala
+++ b/path/to/file.scala
@@ -LINE_NUMBER,CONTEXT_SIZE +LINE_NUMBER,CONTEXT_SIZE @@
 context_line_before
-OLD_LINE_TO_REPLACE
+NEW_LINE_REPLACEMENT
 context_line_after
```

**Example Usage:**
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/Main.scala\n+++ b/src/main/scala/Main.scala\n@@ -2,4 +2,4 @@\n object Main {\n-  println(\"Hello, World!\")\n+  println(\"Hello, Scala!\")\n }"
  }
}
```

#### 🔧 **Template 3: Remove Single Line**
```diff
--- a/path/to/file.scala
+++ b/path/to/file.scala
@@ -LINE_NUMBER,CONTEXT_SIZE +LINE_NUMBER,CONTEXT_SIZE-1 @@
 context_line_before
-LINE_TO_REMOVE
 context_line_after
```

**Example Usage:**
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/Debug.scala\n+++ b/src/main/scala/Debug.scala\n@@ -5,7 +5,6 @@\n   def processData(input: String): String = {\n     val cleaned = input.trim\n-    println(s\"Debug: processing $cleaned\")  // Remove debug line\n     cleaned.toUpperCase\n   }"
  }
}
```

#### 🔧 **Template 4: Add Multiple Lines (Single Block)**
```diff
--- a/path/to/file.scala
+++ b/path/to/file.scala
@@ -LINE_NUMBER,CONTEXT_SIZE +LINE_NUMBER,CONTEXT_SIZE+LINES_ADDED @@
 context_line_before
 existing_line
+FIRST_NEW_LINE
+SECOND_NEW_LINE
+THIRD_NEW_LINE
 context_line_after
```

**Example Usage:**
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/Validator.scala\n+++ b/src/main/scala/Validator.scala\n@@ -4,6 +4,9 @@\n   def validate(input: String): Boolean = {\n     if (input == null) return false\n     \n+    if (input.trim.isEmpty) {\n+      throw new IllegalArgumentException(\"Input cannot be empty\")\n+    }\n+    \n     input.length > 0\n   }"
  }
}
```

#### 🔧 **Template 5: Replace Function Body**
```diff
--- a/path/to/file.scala
+++ b/path/to/file.scala
@@ -START_LINE,OLD_COUNT +START_LINE,NEW_COUNT @@
 context_before_function
 def functionName(params): ReturnType = {
-  OLD_FUNCTION_BODY_LINE_1
-  OLD_FUNCTION_BODY_LINE_2
+  NEW_FUNCTION_BODY_LINE_1
+  NEW_FUNCTION_BODY_LINE_2
+  NEW_FUNCTION_BODY_LINE_3
 }
 context_after_function
```

**Example Usage:**
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/Calculator.scala\n+++ b/src/main/scala/Calculator.scala\n@@ -5,8 +5,11 @@\n   \n   def calculate(x: Int, y: Int): Int = {\n-    x + y\n+    if (x < 0 || y < 0) {\n+      throw new IllegalArgumentException(\"Negative numbers not allowed\")\n+    }\n+    val result = x + y\n+    result\n   }\n   \n   def format(value: Int): String = value.toString"
  }
}
```

#### 🔧 **Template 6: Add Import Statement**
```diff
--- a/path/to/file.scala
+++ b/path/to/file.scala
@@ -IMPORT_LINE,CONTEXT_SIZE +IMPORT_LINE,CONTEXT_SIZE+1 @@
 existing_import_or_package
+import new.package.ClassName
 
 class_or_object_definition
```

**Example Usage:**
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- a/src/main/scala/Service.scala\n+++ b/src/main/scala/Service.scala\n@@ -1,4 +1,5 @@\n package com.example\n \n+import scala.concurrent.Future\n import scala.util.Try\n \n class Service {"
  }
}
```

#### 🔧 **Template 7: Create New File**
```diff
--- /dev/null
+++ b/path/to/new/file.scala
@@ -0,0 +1,NUMBER_OF_LINES @@
+FIRST_LINE_OF_NEW_FILE
+SECOND_LINE_OF_NEW_FILE
+...
+LAST_LINE_OF_NEW_FILE
```

**Example Usage:**
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "--- /dev/null\n+++ b/src/main/scala/Helper.scala\n@@ -0,0 +1,8 @@\n+package com.example\n+\n+object Helper {\n+  def formatString(input: String): String = {\n+    input.trim.toLowerCase.capitalize\n+  }\n+}"
  }
}
```

### 🎯 **ATOMIC PATCH WORKFLOW**

#### Step 1: Identify Single Change
Before creating any patch, identify exactly **ONE** thing you want to change:
- ✅ Add one method
- ✅ Modify one function  
- ✅ Add one import
- ✅ Change one line
- ❌ Add method AND modify imports
- ❌ Change multiple functions
- ❌ Multiple unrelated changes

#### Step 2: Search for Exact Location
```json
{
  "function": "search_files",
  "params": {
    "workspace_name": "my-project",
    "query": "EXACT_CODE_YOU_WANT_TO_CHANGE",
    "limit": 5
  }
}
```

#### Step 3: Read File for Context
```json
{
  "function": "get_file_content",
  "params": {
    "workspace_name": "my-project",
    "file_path": "path/from/search/results"
  }
}
```

#### Step 4: Choose Appropriate Template
Select the template that matches your change type:
- Adding lines → Template 1 or 4
- Replacing lines → Template 2 or 5  
- Removing lines → Template 3
- New import → Template 6
- New file → Template 7

#### Step 5: Fill Template with Exact Content
```json
{
  "function": "apply_patch",
  "params": {
    "workspace_name": "my-project",
    "patch": "TEMPLATE_FILLED_WITH_EXACT_CONTENT"
  }
}
```

### 📋 **TEMPLATE SELECTION GUIDE**

| What you want to do | Template to use | Key markers |
|---------------------|-----------------|-------------|
| Add 1 line | Template 1 | `+1` in hunk header |
| Replace 1 line | Template 2 | Same count in hunk header |
| Remove 1 line | Template 3 | `-1` in hunk header |
| Add method/block | Template 4 | Multiple `+` lines |
| Rewrite function | Template 5 | Multiple `-` and `+` lines |
| Add import | Template 6 | Near top of file |
| Create new file | Template 7 | `/dev/null` source |

### 🚨 **MULTIPLE CHANGES WORKFLOW**

If you need to make multiple changes, **create separate patches for each change**:

#### ❌ WRONG - Multiple changes in one patch
```json
{
  "patch": "--- a/File.scala\n+++ b/File.scala\n@@ -1,5 +1,6 @@\n+import NewPackage\n class MyClass {\n   def method1(): String = {\n-    \"old\"\n+    \"new\"\n   }\n@@ -10,12 +11,15 @@\n   def method2(): Int = {\n+    if (condition) return 0\n     42\n   }"
}
```

#### ✅ CORRECT - Separate patches for each change
```json
// First patch: Add import
{
  "patch": "--- a/File.scala\n+++ b/File.scala\n@@ -1,3 +1,4 @@\n package com.example\n \n+import NewPackage\n class MyClass {"
}

// Second patch: Modify method1
{
  "patch": "--- a/File.scala\n+++ b/File.scala\n@@ -4,6 +4,6 @@\n class MyClass {\n   def method1(): String = {\n-    \"old\"\n+    \"new\"\n   }"
}

// Third patch: Add validation to method2
{
  "patch": "--- a/File.scala\n+++ b/File.scala\n@@ -8,5 +8,6 @@\n   \n   def method2(): Int = {\n+    if (condition) return 0\n     42\n   }"
}
```

### 🔧 **TEMPLATE DEBUGGING CHECKLIST**

Before applying any patch, verify:
- [ ] **File path is correct** (`--- a/` and `+++ b/` match actual file)
- [ ] **Hunk header math is correct** (line numbers and counts match content)
- [ ] **Context lines are exact** (copied exactly from file content)
- [ ] **Only ONE change** is being made
- [ ] **Line prefixes are valid** (space, `+`, `-`, `\` only)
- [ ] **No mixed line endings** (consistent `\n`)

### 💡 **TEMPLATE EXAMPLES WITH EXPLANATIONS**

#### Example 1: Add Method (Template 4)
**Search Result:** Found `object Utils` at line 3 in `Utils.scala`
**File Content:** 
```scala
package com.example

object Utils {
  def existing(): String = "test"
  
  // End of object
}
```

**Template Application:**
```json
{
  "patch": "--- a/src/main/scala/Utils.scala\n+++ b/src/main/scala/Utils.scala\n@@ -4,5 +4,9 @@\n object Utils {\n   def existing(): String = \"test\"\n   \n+  def newMethod(input: String): String = {\n+    input.toUpperCase\n+  }\n+\n   // End of object\n }"
}
```

**Explanation:**
- `@@ -4,5 +4,9 @@` means: starting at line 4, showing 5 old lines, replacing with 9 new lines
- Context before: `object Utils {` and `def existing(): String = "test"`  
- Context after: `// End of object`
- Change: Added 4 new lines (+4 in count)

#### Example 2: Replace Line (Template 2)
**Search Result:** Found `println("Hello")` at line 6 in `Main.scala`
**File Content:**
```scala
object Main {
  def main(args: Array[String]): Unit = {
    println("Hello")
    val x = 42
  }
}
```

**Template Application:**
```json
{
  "patch": "--- a/src/main/scala/Main.scala\n+++ b/src/main/scala/Main.scala\n@@ -2,5 +2,5 @@\n object Main {\n   def main(args: Array[String]): Unit = {\n-    println(\"Hello\")\n+    println(\"Hello, World!\")\n     val x = 42\n   }"
}
```

**Explanation:**
- `@@ -2,5 +2,5 @@` means: starting at line 2, 5 lines total, count stays the same
- One line removed (`-`), one line added (`+`)
- Context preserved before and after the change

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