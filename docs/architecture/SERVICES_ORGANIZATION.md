# Services Organization

This document describes the modular organization of the FastAPI application into separate service routers.

## Overview

The application has been refactored from a monolithic `main.py` file into a modular structure where endpoints are grouped by their functional domain. This improves code organization, maintainability, and makes it easier to understand the API structure.

## New Structure

```
scala_runner/
├── main.py                 # Main FastAPI app with router registration
├── routers/                # Service-specific router modules
│   ├── __init__.py        # Router exports
│   ├── workspace.py       # Workspace management endpoints
│   ├── git.py            # Git operations endpoints
│   ├── files.py          # File management endpoints
│   ├── search.py         # Search functionality endpoints
│   ├── sbt.py            # SBT command execution endpoints
│   ├── bash.py           # Bash session management endpoints
│   └── utils.py          # Utility endpoints (ping, openapi)
└── ...                   # Other modules unchanged
```

## Service Groups

### 1. Workspace Service (`/workspaces`)
**Module**: `scala_runner/routers/workspace.py`
**Tag**: `workspace`

Handles workspace lifecycle management:
- `POST /workspaces` - Create new workspace
- `GET /workspaces` - List all workspaces  
- `DELETE /workspaces/{workspace_name}` - Delete workspace
- `GET /workspaces/{workspace_name}/tree` - Get file tree
- `POST /workspaces/clone` - Clone from Git repository
- `GET /workspaces/{workspace_name}/git-info` - Get Git information

### 2. Git Operations Service (`/git`)
**Module**: `scala_runner/routers/git.py`
**Tag**: `git`

Handles Git version control operations:
- `POST /git/checkout` - Checkout branch
- `POST /git/add` - Add files to staging
- `POST /git/commit` - Commit changes
- `POST /git/push` - Push to remote
- `POST /git/pull` - Pull from remote
- `GET /git/status/{workspace_name}` - Get Git status
- `GET /git/log/{workspace_name}` - Get commit history

### 3. File Management Service (`/files`)
**Module**: `scala_runner/routers/files.py`
**Tag**: `files`

Handles file operations within workspaces:
- `POST /files` - Create new file
- `PUT /files` - Update existing file
- `PATCH /files` - Apply Git diff patch
- `DELETE /files/{workspace_name}/{file_path}` - Delete file
- `GET /files/{workspace_name}/{file_path}` - Get file content

### 4. Search Service (`/search`)
**Module**: `scala_runner/routers/search.py`
**Tag**: `search`

Handles content search across workspaces:
- `POST /search` - Search files by content

### 5. SBT Commands Service (`/sbt`)
**Module**: `scala_runner/routers/sbt.py`
**Tag**: `sbt`

Handles SBT build tool operations:
- `POST /sbt/run` - Execute SBT command
- `POST /sbt/compile` - Compile project
- `POST /sbt/run-project` - Run main class
- `POST /sbt/test` - Run tests
- `POST /sbt/clean` - Clean build artifacts
- `GET /sbt/project-info/{workspace_name}` - Get project info

### 6. Bash Sessions Service (`/bash`) - *Hidden from OpenAPI*
**Module**: `scala_runner/routers/bash.py`
**Tag**: `bash`
**Note**: *These endpoints are excluded from the OpenAPI schema but remain functional*

Handles interactive bash session management:
- `POST /bash/sessions` - Create bash session
- `POST /bash/execute` - Execute command in session
- `DELETE /bash/sessions/{session_id}` - Close session
- `DELETE /bash/workspaces/{workspace_name}/sessions` - Close all workspace sessions
- `GET /bash/sessions` - List sessions
- `GET /bash/sessions/{session_id}` - Get session info
- `POST /bash/cleanup` - Manual cleanup
- `POST /bash/auto-cleanup/start` - Start auto-cleanup
- `POST /bash/auto-cleanup/stop` - Stop auto-cleanup
- `PUT /bash/auto-cleanup/configure` - Configure cleanup
- `GET /bash/auto-cleanup/stats` - Get cleanup stats

### 7. Utilities Service
**Module**: `scala_runner/routers/utils.py`
**Tag**: `utils`

Handles utility endpoints:
- `GET /ping` - Health check
- `GET /openapi` - OpenAPI schema alias

## Benefits

1. **Improved Organization**: Related endpoints are grouped together logically
2. **Better Maintainability**: Each service module can be maintained independently
3. **Cleaner Code**: Reduced complexity in main.py file
4. **Better Testing**: Individual service modules can be tested in isolation
5. **Clearer API Documentation**: OpenAPI schema is organized by service tags
6. **Easier Development**: New endpoints can be added to appropriate service modules
7. **Flexible API Exposure**: Some services (like bash sessions) can be hidden from public documentation while remaining functional

## Implementation Details

- Each router module defines its own Pydantic models for request/response validation
- Dependency injection is used to share manager instances across routers
- Rate limiting is applied consistently across all endpoints
- Error handling patterns are maintained from the original implementation
- The main FastAPI app registers all routers and handles application lifecycle
- Bash session endpoints are excluded from OpenAPI schema (`include_in_schema=False`) but remain fully functional

## Usage

The API endpoints remain the same - only the internal code organization has changed. All existing client code will continue to work without modification.

The OpenAPI documentation will now show endpoints grouped by service tags, making it easier to navigate the API documentation. 