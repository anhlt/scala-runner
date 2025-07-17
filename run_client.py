#!/usr/bin/env python3
"""
Quick start script for Scala Runner Sync Client.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run the Scala Runner Sync Client"""
    client_dir = Path(__file__).parent / "scala_runner_sync_client"
    
    # Check if client directory exists
    if not client_dir.exists():
        print("❌ Client directory not found!")
        print(f"Expected: {client_dir}")
        sys.exit(1)
    
    # Install dependencies if needed
    requirements_file = client_dir / "requirements.txt"
    if requirements_file.exists():
        print("📦 Installing dependencies...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], check=True, capture_output=True)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            print("You may need to install them manually:")
            print(f"pip install -r {requirements_file}")
    
    # Change to client directory
    os.chdir(client_dir)
    
    # Run the client
    print("🚀 Starting Scala Runner Sync Client...")
    print("Use --help for command line options")
    print()
    
    try:
        # Pass through all command line arguments
        cmd = [sys.executable, "-m", "scala_runner_sync_client.main"] + sys.argv[1:]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error running client: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 