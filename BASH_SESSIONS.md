# Bash Sessions API

This document describes the bash session functionality that allows you to run interactive bash commands within workspace containers.

## Overview

The bash session feature provides:
- **Create Session**: Start a new bash session in a Docker container for a workspace
- **Execute Commands**: Run bash commands interactively within the session
- **Session Management**: List, monitor, and close sessions
- **Safety Features**: Built-in protection against dangerous commands

All bash sessions run inside Docker containers with the same environment as SBT commands, ensuring consistency.

## API Endpoints

### Create a Bash Session

**POST** `/bash/sessions`

Creates a new bash session for a workspace.

```json
{
  "workspace_name": "my-workspace"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "bash_my-workspace_a1b2c3d4",
    "workspace_name": "my-workspace", 
    "status": "started",
    "created_at": 1703123456.789
  }
}
```

### Execute Command

**POST** `/bash/execute`

Execute a bash command in an existing session.

```json
{
  "session_id": "bash_my-workspace_a1b2c3d4",
  "command": "ls -la",
  "timeout": 30
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "bash_my-workspace_a1b2c3d4",
    "command": "ls -la",
    "status": "success",
    "output": "total 8\ndrwxr-xr-x 1 root root 4096 Dec 21 10:30 .\ndrwxr-xr-x 1 root root 4096 Dec 21 10:30 ..\n-rw-r--r-- 1 root root  123 Dec 21 10:30 build.sbt",
    "stderr": [],
    "success": true,
    "workspace_name": "my-workspace"
  }
}
```

### List Sessions

**GET** `/bash/sessions`

List all active bash sessions.

**Optional Query Parameters:**
- `workspace_name`: Filter sessions by workspace

**Response:**
```json
{
  "status": "success",
  "data": {
    "workspace_name": null,
    "total_sessions": 2,
    "sessions": [
      {
        "session_id": "bash_workspace1_a1b2c3d4",
        "workspace_name": "workspace1",
        "workspace_path": "/tmp/workspaces/workspace1",
        "is_active": true,
        "created_at": 1703123456.789,
        "last_used": 1703123500.123,
        "uptime": 43.334
      }
    ]
  }
}
```

### Get Session Info

**GET** `/bash/sessions/{session_id}`

Get detailed information about a specific session.

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "bash_my-workspace_a1b2c3d4",
    "workspace_name": "my-workspace",
    "workspace_path": "/tmp/workspaces/my-workspace",
    "is_active": true,
    "created_at": 1703123456.789,
    "last_used": 1703123500.123,
    "uptime": 43.334
  }
}
```

### Close Session

**DELETE** `/bash/sessions/{session_id}`

Close a specific bash session.

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "bash_my-workspace_a1b2c3d4",
    "workspace_name": "my-workspace",
    "status": "closed"
  }
}
```

### Close All Workspace Sessions

**DELETE** `/bash/workspaces/{workspace_name}/sessions`

Close all bash sessions for a workspace.

**Response:**
```json
{
  "status": "success",
  "data": {
    "workspace_name": "my-workspace",
    "closed_sessions": 2,
    "results": [
      {
        "session_id": "bash_my-workspace_a1b2c3d4",
        "workspace_name": "my-workspace",
        "status": "closed"
      }
    ]
  }
}
```

### Cleanup Inactive Sessions

**POST** `/bash/cleanup`

Clean up inactive or timed-out sessions.

**Response:**
```json
{
  "status": "success",
  "data": {
    "cleaned_sessions": 3,
    "session_ids": ["bash_old-workspace_x1y2z3w4", "bash_test_p9q8r7s6"]
  }
}
```

## Docker Environment

Bash sessions run in Docker containers with:
- **Base Image**: `sbtscala/scala-sbt:eclipse-temurin-alpine-21.0.7_6_1.11.2_3.7.1`
- **Working Directory**: `/workspace` (mounted from workspace directory)
- **Available Tools**: Java, Scala, SBT, standard Linux utilities
- **Persistent Cache**: SBT/Ivy/Coursier caches are shared across sessions

## Safety Features

The API includes built-in safety checks that prevent execution of dangerous commands:

### Blocked Commands
- `rm -rf /` - System deletion
- `sudo` / `su` - Privilege escalation  
- `shutdown` / `reboot` / `halt` - System control
- Fork bombs and similar destructive patterns
- File system formatting commands
- Direct device access

### Safety Guidelines
- Commands are executed within the container only
- No access to host system outside workspace
- Automatic session cleanup prevents resource leaks
- Session limits prevent abuse

## Usage Examples

### Basic File Operations

```bash
# Create session
curl -X POST http://localhost:8000/bash/sessions \
  -H "Content-Type: application/json" \
  -d '{"workspace_name": "my-project"}'

# Create a file
curl -X POST http://localhost:8000/bash/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "bash_my-project_a1b2c3d4",
    "command": "echo \"Hello World\" > hello.txt"
  }'

# Read the file
curl -X POST http://localhost:8000/bash/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "bash_my-project_a1b2c3d4", 
    "command": "cat hello.txt"
  }'
```

### Scala Development

```bash
# Check environment
curl -X POST http://localhost:8000/bash/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "bash_my-project_a1b2c3d4",
    "command": "java -version && sbt --version"
  }'

# Compile project
curl -X POST http://localhost:8000/bash/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "bash_my-project_a1b2c3d4",
    "command": "sbt compile",
    "timeout": 120
  }'

# Run tests
curl -X POST http://localhost:8000/bash/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "bash_my-project_a1b2c3d4",
    "command": "sbt test",
    "timeout": 180
  }'
```

### Git Operations

```bash
# Check git status
curl -X POST http://localhost:8000/bash/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "bash_my-project_a1b2c3d4",
    "command": "git status"
  }'

# Create and switch branch
curl -X POST http://localhost:8000/bash/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "bash_my-project_a1b2c3d4",
    "command": "git checkout -b feature-branch"
  }'
```

## Session Management

### Limits
- **Max sessions per workspace**: 5
- **Session timeout**: 1 hour of inactivity
- **Command timeout**: 30 seconds (configurable per command)

### Best Practices
1. Close sessions when done to free resources
2. Use appropriate timeouts for long-running commands
3. Monitor session usage with list endpoints
4. Run cleanup periodically for inactive sessions

## Error Handling

### Common Error Responses

**400 Bad Request** - Invalid input or unsafe command
```json
{
  "detail": "Unsafe command detected: rm -rf /"
}
```

**404 Not Found** - Session or workspace not found
```json
{
  "detail": "Session 'invalid_session_id' not found"
}
```

**500 Internal Server Error** - System error
```json
{
  "detail": "Internal server error: Container failed to start"
}
```

### Timeout Handling
Commands that exceed their timeout return:
```json
{
  "status": "success",
  "data": {
    "session_id": "bash_my-project_a1b2c3d4",
    "command": "sleep 60",
    "status": "timeout", 
    "output": "Command timed out after 30 seconds",
    "stderr": [],
    "success": false,
    "timeout": true
  }
}
``` 