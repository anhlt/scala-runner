#!/usr/bin/env python3
"""
Main entry point for Scala Runner Sync Client.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from .gui import main as gui_main
from .api_client import ScalaRunnerAPIClient
from .websocket_client import WebSocketClient
from .file_sync import FileSynchronizer

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scala_runner_client.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

async def test_connection(server_url: str):
    """Test connection to the server"""
    print(f"Testing connection to {server_url}...")
    
    try:
        async with ScalaRunnerAPIClient(server_url) as client:
            result = await client.ping()
            print(f"✓ Server is reachable: {result}")
            
            workspaces = await client.list_workspaces()
            print(f"✓ Found {len(workspaces)} workspaces")
            for ws in workspaces:
                print(f"  - {ws['name']}")
                
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    return True

async def sync_workspace(server_url: str, workspace_name: str, local_dir: str = None):
    """Sync a workspace to local directory"""
    print(f"Syncing workspace '{workspace_name}' from {server_url}...")
    
    try:
        async with ScalaRunnerAPIClient(server_url) as client:
            local_path = Path(local_dir) if local_dir else None
            sync = FileSynchronizer(client, workspace_name, local_path)
            
            print("Getting sync status...")
            status = await sync.get_sync_status()
            
            print(f"Sync Status:")
            print(f"  In sync: {len(status['in_sync'])} files")
            print(f"  Local changes: {len(status['local_changes'])} files")
            print(f"  Server changes: {len(status['server_changes'])} files")
            print(f"  New on server: {len(status['new_on_server'])} files")
            print(f"  Local only: {len(status['local_only'])} files")
            
            if status['server_changes'] or status['new_on_server']:
                print("\nSyncing changes from server...")
                result = await sync.sync_workspace()
                print(f"✓ Synced {len(result['synced_files'])} files")
                if result['errors']:
                    print(f"✗ {len(result['errors'])} errors occurred")
                    for error in result['errors']:
                        print(f"  - {error['file']}: {error['error']}")
            else:
                print("✓ Workspace is already up to date")
                
    except Exception as e:
        print(f"✗ Sync failed: {e}")
        return False
    
    return True

async def watch_workspace(server_url: str, workspace_name: str):
    """Watch workspace for real-time changes"""
    print(f"Watching workspace '{workspace_name}' for changes...")
    print("Press Ctrl+C to stop watching")
    
    def on_file_change(data):
        change_data = data.get('data', {})
        action = change_data.get('action', 'unknown')
        file_path = change_data.get('file_path', '')
        print(f"📝 {action.title()}: {file_path}")
    
    def on_workspace_event(data):
        event = data.get('event', 'unknown')
        workspace = data.get('workspace', '')
        print(f"🏗️  Workspace {event}: {workspace}")
    
    def on_connected():
        print("✓ Connected to WebSocket")
    
    def on_disconnected():
        print("✗ Disconnected from WebSocket")
    
    def on_error(error):
        print(f"✗ WebSocket error: {error}")
    
    try:
        client = WebSocketClient(server_url, workspace_name)
        client.set_file_change_handler(on_file_change)
        client.set_workspace_event_handler(on_workspace_event)
        client.set_connection_handlers(on_connected, on_disconnected, on_error)
        
        await client.connect()
        
    except KeyboardInterrupt:
        print("\nStopping...")
        await client.disconnect()
    except Exception as e:
        print(f"✗ Watch failed: {e}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Scala Runner Sync Client")
    parser.add_argument(
        "--server", 
        default="http://localhost:8000",
        help="Server URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # GUI command
    gui_parser = subparsers.add_parser("gui", help="Start GUI interface")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test connection to server")
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync workspace to local directory")
    sync_parser.add_argument("workspace", help="Workspace name to sync")
    sync_parser.add_argument(
        "--local-dir", 
        help="Local directory to sync to (default: ./local_workspace/WORKSPACE_NAME)"
    )
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch workspace for real-time changes")
    watch_parser.add_argument("workspace", help="Workspace name to watch")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Handle commands
    if not args.command or args.command == "gui":
        # Start GUI
        asyncio.run(gui_main())
        
    elif args.command == "test":
        success = asyncio.run(test_connection(args.server))
        sys.exit(0 if success else 1)
        
    elif args.command == "sync":
        success = asyncio.run(sync_workspace(args.server, args.workspace, args.local_dir))
        sys.exit(0 if success else 1)
        
    elif args.command == "watch":
        asyncio.run(watch_workspace(args.server, args.workspace))
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 