# Async Lock and FIFO Queue System for Indexing

## Overview

This implementation provides a robust async lock and FIFO (First In, First Out) queue system for Whoosh indexing operations. It prevents race conditions, ensures proper ordering, and provides better performance and reliability.

## 🔧 Key Components

### 1. **IndexTask and IndexTaskType**
```python
class IndexTaskType(Enum):
    INDEX_FILE = "index_file"
    REMOVE_FILE = "remove_file" 
    REMOVE_WORKSPACE = "remove_workspace"
    REINDEX_WORKSPACE = "reindex_workspace"

@dataclass
class IndexTask:
    task_type: IndexTaskType
    workspace_name: str
    file_path: Optional[str] = None
    content: Optional[str] = None
    priority: int = 0
    timestamp: float = 0.0
```

### 2. **Async Lock and Queue**
```python
self._index_lock = asyncio.Lock()
self._index_queue: asyncio.Queue[IndexTask] = asyncio.Queue()
self._index_worker_task: Optional[asyncio.Task] = None
self._shutdown_event = asyncio.Event()
```

### 3. **Background Worker**
- Continuously processes tasks from the FIFO queue
- Uses async lock to prevent concurrent index modifications
- Graceful shutdown with proper cleanup

## 🛡️ Race Condition Prevention

### Before (Problems):
- Multiple threads could modify Whoosh index simultaneously
- Race conditions could corrupt the index
- No guaranteed ordering of operations
- Difficult to debug indexing issues

### After (Solutions):
- **Async Lock**: Only one indexing operation at a time
- **FIFO Queue**: Guaranteed processing order
- **Background Worker**: Asynchronous processing without blocking API calls
- **Error Isolation**: Failed tasks don't affect others

## 📊 Queue System Architecture

```
API Call → Queue Task → Background Worker → Lock Protected Operation → Index Update
    ↓           ↓              ↓                      ↓                    ↓
 Immediate   FIFO Order   Async Processing    Thread Safety        Data Integrity
 Return      Preserved    Non-blocking        Guaranteed           Ensured
```

## 🔍 Monitoring and Status

### Queue Status Monitoring
```python
status = await tools.get_index_queue_status()
# Returns:
{
    "queue_size": 3,
    "worker_running": True,
    "shutdown_requested": False
}
```

### Index Status
```python
status = await tools.get_index_status(workspace_name)
# Returns:
{
    "filesystem_files": 15,
    "indexed_files": 15,
    "is_up_to_date": True,
    "missing_files": 0,
    "extra_indexed": 0,
    "index_coverage": 100.0
}
```

## 🚀 Usage Examples

### 1. **Basic File Operations (Automatic Queuing)**
```python
# These operations automatically queue indexing tasks
await tools.create_file(workspace_name, "file.scala", content)
await tools.update_file(workspace_name, "file.scala", new_content)
await tools.delete_file(workspace_name, "file.scala")
```

### 2. **Concurrent Operations (Safe)**
```python
# These will be processed in FIFO order with lock protection
tasks = []
for i in range(10):
    tasks.append(tools.create_file(workspace_name, f"file_{i}.scala", content))

# All operations are queued immediately, processed sequentially
await asyncio.gather(*tasks)
```

### 3. **Wait for Completion**
```python
# Wait for all queued tasks to complete
await tools.wait_for_index_ready(workspace_name, timeout=30)
```

### 4. **Force Reindexing (Queue-based)**
```python
# This uses the queue system for safe reindexing
await tools.force_reindex_workspace(workspace_name)
```

## 📈 Performance Benefits

### 1. **Non-blocking API Calls**
- API calls return immediately after queueing
- No waiting for index operations to complete
- Better user experience

### 2. **Batch Processing**
- Background worker can optimize similar operations
- Reduced overhead from frequent index opens/closes
- Better resource utilization

### 3. **Error Recovery**
- Failed tasks don't block subsequent operations
- Centralized error logging and handling
- System remains stable under error conditions

## 🧪 Testing

### Run the Test Suite
```bash
# Test basic index management
python test_index_management.py

# Test async lock and FIFO queue specifically
python test_async_indexing.py
```

