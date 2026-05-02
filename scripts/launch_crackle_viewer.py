#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Crackle Viewer Wrapper
Provides a simple CLI to launch the Crackle Viewer GUI for inspecting ink predictions.
"""
import os
import sys
import subprocess

def main():
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    crackle_dir = os.path.join(PROJECT_ROOT, "villa/crackle-viewer")
    gui_script = os.path.join(crackle_dir, "view_gui.py")

    if not os.path.exists(gui_script):
        print(f"Error: Crackle Viewer not found at {gui_script}")
        sys.exit(1)

    print("Launching Crackle Viewer...")
    print("Usage: Use 'File -> Open' to load your prediction and base images.")
    
    try:
        # Run using the current virtual environment's python
        cmd = [sys.executable, gui_script]
        subprocess.run(cmd, cwd=crackle_dir, check=True)
    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print(f"Failed to launch Crackle Viewer: {e}")

if __name__ == "__main__":
    main()
