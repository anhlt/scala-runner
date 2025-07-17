# Scala Runner Sync Client

A Python client for the Scala Runner API with real-time file synchronization, GUI interface, and WebSocket support.

## Features

- **🖥️ GUI Interface**: Beautiful prompt toolkit-based GUI for workspace management
- **📡 Real-time Notifications**: WebSocket-based live file change notifications  
- **🔄 File Synchronization**: Automatic sync between server and local files
- **📝 Change Preview**: Built-in diff viewer for file changes
- **⌨️ CLI Interface**: Command-line tools for automation and scripting
- **🌐 WebSocket Support**: Real-time communication with the server
- **📂 Workspace Management**: Create, browse, and manage workspaces

## Installation

### From Source

```bash
cd scala_runner_sync_client
pip install -r requirements.txt
pip install -e .
```

### Using pip (if published)

```bash
pip install scala-runner-sync-client
```

## Usage

### GUI Mode (Default)

Start the graphical interface:

```bash
scala-runner-client
# or explicitly
scala-runner-client gui
```

The GUI provides:
- Workspace selection and management
- File browser with tree view
- File editor with syntax highlighting
- Real-time notifications panel
- Change preview with diff view
- Status monitoring

**Key Bindings:**
- `Ctrl+C`: Exit application
- `Ctrl+R`: Refresh workspaces
- `Ctrl+O`: Open selected file
- `Ctrl+S`: Save/update current file
- `Ctrl+N`: Create new file
- `F5`: Sync with server

### CLI Mode

#### Test Connection

Test connectivity to the Scala Runner server:

```bash
scala-runner-client test --server http://localhost:8000
```

#### Sync Workspace

Download and sync a workspace to local directory:

```bash
# Sync to default location (./local_workspace/WORKSPACE_NAME)
scala-runner-client sync my-workspace

# Sync to custom directory
scala-runner-client sync my-workspace --local-dir /path/to/local/workspace
```

#### Watch for Changes

Monitor workspace for real-time file changes:

```bash
scala-runner-client watch my-workspace
```

This will display real-time notifications when files are created, updated, or deleted on the server.

### Command Line Options

```bash
scala-runner-client --help

Options:
  --server URL         Server URL (default: http://localhost:8000)
  --verbose, -v        Enable verbose logging

Commands:
  gui                  Start GUI interface (default)
  test                 Test connection to server
  sync WORKSPACE       Sync workspace to local directory
  watch WORKSPACE      Watch workspace for real-time changes
```

## Configuration

### Environment Variables

- `SCALA_RUNNER_SERVER_URL`: Default server URL
- `SCALA_RUNNER_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Logging

Logs are written to `scala_runner_client.log` in the current directory. Use `--verbose` for detailed debug information.

## GUI Interface

### Main Layout

```
┌─ Workspaces ─────┬─ File Content ────────────────────────┐
│ □ workspace-1    │ object HelloWorld {                   │
│ ■ workspace-2    │   def main(args: Array[String]): Unit │
│ □ workspace-3    │     println("Hello, World!")         │
│                  │   }                                   │
│ [Connect]        │ }                                     │
│ [Refresh]        │                                       │
│ [Create]         │                                       │
├─ File Browser ───┼─ Changes Preview ─────────────────────┤
│ ■ src/           │ --- a/HelloWorld.scala                │
│   ■ main/        │ +++ b/HelloWorld.scala                │
│     ■ scala/     │ @@ -1,4 +1,4 @@                      │
│       □ Hello.sc │  object HelloWorld {                  │
│   □ test/        │ -  println("Hello")                   │
│                  │ +  println("Hello, World!")           │
│ [Open] [Sync]    │  }                                    │
│ [Update]         │                                       │
├─ Notifications ──────────────────────────────────────────┤
│ [12:34:56] ✓ Connected to workspace-2                    │
│ [12:35:12] 📝 Updated: src/main/scala/Hello.scala        │
│ [12:35:18] ⚠ Current file was updated on server          │
├─ Status ─────────────────────────────────────────────────┤
│ [12:35:20] Connected to workspace: workspace-2           │
└──────────────────────────────────────────────────────────┘
```

### Features

1. **Workspace Panel**: List and manage workspaces
   - Select workspace to connect
   - Create new workspaces
   - Real-time WebSocket connection status

2. **File Browser**: Navigate workspace files
   - Hierarchical tree view
   - File type icons and syntax highlighting
   - Quick actions (open, sync, update)

3. **File Editor**: Edit files with syntax highlighting
   - Live editing with auto-save
   - Undo/redo support
   - Search and replace

4. **Changes Preview**: Visual diff display
   - Side-by-side comparison
   - Unified diff format
   - Conflict resolution helpers

5. **Notifications**: Real-time event stream
   - File change notifications
   - Connection status updates
   - Error and success messages

## WebSocket Integration

The client connects to WebSocket endpoints for real-time updates:

- **General endpoint**: `ws://server/ws` - All workspace events
- **Workspace-specific**: `ws://server/ws/{workspace}` - File changes for specific workspace