### Test Features:
- **Concurrent file creation/updates**
- **FIFO ordering verification** 
- **Queue status monitoring**
- **Race condition prevention**
- **Error handling**
- **Performance under load**

## 🔧 Configuration

### Worker Settings
```python
# In WorkspaceManager.__init__()
self._index_lock = asyncio.Lock()
self._index_queue: asyncio.Queue[IndexTask] = asyncio.Queue()

# Queue timeout for graceful shutdown
SHUTDOWN_TIMEOUT = 30.0  # seconds
```

### Task Priorities
```python
# Higher priority tasks (lower number = higher priority)
task = IndexTask(
    task_type=IndexTaskType.REINDEX_WORKSPACE,
    workspace_name=workspace_name,
    priority=1  # Higher priority
)
```

## 🛠️ Implementation Details

### 1. **Direct vs Queued Methods**
```python
# Queued methods (public API)
async def _index_file(self, workspace_name, file_path, content):
    # Creates task and queues it
    
# Direct methods (worker only)
async def _index_file_direct(self, workspace_name, file_path, content):
    # Actually performs indexing with lock protection
```

### 2. **Background Worker Loop**
```python
async def _index_worker(self):
    while not self._shutdown_event.is_set():
        try:
            task = await asyncio.wait_for(self._index_queue.get(), timeout=1.0)
            async with self._index_lock:
                await self._process_index_task(task)
            self._index_queue.task_done()
        except asyncio.TimeoutError:
            continue  # Check shutdown event
```

### 3. **Graceful Shutdown**
```python
async def shutdown(self):
    self._shutdown_event.set()
    await asyncio.wait_for(self._index_queue.join(), timeout=30.0)
    if self._index_worker_task:
        self._index_worker_task.cancel()
```

## 🚨 Error Handling

### Task Validation
- Required fields checked before processing
- Invalid tasks logged and skipped
- Continues processing other tasks

### Worker Recovery
- Exceptions don't crash the worker
- Error logging for debugging
- Automatic retry for transient failures

### Graceful Degradation
- Queue overflow protection
- Timeout handling
- Resource cleanup

## 📋 Best Practices

### 1. **Always Wait for Index Ready**
```python
# Before searching, ensure index is up to date
await tools.wait_for_index_ready(workspace_name)
results = await tools.search_files(workspace_name, query)
```

### 2. **Monitor Queue Status**
```python
# Check queue health periodically
status = await tools.get_index_queue_status()
if status["queue_size"] > 100:
    # Consider throttling operations
```

### 3. **Handle Timeouts Appropriately**
```python
# Use reasonable timeouts
await tools.wait_for_index_ready(workspace_name, timeout=30)
```

### 4. **Batch Operations When Possible**
```python
# Create multiple files then wait once
for file_data in file_list:
    await tools.create_file(workspace_name, file_data.path, file_data.content)

# Wait for all to complete
await tools.wait_for_index_ready(workspace_name)
```

## 🔄 Migration from Old System

### Old Approach (Direct)
```python
# Old: Direct indexing with potential race conditions
async def _index_file(self, workspace_name, file_path, content):
    # Direct Whoosh operations
    index = open_dir(str(self.index_dir))
    writer = index.writer()
    # ... direct operations
```

### New Approach (Queued)
```python
# New: Queue-based with lock protection
async def _index_file(self, workspace_name, file_path, content):
    task = IndexTask(IndexTaskType.INDEX_FILE, workspace_name, file_path, content)
    await self._queue_index_task(task)
```

## 💡 Future Enhancements

### Potential Improvements:
1. **Task Priorities**: Higher priority for critical operations
2. **Batch Operations**: Combine similar tasks for efficiency
3. **Metrics Collection**: Performance monitoring and analytics
4. **Persistent Queue**: Survive server restarts
5. **Multiple Workers**: Parallel processing for different workspaces

## 🧩 Integration with Existing Code

The async lock and FIFO queue system is fully backward compatible:

- All existing API calls work unchanged
- Performance improvements are automatic
- Race conditions are eliminated
- Better error handling is built-in

The system maintains the same external API while providing:
- **Better reliability**
- **Improved performance** 
- **Race condition prevention**
- **Enhanced monitoring** 