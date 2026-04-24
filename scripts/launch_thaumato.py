#!/usr/bin/env python3
"""
Vesuvius Autoresearch: ThaumatoAnakalyptor Automation Wrapper
Provides a unified CLI for the complex docker-based segmentation pipeline.
"""
import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Run ThaumatoAnakalyptor automatic segmentation pipeline.")
    parser.add_argument("--scroll", type=str, required=True, help="Scroll identifier (e.g., PHerc0332)")
    parser.add_argument("--vol_id", type=str, required=True, help="Canonical volume ID (e.g., 20231027191953)")
    parser.add_argument("--data_dir", type=str, default="local_data", help="Directory containing the scroll volpkg")
    args = parser.parse_args()

    scroll_path = os.path.abspath(os.path.join(args.data_dir, f"{args.scroll}.volpkg"))
    
    print(f"--- ThaumatoAnakalyptor Segmentation: {args.scroll} ---")
    print("WARNING: This pipeline requires ~200GB RAM, 24GB VRAM, and significant disk space.")
    print("To execute, you must first build the docker image (see villa/thaumato-anakalyptor/README.md).")
    
    docker_cmd = [
        "docker", "run", "--gpus", "all", "--shm-size=150g", "-it", "--rm",
        "-v", f"{os.getcwd()}/:/workspace",
        "-v", f"{scroll_path}:/scroll.volpkg",
        "-v", "/tmp/.X11-unix:/tmp/.X11-unix",
        "-e", "DISPLAY=$DISPLAY",
        "thaumato_image"
    ]
    
    print("\nRun this command to start the interactive container:")
    print(" ".join(docker_cmd))
    print("\nInside the container, run:")
    print("python3 ThaumatoAnakalyptor.py")

if __name__ == "__main__":
    main()
