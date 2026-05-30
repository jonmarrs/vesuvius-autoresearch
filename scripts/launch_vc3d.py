#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Volume Cartographer (VC3D) Docker Launcher
Provides a simple CLI to launch the official VC3D environment.
"""

import os
import subprocess
import sys


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
        "xhost",
        "+local:docker",
        "&&",
        "sudo",
        "docker",
        "run",
        "-it",
        "--rm",
        "-v",
        f"{WORKSPACE_DIR}:{WORKSPACE_DIR}",
        "-v",
        "/tmp/.X11-unix:/tmp/.X11-unix",
        "-e",
        f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
        "-e",
        "QT_QPA_PLATFORM=xcb",
        "-e",
        "QT_X11_NO_MITSHM=1",
        DOCKER_IMAGE,
    ]

    print("\nRun this command to start the interactive container:")
    print(" ".join(docker_cmd))
    print("\nWorkflow to review Autoresearch Fiber/Ink predictions in VC3D:")
    print(
        "1. Inside the container, open your target surface (e.g. using a .volpkg or OME-Zarr volume)."
    )
    print("2. In the VC3D GUI, go to File -> Open Overlay (or Layer -> Add).")
    print("3. Navigate to the 'predictions/' directory.")
    print("4. Load both '*_ink.zarr' and '*_fiber.zarr' as surface overlays.")
    print(
        "5. Adjust opacity or toggle visibility to verify that ink predictions align with papyrus fiber structures."
    )


if __name__ == "__main__":
    main()
