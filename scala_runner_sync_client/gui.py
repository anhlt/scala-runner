"""
Prompt Toolkit GUI interface for Scala Runner Sync Client.
"""

import asyncio
import logging
import difflib
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import (
    Frame, Label, Button, TextArea, RadioList, CheckboxList, 
    ProgressBar, Dialog, SearchToolbar
)
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import message_dialog, input_dialog, yes_no_dialog
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import Condition
from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text

from .websocket_client import WebSocketClient
from .api_client import ScalaRunnerAPIClient
from .file_sync import FileSynchronizer

logger = logging.getLogger(__name__)

class ScalaRunnerGUI:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.api_client = ScalaRunnerAPIClient(server_url)
        self.websocket_client = None
        self.file_sync = None
        self.current_workspace = None
        self.workspaces = []
        self.file_tree = {}
        self.selected_file = None
        self.file_content = ""
        self.notifications = []
        self.changes_preview = []
        
        # UI Components
        self.workspace_list = None
        self.file_browser = None
        self.file_viewer = None
        self.notification_area = None
        self.status_bar = None
        self.changes_panel = None
        
        # Console for rich text rendering
        self.console = Console(width=120, legacy_windows=False)
        
        self._setup_ui()
        self._setup_key_bindings()
        
    def _setup_ui(self):
        """Setup the UI layout"""
        # Workspace selection
        self.workspace_list = RadioList(values=[])
        workspace_frame = Frame(
            HSplit([
                Label(text="Workspaces:", style="bold"),
                self.workspace_list,
                HSplit([
                    Button(text="Connect", handler=self._connect_workspace),
                    Button(text="Refresh", handler=self._refresh_workspaces),
                    Button(text="Create", handler=self._create_workspace),
                ])
            ]),
            title="Workspaces"
        )
        
        # File browser
        self.file_browser = RadioList(values=[])
        file_browser_frame = Frame(
            HSplit([
                Label(text="Files:", style="bold"),
                self.file_browser,
                HSplit([
                    Button(text="Open", handler=self._open_file),
                    Button(text="Sync", handler=self._sync_file),
                    Button(text="Update", handler=self._update_file),
                ])
            ]),
            title="File Browser"
        )
        
        # File viewer/editor
        self.file_viewer = TextArea(
            text="Select a file to view/edit...",
            read_only=False,
            wrap_lines=True,
            scrollbar=True
        )
        file_viewer_frame = Frame(self.file_viewer, title="File Content")
        
        # Changes preview
        self.changes_panel = TextArea(
            text="Changes will appear here...",
            read_only=True,
            wrap_lines=True,
            scrollbar=True
        )
        changes_frame = Frame(self.changes_panel, title="Changes Preview")
        
        # Notifications area
        self.notification_area = TextArea(
            text="Notifications will appear here...",
            read_only=True,
            wrap_lines=True,
            scrollbar=True,
            height=8
        )
        notifications_frame = Frame(self.notification_area, title="Notifications")
        
        # Status bar
        self.status_bar = FormattedTextControl(text="Ready")
        status_window = Window(content=self.status_bar, height=1, style="reverse")
        
        # Main layout
        left_panel = VSplit([
            workspace_frame,
            file_browser_frame
        ], width=50)
        
        right_panel = HSplit([
            file_viewer_frame,
            changes_frame,
        ])
        
        main_content = VSplit([
            left_panel,
            right_panel
        ])
        
        root_container = HSplit([
            main_content,
            notifications_frame,
            status_window
        ])
        
        self.layout = Layout(root_container)
        
    def _setup_key_bindings(self):
        """Setup key bindings"""
        self.kb = KeyBindings()
        
        @self.kb.add('c-c')
        def _(event):
            """Exit application"""
            event.app.exit()
        
        @self.kb.add('c-r')
        def _(event):
            """Refresh workspaces"""
            self._refresh_workspaces()
        
        @self.kb.add('c-o')
        def _(event):
            """Open selected file"""
            self._open_file()
        
        @self.kb.add('c-s')
        def _(event):
            """Save/update current file"""
            self._update_file()
        
        @self.kb.add('c-n')
        def _(event):
            """Create new file"""
            self._create_file()
        
        @self.kb.add('f5')
        def _(event):
            """Sync with server"""
            self._sync_file()
    
    async def start(self):
        """Start the GUI application"""
        # Create the application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True
        )
        
        # Load initial data
        await self._refresh_workspaces()
        self._update_status("Application started. Use Ctrl+C to exit.")
        
        # Run the application
        await self.app.run_async()
    
    async def _refresh_workspaces(self):
        """Refresh workspace list"""
        try:
            self._update_status("Loading workspaces...")
            self.workspaces = await self.api_client.list_workspaces()
            
            workspace_items = [(ws["name"], ws) for ws in self.workspaces]
            self.workspace_list.values = workspace_items
            
            self._update_status(f"Loaded {len(self.workspaces)} workspaces")
        except Exception as e:
            self._add_notification(f"Error loading workspaces: {str(e)}", "error")
            self._update_status("Error loading workspaces")
    
    async def _connect_workspace(self):
        """Connect to selected workspace"""
        current_value = self.workspace_list.current_value
        if not current_value:
            self._add_notification("No workspace selected", "warning")
            return
        
        workspace_name = current_value["name"]
        self.current_workspace = workspace_name
        
        try:
            # Setup WebSocket connection
            if self.websocket_client:
                await self.websocket_client.disconnect()
            
            self.websocket_client = WebSocketClient(self.server_url, workspace_name)
            self.websocket_client.set_file_change_handler(self._handle_file_change)
            self.websocket_client.set_workspace_event_handler(self._handle_workspace_event)
            self.websocket_client.set_connection_handlers(
                on_connected=lambda: self._add_notification(f"Connected to {workspace_name}", "info"),
                on_disconnected=lambda: self._add_notification(f"Disconnected from {workspace_name}", "warning"),
                on_error=lambda e: self._add_notification(f"WebSocket error: {str(e)}", "error")
            )
            
            # Setup file synchronizer
            self.file_sync = FileSynchronizer(self.api_client, workspace_name)
            
            # Connect WebSocket in background
            asyncio.create_task(self.websocket_client.connect())
            
            # Load file tree
            await self._refresh_file_tree()
            
            self._update_status(f"Connected to workspace: {workspace_name}")
            
        except Exception as e:
            self._add_notification(f"Error connecting to workspace: {str(e)}", "error")
    
    async def _refresh_file_tree(self):
        """Refresh file tree for current workspace"""
        if not self.current_workspace:
            return
        
        try:
            self._update_status("Loading file tree...")
            tree_data = await self.api_client.get_file_tree(self.current_workspace)
            self.file_tree = tree_data.get("tree", {})
            
            # Convert tree to flat list for RadioList
            file_items = self._flatten_tree(self.file_tree)
            self.file_browser.values = file_items
            
            self._update_status(f"Loaded file tree ({len(file_items)} files)")
            
        except Exception as e:
            self._add_notification(f"Error loading file tree: {str(e)}", "error")
    
    def _flatten_tree(self, tree_node, prefix="", items=None):
        """Flatten file tree into list of (display_name, file_path) tuples"""
        if items is None:
            items = []
        
        if tree_node.get("type") == "file":
            display_name = f"{prefix}{tree_node['name']}"
            file_path = tree_node.get("path", tree_node["name"])
            items.append((display_name, file_path))
        elif tree_node.get("type") == "directory":
            children = tree_node.get("children", [])
            for child in children:
                child_prefix = f"{prefix}{tree_node['name']}/" if prefix or tree_node['name'] != '.' else ""
                self._flatten_tree(child, child_prefix, items)
        
        return items
    
    async def _open_file(self):
        """Open selected file"""
        current_value = self.file_browser.current_value
        if not current_value:
            self._add_notification("No file selected", "warning")
            return
        
        file_path = current_value
        self.selected_file = file_path
        
        try:
            self._update_status(f"Loading file: {file_path}")
            file_data = await self.api_client.get_file_content(self.current_workspace, file_path)
            content = file_data.get("content", "")
            
            self.file_content = content
            self.file_viewer.text = content
            
            self._update_status(f"Opened file: {file_path}")
            
        except Exception as e:
            self._add_notification(f"Error opening file {file_path}: {str(e)}", "error")
    
    async def _update_file(self):
        """Update current file on server"""
        if not self.selected_file:
            self._add_notification("No file selected", "warning")
            return
        
        try:
            new_content = self.file_viewer.text
            
            self._update_status(f"Updating file: {self.selected_file}")
            await self.api_client.update_file(self.current_workspace, self.selected_file, new_content)
            
            self.file_content = new_content
            self._update_status(f"Updated file: {self.selected_file}")
            self._add_notification(f"File updated: {self.selected_file}", "success")
            
        except Exception as e:
            self._add_notification(f"Error updating file: {str(e)}", "error")
    
    async def _sync_file(self):
        """Sync current file with server"""
        if not self.file_sync or not self.selected_file:
            self._add_notification("No file selected or sync not available", "warning")
            return
        
        try:
            result = await self.file_sync.sync_file(self.selected_file)
            if result:
                # Show diff if content changed
                server_content = result.get("content", "")
                if server_content != self.file_content:
                    self._show_diff_preview(self.file_content, server_content)
                    self.file_viewer.text = server_content
                    self.file_content = server_content
                    self._add_notification(f"File synced: {self.selected_file}", "success")
                else:
                    self._add_notification(f"File already up to date: {self.selected_file}", "info")
            
        except Exception as e:
            self._add_notification(f"Error syncing file: {str(e)}", "error")
    
    async def _create_workspace(self):
        """Create a new workspace"""
        name = await input_dialog(title="Create Workspace", text="Workspace name:")
        if name:
            try:
                await self.api_client.create_workspace(name)
                self._add_notification(f"Created workspace: {name}", "success")
                await self._refresh_workspaces()
            except Exception as e:
                self._add_notification(f"Error creating workspace: {str(e)}", "error")
    
    async def _create_file(self):
        """Create a new file"""
        if not self.current_workspace:
            self._add_notification("No workspace connected", "warning")
            return
        
        file_path = await input_dialog(title="Create File", text="File path:")
        if file_path:
            try:
                await self.api_client.create_file(self.current_workspace, file_path, "")
                self._add_notification(f"Created file: {file_path}", "success")
                await self._refresh_file_tree()
            except Exception as e:
                self._add_notification(f"Error creating file: {str(e)}", "error")
    
    def _handle_file_change(self, change_data: Dict[str, Any]):
        """Handle file change notification from WebSocket"""
        data = change_data.get("data", {})
        action = data.get("action", "unknown")
        file_path = data.get("file_path", "")
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] {action.title()}: {file_path}"
        
        self._add_notification(message, "info")
        
        # If this is the currently open file, show notification
        if file_path == self.selected_file:
            self._add_notification(f"Current file was {action} on server", "warning")
    
    def _handle_workspace_event(self, event_data: Dict[str, Any]):
        """Handle workspace event notification from WebSocket"""
        event = event_data.get("event", "unknown")
        workspace = event_data.get("workspace", "")
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] Workspace {event}: {workspace}"
        
        self._add_notification(message, "info")
    
    def _show_diff_preview(self, old_content: str, new_content: str):
        """Show diff preview in changes panel"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile="local", tofile="server",
            lineterm=""
        ))
        
        if diff:
            diff_text = "".join(diff)
            self.changes_panel.text = diff_text
        else:
            self.changes_panel.text = "No differences found"
    
    def _add_notification(self, message: str, level: str = "info"):
        """Add notification to the notification area"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗"
        }.get(level, "•")
        
        formatted_message = f"[{timestamp}] {prefix} {message}"
        self.notifications.append(formatted_message)
        
        # Keep only last 50 notifications
        if len(self.notifications) > 50:
            self.notifications = self.notifications[-50:]
        
        # Update notification area
        notification_text = "\n".join(self.notifications[-20:])  # Show last 20
        self.notification_area.text = notification_text
        
        # Auto-scroll to bottom
        self.notification_area.buffer.cursor_position = len(self.notification_area.text)
    
    def _update_status(self, message: str):
        """Update status bar"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_bar.text = f"[{timestamp}] {message}"
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.websocket_client:
            await self.websocket_client.disconnect()
        if self.api_client:
            await self.api_client.close()


# Main entry point
async def main():
    """Main entry point for the GUI application"""
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scala_runner_client.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Get server URL from command line or use default
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    # Create and start GUI
    gui = ScalaRunnerGUI(server_url)
    try:
        await gui.start()
    finally:
        await gui.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 