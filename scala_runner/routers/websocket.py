"""
WebSocket endpoints for real-time file change notifications.
"""

import logging
import json
import asyncio
from typing import Dict, Set, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pathlib import Path
import time
from asyncio import Queue

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["websocket"],
)

# Global connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.workspace_watchers: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, workspace_name: Optional[str] = None):
        """Connect a WebSocket client"""
        await websocket.accept()
        
        if workspace_name:
            if workspace_name not in self.workspace_watchers:
                self.workspace_watchers[workspace_name] = set()
            self.workspace_watchers[workspace_name].add(websocket)
            logger.info(f"WebSocket connected for workspace: {workspace_name}")
        else:
            # General connection (not workspace-specific)
            if "general" not in self.active_connections:
                self.active_connections["general"] = []
            self.active_connections["general"].append(websocket)
            logger.info("General WebSocket connection established")
    
    async def disconnect(self, websocket: WebSocket, workspace_name: Optional[str] = None):
        """Disconnect a WebSocket client"""
        if workspace_name:
            if workspace_name in self.workspace_watchers:
                self.workspace_watchers[workspace_name].discard(websocket)
                if not self.workspace_watchers[workspace_name]:
                    del self.workspace_watchers[workspace_name]
                logger.info(f"WebSocket disconnected from workspace: {workspace_name}")
        else:
            if "general" in self.active_connections:
                try:
                    self.active_connections["general"].remove(websocket)
                except ValueError:
                    pass
                if not self.active_connections["general"]:
                    del self.active_connections["general"]
            logger.info("General WebSocket connection closed")
    
    async def broadcast_file_change(self, workspace_name: str, change_data: Dict):
        """Broadcast file change to all connected clients for a workspace"""
        if workspace_name not in self.workspace_watchers:
            return
            
        connections_to_remove = []
        for websocket in self.workspace_watchers[workspace_name]:
            try:
                await websocket.send_json({
                    "type": "file_change",
                    "workspace": workspace_name,
                    "timestamp": time.time(),
                    "data": change_data
                })
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                connections_to_remove.append(websocket)
        
        # Remove dead connections
        for websocket in connections_to_remove:
            self.workspace_watchers[workspace_name].discard(websocket)
    
    async def broadcast_workspace_event(self, event_type: str, workspace_name: str, data: Dict):
        """Broadcast workspace-level events (create, delete, etc.)"""
        message = {
            "type": "workspace_event",
            "event": event_type,
            "workspace": workspace_name,
            "timestamp": time.time(),
            "data": data
        }
        
        # Broadcast to workspace-specific connections
        if workspace_name in self.workspace_watchers:
            connections_to_remove = []
            for websocket in self.workspace_watchers[workspace_name]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending workspace event: {e}")
                    connections_to_remove.append(websocket)
            
            for websocket in connections_to_remove:
                self.workspace_watchers[workspace_name].discard(websocket)
        
        # Also broadcast to general connections
        if "general" in self.active_connections:
            connections_to_remove = []
            for websocket in self.active_connections["general"]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending workspace event to general connection: {e}")
                    connections_to_remove.append(websocket)
            
            for websocket in connections_to_remove:
                self.active_connections["general"].remove(websocket)

# Global instance
connection_manager = ConnectionManager()

# WebSocket endpoints
@router.websocket("/ws")
async def websocket_general_endpoint(websocket: WebSocket):
    """General WebSocket endpoint for all workspace events"""
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle ping/pong
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
            except json.JSONDecodeError:
                # Ignore invalid JSON
                pass
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)

@router.websocket("/ws/{workspace_name}")
async def websocket_workspace_endpoint(websocket: WebSocket, workspace_name: str):
    """WebSocket endpoint for specific workspace file changes"""
    await connection_manager.connect(websocket, workspace_name)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "workspace": workspace_name,
            "message": f"Connected to workspace: {workspace_name}",
            "timestamp": time.time()
        })
        
        while True:
            # Keep connection alive and handle ping/pong
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                elif message.get("type") == "subscribe_files":
                    # Client can request to subscribe to specific files
                    files = message.get("files", [])
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "files": files,
                        "timestamp": time.time()
                    })
            except json.JSONDecodeError:
                # Ignore invalid JSON
                pass
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, workspace_name)

# Function to get the connection manager (for use by other modules)
def get_connection_manager():
    return connection_manager 