### WebSocket Message Types

#### Received Messages

```json
{
  "type": "connected",
  "workspace": "my-workspace",
  "timestamp": 1234567890
}
```

```json
{
  "type": "file_change",
  "workspace": "my-workspace", 
  "timestamp": 1234567890,
  "data": {
    "action": "updated",
    "file_path": "src/main/scala/Hello.scala",
    "size": 1024
  }
}
```

```json
{
  "type": "workspace_event",
  "event": "created",
  "workspace": "new-workspace",
  "timestamp": 1234567890
}
```

#### Sent Messages

```json
{
  "type": "ping",
  "timestamp": 1234567890
}
```

```json
{
  "type": "subscribe_files",
  "files": ["src/main/scala/Hello.scala", "build.sbt"]
}
```

## File Synchronization

### Sync Metadata

The client maintains sync metadata in `.sync_metadata.json`:

```json
{
  "src/main/scala/Hello.scala": {
    "hash": "sha256:abc123...",
    "last_sync": "2024-01-15T10:30:00",
    "size": 1024
  }
}
```

### Sync Algorithm

1. **Hash Comparison**: Uses SHA256 hashes to detect changes
2. **Three-way Sync**: Compares local, server, and cached versions
3. **Conflict Detection**: Identifies when both local and server have changes
4. **Automatic Updates**: Downloads server changes automatically
5. **Manual Review**: Prompts for conflicts requiring user decision

### Sync Status

- `in_sync`: Files identical on local and server
- `local_changes`: Local file modified since last sync
- `server_changes`: Server file modified since last sync  
- `new_on_server`: Files exist on server but not locally
- `local_only`: Files exist locally but not on server

## API Client

The client provides a comprehensive async API wrapper:

```python
from scala_runner_sync_client import ScalaRunnerAPIClient

async with ScalaRunnerAPIClient("http://localhost:8000") as client:
    # Workspace operations
    workspaces = await client.list_workspaces()
    workspace = await client.create_workspace("my-project")
    
    # File operations  
    content = await client.get_file_content("my-project", "Hello.scala")
    await client.update_file("my-project", "Hello.scala", new_content)
    
    # Git operations
    status = await client.git_status("my-project")
    await client.git_commit("my-project", "Update file")
```

## Development

### Project Structure

```
scala_runner_sync_client/
├── __init__.py           # Package initialization
├── main.py              # CLI entry point
├── gui.py               # Prompt toolkit GUI
├── api_client.py        # HTTP API client
├── websocket_client.py  # WebSocket client
├── file_sync.py         # File synchronization
├── requirements.txt     # Dependencies
├── setup.py            # Package setup
└── README.md           # This file
```

### Dependencies

- `prompt-toolkit` - GUI framework
- `httpx` - Async HTTP client
- `websockets` - WebSocket client
- `aiofiles` - Async file operations
- `rich` - Rich text and syntax highlighting
- `pydantic` - Data validation

### Running from Source

```bash
cd scala_runner_sync_client

# Install dependencies
pip install -r requirements.txt

# Run GUI
python -m scala_runner_sync_client.main gui

# Run CLI commands
python -m scala_runner_sync_client.main test
python -m scala_runner_sync_client.main sync my-workspace
python -m scala_runner_sync_client.main watch my-workspace
```

## Troubleshooting

### Connection Issues

```bash
# Test server connectivity
scala-runner-client test --server http://your-server:8000

# Check verbose logs
scala-runner-client --verbose test
```

### WebSocket Problems

- Ensure server supports WebSocket endpoints `/ws` and `/ws/{workspace}`
- Check firewall settings for WebSocket connections
- Verify server URL uses correct protocol (`http://` vs `https://`)

### Sync Issues

```bash
# Force full workspace sync
scala-runner-client sync my-workspace --local-dir ./fresh-sync

# Check sync status
scala-runner-client sync my-workspace --dry-run
```

### GUI Issues

- Ensure terminal supports unicode characters for icons
- Try running with `--verbose` to see detailed error messages
- Check that prompt-toolkit is properly installed

## License

MIT License - see LICENSE file for details. 