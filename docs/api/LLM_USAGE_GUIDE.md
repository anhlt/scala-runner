# Scala Runner Tools - LLM Usage Guide

## Overview

The Scala Runner Tools enable LLMs to manage complete Scala development workflows through workspace management, file operations, Git version control, SBT build operations, search functionality, and bash session management.

**⚠️ PATCH OPERATIONS ARE THE PREFERRED METHOD FOR FILE MODIFICATIONS** - Use patches for multi-file changes, refactoring, and complex modifications instead of individual file operations.

## Core Concepts

### Workspaces
- **Workspace**: A project container with its own file system, Git repository, and SBT configuration
- **Isolation**: Each workspace is isolated from others, allowing multiple projects simultaneously
- **Persistence**: Workspaces persist across sessions until explicitly deleted

### Patch-First Approach
- **SEARCH/REPLACE Format**: All patches use SEARCH/REPLACE format with clear markers
- **Multi-file Operations**: Single patch can modify multiple files simultaneously
- **Atomic Changes**: Patches are applied atomically - either all changes succeed or none do
- **Error Validation**: Comprehensive syntax validation with specific error codes

## 🔥 PATCH API SYNTAX GUIDE

**Understanding SEARCH/REPLACE Patch Format:**

```
file_path.scala
<<<<<<< SEARCH
old content that needs to be replaced
=======
new content to replace the old content
>>>>>>> REPLACE
```

**Critical Patch Syntax Rules:**
1. **File Path is MANDATORY**: Every patch must start with the file path on its own line
2. **SEARCH Block**: Must contain the exact existing content to be replaced
3. **REPLACE Block**: Contains the new content that will replace the SEARCH content
4. **Exact Matching**: SEARCH content must match the file exactly (including whitespace and indentation)
5. **Markers Must Be Exact**: Use exactly `<<<<<<< SEARCH`, `=======`, and `>>>>>>> REPLACE`

**Example: Adding a new method**
```
src/main/scala/Calculator.scala
<<<<<<< SEARCH
  def subtract(a: Int, b: Int): Int = a - b
  
  def multiply(a: Int, b: Int): Int = a * b
}
=======
  def subtract(a: Int, b: Int): Int = a - b
  
  def multiply(a: Int, b: Int): Int = a * b
  
  def divide(a: Int, b: Int): Double = {
    require(b != 0, "Division by zero")
    a.toDouble / b.toDouble
  }
}
>>>>>>> REPLACE
```

**Example: Creating a new file**
```
src/main/scala/Utils.scala
<<<<<<< SEARCH
=======
object Utils {
  def formatMessage(msg: String): String = {
    val timestamp = java.time.LocalDateTime.now()
    s"[$timestamp] $msg"
  }
  
  def isValidEmail(email: String): Boolean = email.contains("@")
}
>>>>>>> REPLACE
```

**Example: Replacing specific content**
```
src/main/scala/Main.scala
<<<<<<< SEARCH
  println("Hello, World!")
=======
  println("Hello, Scala!")
  println("Welcome to the updated application!")
>>>>>>> REPLACE
```

## 🎯 ACCOMPLISHING USER REQUIREMENTS

### Setting Up New Scala Projects

**Goal**: Create a new Scala project with proper structure and dependencies

**Approach**:
1. **Create workspace** using `create_workspace`
2. **Set up project structure** using patches to create `build.sbt`, source directories, and initial files
3. **Verify setup** by compiling the project
4. **Initialize Git** if needed

**Key Functions**: `create_workspace`, `apply_patch`, `sbt_compile`, `git_add`, `git_commit`

### Implementing New Features

**Goal**: Add functionality to existing Scala code

**Approach**:
1. **Explore existing code** using `search_files` to understand current structure
2. **Read target files** using `get_file_content_by_lines` to understand exact content
3. **Apply changes atomically** using patches for modifications
4. **Verify changes** by reading files again and compiling
5. **Test implementation** using SBT test commands
6. **Commit working changes** to Git

**Key Functions**: `search_files`, `get_file_content_by_lines`, `apply_patch`, `sbt_compile`, `sbt_test`, `git_add`, `git_commit`

### Debugging and Fixing Issues

**Goal**: Identify and resolve compilation errors, test failures, or runtime issues

**Approach**:
1. **Identify problems** using `sbt_compile` or `sbt_test` to see error messages
2. **Investigate code** using `search_files` to find related code patterns
3. **Examine specific files** using `get_file_content_by_lines` around error locations
4. **Apply targeted fixes** using patches
5. **Verify fixes** by recompiling and retesting
6. **Use bash sessions** for complex debugging scenarios

**Key Functions**: `sbt_compile`, `sbt_test`, `search_files`, `get_file_content_by_lines`, `apply_patch`, `create_bash_session`, `execute_bash_command`

