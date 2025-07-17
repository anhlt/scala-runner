"""
WebSocket client for real-time file change notifications from Scala Runner server.
"""

import asyncio
import json
import logging
import time
from typing import Callable, Optional, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

class WebSocketClient:
    def __init__(self, server_url: str, workspace_name: Optional[str] = None):
        self.server_url = server_url
        self.workspace_name = workspace_name
        self.websocket = None
        self.running = False
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_attempts = 10
        self.reconnect_attempts = 0
        
        # Event handlers
        self.on_file_change: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_workspace_event: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
    def set_file_change_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Set handler for file change events"""
        self.on_file_change = handler
        
    def set_workspace_event_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Set handler for workspace events"""
        self.on_workspace_event = handler
        
    def set_connection_handlers(self, 
                               on_connected: Optional[Callable[[], None]] = None,
                               on_disconnected: Optional[Callable[[], None]] = None,
                               on_error: Optional[Callable[[Exception], None]] = None):
        """Set connection state handlers"""
        if on_connected:
            self.on_connected = on_connected
        if on_disconnected:
            self.on_disconnected = on_disconnected
        if on_error:
            self.on_error = on_error
    
    def _get_websocket_url(self) -> str:
        """Get the appropriate WebSocket URL"""
        # Convert HTTP URL to WebSocket URL
        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        
        if self.workspace_name:
            return f"{ws_url}/ws/{self.workspace_name}"
        else:
            return f"{ws_url}/ws"
    
    async def connect(self):
        """Connect to the WebSocket server"""
        if self.running:
            return
            
        self.running = True
        url = self._get_websocket_url()
        
        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                logger.info(f"Connecting to WebSocket: {url}")
                self.websocket = await websockets.connect(url)
                self.reconnect_attempts = 0
                
                if self.on_connected:
                    self.on_connected()
                
                await self._listen()
                
            except (ConnectionClosed, WebSocketException) as e:
                logger.warning(f"WebSocket connection error: {e}")
                if self.on_error:
                    self.on_error(e)
                await self._handle_disconnect()
                
            except Exception as e:
                logger.error(f"Unexpected WebSocket error: {e}")
                if self.on_error:
                    self.on_error(e)
                await self._handle_disconnect()
    
    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        self.running = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            finally:
                self.websocket = None
        
        if self.on_disconnected:
            self.on_disconnected()
    
    async def _handle_disconnect(self):
        """Handle disconnection and potential reconnection"""
        if self.websocket:
            self.websocket = None
            
        if self.on_disconnected:
            self.on_disconnected()
        
        if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Reconnecting in {self.reconnect_delay} seconds (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            await asyncio.sleep(self.reconnect_delay)
    
    async def _listen(self):
        """Listen for messages from the WebSocket server"""
        if not self.websocket:
            return
        
        try:
            async for message in self.websocket:
                if not self.running:
                    break
                    
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except ConnectionClosed:
            logger.info("WebSocket connection closed by server")
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {e}")
            raise
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "connected":
            logger.info(f"Connected to workspace: {data.get('workspace', 'general')}")
            
        elif message_type == "file_change":
            logger.info(f"File change received: {data}")
            if self.on_file_change:
                self.on_file_change(data)
                
        elif message_type == "workspace_event":
            logger.info(f"Workspace event received: {data}")
            if self.on_workspace_event:
                self.on_workspace_event(data)
                
        elif message_type == "pong":
            logger.debug("Pong received")
            
        else:
            logger.debug(f"Unknown message type: {message_type}")
    
    async def ping(self):
        """Send a ping to the server"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps({"type": "ping", "timestamp": time.time()}))
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
    
    async def subscribe_to_files(self, file_paths: list[str]):
        """Subscribe to specific file changes"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps({
                    "type": "subscribe_files",
                    "files": file_paths
                }))
            except Exception as e:
                logger.error(f"Error subscribing to files: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.websocket is not None and hasattr(self.websocket, 'state') and self.websocket.state.name == 'OPEN' 