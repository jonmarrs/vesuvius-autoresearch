#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Volume Cartographer (VC3D) Docker Launcher
Provides a simple CLI to launch the official VC3D environment.
"""
import os
import sys
import subprocess

def main():
    print("Vesuvius Challenge: Volume Cartographer (VC3D) Launcher")
    
    # Configuration
    DOCKER_IMAGE = "ghcr.io/scrollprize/villa/volume-cartographer:edge"
    WORKSPACE_DIR = os.getcwd()
    
    # Check if docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.DEVNULL)
    except Exception:
        print("Error: Docker not found. Please install docker to run VC3D.")
        sys.exit(1)

    print(f"Mounting current workspace: {WORKSPACE_DIR}")
    
    # Prepare docker command
    docker_cmd = [
        "xhost", "+local:docker", "&&",
        "sudo", "docker", "run", "-it", "--rm",
        "-v", f"{WORKSPACE_DIR}:{WORKSPACE_DIR}",
        "-v", "/tmp/.X11-unix:/tmp/.X11-unix",
        "-e", f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
        "-e", "QT_QPA_PLATFORM=xcb",
        "-e", "QT_X11_NO_MITSHM=1",
        DOCKER_IMAGE
    ]
    
    print("\nRun this command to start the interactive container:")
    print(" ".join(docker_cmd))
    print("\nInside the container, navigate to your .volpkg and run 'VC3D'.")

if __name__ == "__main__":
    main()