### Refactoring Existing Code

**Goal**: Improve code structure, extract methods, rename variables, or reorganize files

**Approach**:
1. **Map current structure** using `get_workspace_tree` and `search_files`
2. **Plan changes systematically** by reading all affected files
3. **Apply changes in logical order** using patches (dependencies first, then implementations)
4. **Validate each step** with compilation checks
5. **Run comprehensive tests** to ensure no regressions
6. **Document changes** in commit messages

**Key Functions**: `get_workspace_tree`, `search_files`, `get_file_content_by_lines`, `apply_patch`, `sbt_compile`, `sbt_test`

### Managing Dependencies and Build Configuration

**Goal**: Add libraries, update Scala versions, modify build settings

**Approach**:
1. **Read current build configuration** from `build.sbt`
2. **Research dependencies** using bash sessions if needed
3. **Update build files** using patches
4. **Reload and compile** to verify dependency resolution
5. **Update code** to use new dependencies
6. **Test integration** thoroughly

**Key Functions**: `get_file_content`, `apply_patch`, `sbt_compile`, `sbt_clean`, `create_bash_session`

### Working with Git History and Collaboration

**Goal**: Manage version control, review changes, prepare commits

**Approach**:
1. **Check current status** using `git_status` to see modified files
2. **Review changes** by reading files that have been modified
3. **Stage changes selectively** using `git_add` with specific files
4. **Create meaningful commits** using `git_commit` with descriptive messages
5. **Handle conflicts** if working with remote repositories

**Key Functions**: `git_status`, `git_add`, `git_commit`, `get_file_content_by_lines`

### Testing and Quality Assurance

**Goal**: Ensure code quality through comprehensive testing

**Approach**:
1. **Run existing tests** using `sbt_test` to establish baseline
2. **Add new test cases** using patches to create or modify test files
3. **Run specific tests** during development for faster feedback
4. **Handle test failures** by examining output and fixing issues
5. **Verify coverage** of critical functionality

**Key Functions**: `sbt_test`, `apply_patch`, `search_files`, `get_file_content_by_lines`

### Complex Analysis and Exploration

**Goal**: Understand large codebases, analyze patterns, extract insights

**Approach**:
1. **Get high-level overview** using `get_workspace_tree`
2. **Search for patterns** using `search_files` with relevant queries
3. **Use bash sessions** for complex analysis (grep, find, awk commands)
4. **Read key files** to understand implementation details
5. **Document findings** in comments or separate documentation files

**Key Functions**: `get_workspace_tree`, `search_files`, `create_bash_session`, `execute_bash_command`, `get_file_content`

## 🛠️ SYSTEMATIC APPROACH TO DEVELOPMENT

### Essential Development Workflow

**For Any Task:**
1. **Understand**: Explore workspace structure and search for relevant code
2. **Plan**: Identify what needs to change and in what order
3. **Read First**: Always get exact file content before making changes
4. **Change Atomically**: Use patches for modifications, one logical change at a time
5. **Verify Immediately**: Check changes were applied correctly
6. **Compile Often**: Catch syntax errors early
7. **Test Thoroughly**: Ensure functionality works as expected
8. **Commit Meaningfully**: Save working state with descriptive messages

### Best Practices for Success

**File Modifications:**
- Always read files with `get_file_content_by_lines` before creating patches
- Use exact content from file responses in patches
- Modify only one file in one location per patch
- Include sufficient context (3-5 lines before/after changes)
- Verify changes immediately after applying patches

**Error Handling:**
- Check compilation after every significant change
- Read error messages carefully and search for related code
- Use bash sessions for complex debugging scenarios
- Apply targeted fixes rather than broad changes

**Project Management:**
- Use descriptive workspace names
- Keep build files up to date
- Clean build artifacts when encountering issues
- Commit frequently with clear messages

**Performance:**
- Use appropriate timeouts for long-running operations
- Clean up bash sessions when finished
- Search efficiently with targeted queries
- Read only necessary file sections

## ⚠️ CRITICAL REMINDERS

1. **PATCHES ARE PRIMARY** - Use patches for most file modifications
2. **READ BEFORE WRITE** - Always get exact file content before creating patches
3. **VERIFY CHANGES** - Check that patches applied correctly
4. **COMPILE FREQUENTLY** - Catch errors early in development
5. **ONE CHANGE AT A TIME** - Make atomic, focused modifications
6. **HANDLE ERRORS GRACEFULLY** - Read error messages and fix systematically
7. **COMMIT WORKING STATE** - Save progress with meaningful commit messages

The key to success is understanding that these tools enable complete development workflows - from initial project setup through debugging and deployment. Focus on accomplishing user requirements systematically rather than just calling individual functions. 