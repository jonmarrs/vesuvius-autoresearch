#!/usr/bin/env python3
"""
Vesuvius Autoresearch: 3D (Volumetric) Ink Detection Launcher
Wraps Ryan Chesler's 3D-only approach (bypassing unwrapping).
"""


def main():
    print("Vesuvius Autoresearch: 3D Ink Detection Launcher")
    print("Targeting Ryan Chesler's 3D-only approach (bypassing unwrapping).")

    REPO_URL = "https://github.com/ryanchesler/3d-ink-detection.git"
    CLONE_DIR = "villa/3d-ink-detection"

    print(f"\nThis strategy uses the community model located at: {REPO_URL}")
    print("To execute this wildcard strategy for the First Letters Prize:")
    print(f"1. Clone the repository into {CLONE_DIR} (if not already present).")
    print(f"   git clone {REPO_URL} {CLONE_DIR}")
    print("2. Navigate to the directory and follow the setup instructions.")
    print(f"   cd {CLONE_DIR}")
    print("3. Point the inference scripts at our local Scroll 2/3 OME-Zarr data:")
    print("   local_data/PHerc0125_Divisions/")
    print("   local_data/PHerc0332_Divisions/")


if __name__ == "__main__":
    main()
