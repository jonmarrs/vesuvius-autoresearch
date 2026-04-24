#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Crackle Viewer Wrapper
Provides a simple CLI to launch the Crackle Viewer GUI for inspecting ink predictions.
"""
import os
import sys
import subprocess

def main():
    crackle_dir = os.path.abspath("villa/crackle-viewer")
    
    if not os.path.exists(crackle_dir):
        print(f"Error: Crackle Viewer directory not found at {crackle_dir}")
        sys.exit(1)
        
    print(f"--- Launching Crackle Viewer ---")
    print("Please use the GUI to open your generated PNG/TIFF predictions located in predictions/.")
    
    cmd = [sys.executable, "view_gui.py"]
    try:
        subprocess.run(cmd, cwd=crackle_dir, check=True)
    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print(f"Failed to launch Crackle Viewer: {e}")

if __name__ == "__main__":
    main()
