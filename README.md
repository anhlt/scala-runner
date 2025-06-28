# Scala SBT Workspace API

A FastAPI-based service for managing Scala SBT project workspaces with Docker integration. This API allows you to create and manage multiple SBT project workspaces, perform file operations, search through code, and execute SBT commands via Docker containers.

## Features

- **Workspace Management**: Create, list, and delete SBT project workspaces
- **File Operations**: Create, read, update, and delete files within workspaces
- **File Tree Structure**: Get directory tree structure (like `tree` command)
- **Full-Text Search**: Search through files with indexing support
- **SBT Commands**: Execute SBT commands (compile, run, test, etc.) in Docker containers
- **Rate Limiting**: Built-in API rate limiting
- **Docker Isolation**: All SBT operations run in isolated Docker containers

## Requirements

- Python 3.8+
- Docker
- SBT Docker image (`sbtscala/scala-sbt:eclipse-temurin-jammy-17.0.8.1_1.9.6_3.3.1`)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set environment variables (optional):

```bash
export RATE_LIMIT="10/minute"  # Rate limit per IP
export BASE_DIR="/tmp"         # Base directory for workspaces
```

## Running the Server

```bash
uvicorn scala_runner.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Workspace Management

#### Create Workspace
```bash
POST /workspaces
```
Creates a new SBT workspace with basic project structure.

**Request Body:**
```json
{
  "name": "my-project"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "workspace_name": "my-project",
    "path": "/tmp/workspaces/my-project",
    "created": true
  }
}
```

#### Clone Workspace from Git
```bash
POST /workspaces/clone
```
Clone a Git repository into a new workspace.

**Request Body:**
```json
{
  "name": "my-cloned-project",
  "git_url": "https://github.com/user/scala-project.git",
  "branch": "main"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "workspace_name": "my-cloned-project",
    "path": "/tmp/workspaces/my-cloned-project",
    "cloned": true,
    "git_info": {
      "remote_url": "https://github.com/user/scala-project.git",
      "active_branch": "main",
      "latest_commit": {
        "hash": "abc12345",
        "message": "Initial commit",
        "author": "John Doe <john@example.com>",
        "date": "2024-01-15T10:30:00+00:00"
      }
    },
    "is_sbt_project": true,
    "files_indexed": 15
  }
}
```

#### List Workspaces
```bash
GET /workspaces
```

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "name": "my-project",
      "path": "/tmp/workspaces/my-project",
      "files_count": 4
    }
  ]
}
```

#### Delete Workspace
```bash
DELETE /workspaces/{workspace_name}
```

#### Get Workspace File Tree
```bash
GET /workspaces/{workspace_name}/tree
```

