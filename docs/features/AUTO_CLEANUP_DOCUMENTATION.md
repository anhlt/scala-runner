# Auto-Cleanup Functionality for Bash Sessions

This document describes the automatic cleanup functionality for bash sessions, which helps manage system resources by automatically cleaning up inactive or timed-out sessions.

## Overview

The auto-cleanup system provides:
- **Automatic cleanup** of inactive bash sessions after a configurable timeout
- **Background task** that runs periodically to check for expired sessions
- **Manual control** via API endpoints
- **Configurable settings** for timeout and cleanup intervals
- **Detailed statistics** and monitoring

## Configuration

### Default Settings
- **Session Timeout**: 3600 seconds (1 hour)
- **Cleanup Interval**: 300 seconds (5 minutes)
- **Auto-cleanup Enabled**: True

### Configurable Parameters

| Parameter | Description | Default | Min Value |
|-----------|-------------|---------|-----------|
| `session_timeout` | Time in seconds after which inactive sessions are cleaned up | 3600 | 1 |
| `cleanup_interval` | How often the cleanup task runs (seconds) | 300 | 1 |
| `auto_cleanup_enabled` | Whether auto-cleanup is enabled | true | - |

## API Endpoints

### 1. Configure Auto-Cleanup Settings
```http
PUT /bash/auto-cleanup/configure
Content-Type: application/json

{
  "session_timeout": 1800,     // Optional: 30 minutes
  "cleanup_interval": 120,     // Optional: 2 minutes  
  "auto_cleanup_enabled": true // Optional: enable/disable
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "status": "updated",
    "old_settings": {...},
    "new_settings": {...},
    "message": "Cleanup configuration updated successfully"
  }
}
```

### 2. Start Auto-Cleanup
```http
POST /bash/auto-cleanup/start
```

**Response:**
```json
{
  "status": "success", 
  "data": {
    "status": "started",
    "cleanup_interval": 300,
    "session_timeout": 3600,
    "message": "Auto-cleanup task started successfully"
  }
}
```

### 3. Stop Auto-Cleanup
```http
POST /bash/auto-cleanup/stop
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "status": "stopped",
    "message": "Auto-cleanup task stopped successfully"
  }
}
```

### 4. Get Auto-Cleanup Statistics
```http
GET /bash/auto-cleanup/stats
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "configuration": {
      "session_timeout": 3600,
      "cleanup_interval": 300,
      "auto_cleanup_enabled": true,
      "max_sessions_per_workspace": 5
    },
    "statistics": {
      "total_sessions": 3,
      "active_sessions": 2,
      "inactive_sessions": 1,
      "sessions_to_cleanup": 1,
      "workspaces_with_sessions": 2
    },
    "auto_cleanup_task": {
      "running": true,
      "task_status": "running"
    },
    "sessions_pending_cleanup": [
      {
        "session_id": "bash_workspace1_abc123",
        "workspace_name": "workspace1", 
        "inactive_time": 3650.5,
        "will_cleanup": true
      }
    ]
  }
}
```

### 5. Manual Cleanup (Enhanced)
```http
POST /bash/cleanup
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "cleaned_sessions": 2,
    "sessions": [
      {
        "session_id": "bash_workspace1_abc123",
        "workspace_name": "workspace1",
        "inactive_time": 3650.5,
        "reason": "inactive"
      }
    ],
    "cleanup_time": 1635789123.456,
    "session_timeout": 3600
  }
}
```

## How It Works

### Session Lifecycle
1. **Session Creation**: When a bash session is created, its `created_at` and `last_used` timestamps are recorded
2. **Session Usage**: Each time a command is executed in a session, the `last_used` timestamp is updated
3. **Inactivity Detection**: A session is considered inactive if `(current_time - last_used) > session_timeout`
4. **Automatic Cleanup**: The background task periodically checks for inactive sessions and closes them

### Background Task
- Runs every `cleanup_interval` seconds
- Only processes sessions if there are any active sessions
- Logs cleanup activities for monitoring
- Handles errors gracefully without stopping the task
- Can be started/stopped without affecting running sessions

### Application Integration
- Auto-cleanup starts automatically when the application starts (if enabled)
- Stops gracefully when the application shuts down
- Cleans up any remaining sessions during shutdown

## Usage Examples

### Example 1: Configure Short Timeout for Development
```bash
curl -X PUT "http://localhost:8000/bash/auto-cleanup/configure" \
  -H "Content-Type: application/json" \
  -d '{
    "session_timeout": 600,
    "cleanup_interval": 60,
    "auto_cleanup_enabled": true
  }'
```

### Example 2: Disable Auto-Cleanup
```bash
curl -X PUT "http://localhost:8000/bash/auto-cleanup/configure" \
  -H "Content-Type: application/json" \
  -d '{"auto_cleanup_enabled": false}'
```

### Example 3: Monitor Session Activity
```bash
# Get current statistics
curl "http://localhost:8000/bash/auto-cleanup/stats"

# Manually trigger cleanup
curl -X POST "http://localhost:8000/bash/cleanup"
```

## Benefits

1. **Resource Management**: Automatically frees up Docker containers and system resources
2. **Security**: Reduces the attack surface by closing unused sessions
3. **Monitoring**: Provides detailed statistics for system monitoring
4. **Flexibility**: Fully configurable to meet different deployment needs
5. **Reliability**: Graceful error handling and logging

## Best Practices

1. **Production Settings**: Use longer timeouts (1+ hours) for production environments
2. **Development Settings**: Use shorter timeouts (10-30 minutes) for development
3. **Monitoring**: Regularly check cleanup statistics to optimize settings
4. **Manual Cleanup**: Use manual cleanup for immediate resource cleanup when needed
5. **Graceful Shutdown**: Let the application handle session cleanup during shutdown

## Troubleshooting

### Auto-Cleanup Not Running
- Check if auto-cleanup is enabled: `GET /bash/auto-cleanup/stats`
- Start auto-cleanup manually: `POST /bash/auto-cleanup/start`
- Check application logs for error messages

### Sessions Not Being Cleaned Up
- Verify session timeout configuration
- Check if sessions are actually inactive (last_used time)
- Try manual cleanup to test the cleanup logic
- Review cleanup statistics for pending sessions

### Performance Issues
- Increase cleanup interval if system load is high
- Reduce session timeout if resources are limited
- Monitor session creation/cleanup rates 