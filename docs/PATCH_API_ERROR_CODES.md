# Patch API Error Codes Documentation

## Overview

The Patch API now includes comprehensive syntax validation that returns specific error codes when patches contain syntax errors. This provides clear feedback to users about what's wrong with their patch format.

## Error Response Format

When a patch has syntax errors, the API returns:

**HTTP Status:** `400 Bad Request`

**Response Structure:**
```json
{
  "status": "error",
  "error_code": "ERROR_CODE_NAME",
  "error_message": "Detailed error description with line numbers",
  "data": {
    "workspace_name": "workspace-name",
    "patch_applied": false,
    "error_code": "ERROR_CODE_NAME",
    "error_message": "Detailed error description",
    "results": {
      "modified_files": [],
      "total_files": 0,
      "successful_files": 0
    }
  }
}
```

## Error Codes

### `MISSING_FILE_HEADERS`

**Description:** Patch contains hunk headers (`@@`) but lacks proper file headers (`---` and `+++`).

**Example Invalid Patch:**
```diff
@@ -1,1 +1,1 @@
-old line
+new line
```

**Error Message:** `"Hunk header without file headers at line X"`

---

### `INVALID_HUNK_HEADER`

**Description:** Hunk header format is malformed and doesn't match the expected pattern `@@ -old_start,old_count +new_start,new_count @@`.

**Example Invalid Patch:**
```diff
--- a/test.txt
+++ b/test.txt
@@ invalid hunk @@
+some content
```

**Error Message:** `"Invalid hunk header format at line X: '@@ invalid hunk @@'"`

---

### `MISSING_OLD_FILE_HEADER`

**Description:** Patch contains a new file header (`+++`) without a corresponding old file header (`---`).

**Example Invalid Patch:**
```diff
+++ b/test.txt
@@ -1,1 +1,1 @@
+some content
```

**Error Message:** `"New file header without old file header at line X"`

---

### `INVALID_OLD_FILE_HEADER`

**Description:** Old file header (`---`) is malformed or empty.

**Example Invalid Patch:**
```diff
--- 
+++ b/test.txt
@@ -1,1 +1,1 @@
+some content
```

**Error Message:** `"Invalid old file header at line X: '---'"`

---

### `INVALID_NEW_FILE_HEADER`

**Description:** New file header (`+++`) is malformed or empty.

**Example Invalid Patch:**
```diff
--- a/test.txt
+++ 
@@ -1,1 +1,1 @@
+some content
```

**Error Message:** `"Invalid new file header at line X: '+++'"`

---

### `INVALID_LINE_PREFIX`

**Description:** Patch content lines have invalid prefixes. Valid prefixes are:
- ` ` (space) - Context line
- `+` - Added line  
- `-` - Removed line
- `\` - Special marker (e.g., "\ No newline at end of file")

**Example Invalid Patch:**
```diff
--- a/test.txt
+++ b/test.txt
@@ -1,1 +1,1 @@
 context line
*invalid prefix line
+added line
```

**Error Message:** `"Invalid line prefix '*' at line X: '*invalid prefix line'"`

---

## Valid Scenarios

### Empty Patches
Empty or whitespace-only patches are considered **valid** and return success with no changes:

```json
{
  "workspace_name": "workspace-name",
  "patch_applied": true,
  "results": {
    "modified_files": [],
    "total_files": 0,
    "successful_files": 0
  }
}
```

### Valid Patch Example
```diff
--- a/src/main/scala/Test.scala
+++ b/src/main/scala/Test.scala
@@ -1,3 +1,3 @@
 object Test {
-  val x = 1
+  val x = 2
 }
```

## Usage Examples

### REST API

**Request:**
```bash
curl -X PATCH http://localhost:8000/files \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_name": "my-workspace",
    "patch": "@@ -1,1 +1,1 @@\n-old\n+new"
  }'
```

**Response (Error):**
```json
{
  "status": "error",
  "error_code": "MISSING_FILE_HEADERS",
  "error_message": "Hunk header without file headers at line 1",
  "data": {
    "workspace_name": "my-workspace",
    "patch_applied": false,
    "error_code": "MISSING_FILE_HEADERS",
    "error_message": "Hunk header without file headers at line 1",
    "results": {
      "modified_files": [],
      "total_files": 0,
      "successful_files": 0
    }
  }
}
```

### Python SDK

```python
from scala_runner.workspace_manager import WorkspaceManager

workspace_manager = WorkspaceManager()

# Invalid patch
result = await workspace_manager.apply_patch("my-workspace", "@@ -1,1 +1,1 @@\n-old\n+new")

if not result["patch_applied"]:
    print(f"Error: {result['error_code']} - {result['error_message']}")
    # Output: Error: MISSING_FILE_HEADERS - Hunk header without file headers at line 1
```

## Error Handling Best Practices

### 1. **Check `patch_applied` Status**
Always check the `patch_applied` field before assuming success:

```python
result = await workspace_manager.apply_patch(workspace, patch)
if not result["patch_applied"]:
    handle_error(result["error_code"], result["error_message"])
```

### 2. **Use Error Codes for Logic**
Use error codes (not messages) for programmatic handling:

```python
if result["error_code"] == "INVALID_HUNK_HEADER":
    suggest_hunk_format_help()
elif result["error_code"] == "MISSING_FILE_HEADERS":
    suggest_adding_file_headers()
```

### 3. **Display User-Friendly Messages**
Error messages include line numbers for easy debugging:

```
"Invalid hunk header format at line 3: '@@ invalid hunk @@'"
```

### 4. **Validate Before Applying**
You can use the validation method directly:

```python
validation = workspace_manager._validate_patch_syntax(patch_content)
if not validation["valid"]:
    print(f"Patch invalid: {validation['error']}")
```

## Integration Testing

Test all error scenarios in your integration tests:

```python
@pytest.mark.asyncio
async def test_patch_error_codes():
    test_cases = [
        ("@@ -1,1 +1,1 @@\n-old\n+new", "MISSING_FILE_HEADERS"),
        ("--- a/f\n+++ b/f\n@@ bad @@\n+line", "INVALID_HUNK_HEADER"),
        ("+++ b/f\n@@ -1,1 +1,1 @@\n+line", "MISSING_OLD_FILE_HEADER"),
        ("--- a/f\n+++ b/f\n@@ -1,1 +1,1 @@\n*bad", "INVALID_LINE_PREFIX"),
    ]
    
    for patch, expected_error in test_cases:
        result = await workspace_manager.apply_patch("test", patch)
        assert result["error_code"] == expected_error
```

## Benefits

1. **Clear Error Reporting**: Specific error codes and line numbers
2. **Programmatic Handling**: Machine-readable error codes
3. **Fast Validation**: Syntax errors caught before processing
4. **Improved UX**: Users get immediate feedback on patch issues
5. **API Consistency**: Standard error response format
6. **Debugging Support**: Line-by-line error reporting

This error code system ensures robust patch handling and provides clear feedback when patches don't conform to the standard unified diff format. 