#### Get Git Repository Information
```bash
GET /workspaces/{workspace_name}/git-info
```
Get Git repository information for a workspace (if it's a Git repository).

**Response:**
```json
{
  "status": "success",
  "data": {
    "is_git_repo": true,
    "active_branch": "main",
    "latest_commit": {
      "hash": "abc12345",
      "full_hash": "abc1234567890abcdef1234567890abcdef123456",
      "message": "Add new feature",
      "author": "John Doe <john@example.com>",
      "date": "2024-01-15T10:30:00+00:00"
    },
    "remotes": [
      {
        "name": "origin",
        "url": "https://github.com/user/scala-project.git"
      }
    ],
    "branches": [
      {
        "name": "main",
        "is_active": true
      },
      {
        "name": "develop",
        "is_active": false
      }
    ],
    "has_uncommitted_changes": false,
    "untracked_files": []
  }
}
```

### File Management

#### Create File
```bash
POST /files
```

**Request Body:**
```json
{
  "workspace_name": "my-project",
  "file_path": "src/main/scala/Hello.scala",
  "content": "object Hello extends App {\n  println(\"Hello, World!\")\n}"
}
```

#### Update File
```bash
PUT /files
```

#### Get File Content
```bash
GET /files/{workspace_name}/{file_path}
```

#### Delete File
```bash
DELETE /files/{workspace_name}/{file_path}
```

### Search

#### Search Files
```bash
POST /search
```

**Request Body:**
```json
{
  "workspace_name": "my-project",
  "query": "println",
  "limit": 10
}
```

### Git Operations

#### Checkout Branch
```bash
POST /git/checkout
```
Switch to a branch or create a new one.

**Request Body:**
```json
{
  "workspace_name": "my-project",
  "branch_name": "feature-branch",
  "create_new": true
}
```

#### Add Files to Staging
```bash
POST /git/add
```
Add files to Git staging area.

**Request Body:**
```json
{
  "workspace_name": "my-project",
  "file_paths": ["src/main/scala/Hello.scala", "build.sbt"]
}
```
*Note: Omit `file_paths` to add all files*

#### Commit Changes
```bash
POST /git/commit
```
Commit staged changes.

**Request Body:**
```json
{
  "workspace_name": "my-project",
  "message": "Add new feature",
  "author_name": "John Doe",
  "author_email": "john@example.com"
}
```

#### Push Changes
```bash
POST /git/push
```
Push changes to remote repository.

**Request Body:**
```json
{
  "workspace_name": "my-project",
  "remote_name": "origin",
  "branch_name": "main"
}
```

#### Pull Changes
```bash
POST /git/pull
```
Pull changes from remote repository.

**Request Body:**
```json
{
  "workspace_name": "my-project",
  "remote_name": "origin",
  "branch_name": "main"
}
```

#### Get Git Status
```bash
GET /git/status/{workspace_name}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "workspace_name": "my-project",
    "current_branch": "main",
    "is_dirty": true,
    "untracked_files": ["new-file.scala"],
    "modified_files": ["src/main/scala/Hello.scala"],
    "staged_files": ["build.sbt"],
    "ahead_behind": {
      "ahead": 2,
      "behind": 0
    }
  }
}
```

#### Get Commit History
```bash
GET /git/log/{workspace_name}?limit=5
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "workspace_name": "my-project",
    "current_branch": "main",
    "total_commits_shown": 3,
    "commits": [
      {
        "hash": "abc12345",
        "full_hash": "abc1234567890abcdef1234567890abcdef123456",
        "message": "Add new feature",
        "author": "John Doe <john@example.com>",
        "date": "2024-01-15T10:30:00+00:00",
        "files_changed": 2
      }
    ]
  }
}
```

### SBT Commands

#### Run Custom SBT Command
```bash
POST /sbt/run
```

**Request Body:**
```json
{
  "workspace_name": "my-project",
  "command": "compile",
  "timeout": 300
}
```

#### Compile Project
```bash
POST /sbt/compile
```

#### Run Project
```bash
POST /sbt/run-project
```

#### Run Tests
```bash
POST /sbt/test
```

#### Clean Project
```bash
POST /sbt/clean
```

#### Get Project Info
```bash
GET /sbt/project-info/{workspace_name}
```

### Utility Endpoints

#### Health Check
```bash
GET /ping
```

#### OpenAPI Schema
```bash
GET /openapi
```

## Docker Usage

### Build Docker Image
```bash
docker build -t scala-workspace-api .
```

### Run Container
```bash
docker run -p 8000:8000 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /tmp/workspaces:/tmp/workspaces \
    scala-workspace-api
```

## Workspace Structure

Each workspace is created with the following SBT project structure:

```
workspace-name/
├── build.sbt
├── project/
│   └── plugins.sbt
└── src/
    ├── main/
    │   └── scala/
    │       └── Main.scala
    └── test/
        └── scala/
```

## Security Features

- **Command Validation**: Only safe SBT commands are allowed
- **Input Sanitization**: File paths and workspace names are validated
- **Rate Limiting**: API calls are rate-limited per IP address
- **Docker Isolation**: All SBT operations run in isolated containers

## Examples

### Complete Workflow Example

#### Example 1: Create New Workspace

```bash
# 1. Create workspace
curl -X POST "http://localhost:8000/workspaces" \
     -H "Content-Type: application/json" \
     -d '{"name": "hello-scala"}'

# 2. Create a Scala file
curl -X POST "http://localhost:8000/files" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "hello-scala",
       "file_path": "src/main/scala/HelloWorld.scala",
       "content": "object HelloWorld extends App {\n  println(\"Hello from SBT!\")\n}"
     }'

# 3. Compile the project
curl -X POST "http://localhost:8000/sbt/compile" \
     -H "Content-Type: application/json" \
     -d '{"workspace_name": "hello-scala"}'

# 4. Run the project
curl -X POST "http://localhost:8000/sbt/run-project" \
     -H "Content-Type: application/json" \
     -d '{"workspace_name": "hello-scala"}'

# 5. Search for content
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "hello-scala",
       "query": "println",
       "limit": 5
     }'
```

#### Example 2: Clone Git Repository

```bash
# 1. Clone a Scala project from GitHub
curl -X POST "http://localhost:8000/workspaces/clone" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "scala-examples",
       "git_url": "https://github.com/scala/scala-lang.git",
       "branch": "main"
     }'

# 2. Get repository information
curl -X GET "http://localhost:8000/workspaces/scala-examples/git-info"

# 3. View the cloned project structure
curl -X GET "http://localhost:8000/workspaces/scala-examples/tree"

# 4. Search through cloned files
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "scala-examples",
       "query": "class",
       "limit": 10
     }'

# 5. Compile the cloned project (if it's an SBT project)
curl -X POST "http://localhost:8000/sbt/compile" \
     -H "Content-Type: application/json" \
     -d '{"workspace_name": "scala-examples"}'
```

#### Example 3: Git Workflow

```bash
# 1. Create new branch
curl -X POST "http://localhost:8000/git/checkout" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "my-project",
       "branch_name": "feature-auth",
       "create_new": true
     }'

# 2. Make some changes to files (using file endpoints)
curl -X PUT "http://localhost:8000/files" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "my-project",
       "file_path": "src/main/scala/Auth.scala",
       "content": "object Auth { def authenticate(): Boolean = true }"
     }'

# 3. Check Git status
curl -X GET "http://localhost:8000/git/status/my-project"

# 4. Add files to staging
curl -X POST "http://localhost:8000/git/add" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "my-project",
       "file_paths": ["src/main/scala/Auth.scala"]
     }'

# 5. Commit changes
curl -X POST "http://localhost:8000/git/commit" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "my-project",
       "message": "Add authentication module",
       "author_name": "John Doe",
       "author_email": "john@example.com"
     }'

# 6. Push to remote
curl -X POST "http://localhost:8000/git/push" \
     -H "Content-Type: application/json" \
     -d '{
       "workspace_name": "my-project",
       "remote_name": "origin",
       "branch_name": "feature-auth"
     }'

# 7. View commit history
curl -X GET "http://localhost:8000/git/log/my-project?limit=5"
```

## Development

### Running Tests
```bash
pytest tests/
```

### API Documentation
Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Docker Issues
- Ensure Docker is running and accessible
- Check if the SBT Docker image is available

### Permission Issues
- Ensure the API has write permissions to the base directory
- Check Docker socket permissions if running in a container

### Git Clone Issues
- Verify the Git URL is accessible and correct
- For private repositories, ensure proper authentication is configured
- Check if the specified branch exists in the remote repository
- Ensure sufficient disk space for cloning large repositories

### Search Not Working
- Verify Whoosh index is properly initialized
- Check if files are being indexed after creation/updates
- For cloned repositories, indexing happens automatically but may take time for large repos

### SBT Build Issues
- Verify the cloned project has a valid `build.sbt` file
- Check if the project's Scala version is compatible with the SBT Docker image
- Review SBT logs for dependency resolution issues 