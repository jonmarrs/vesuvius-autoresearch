#!/usr/bin/env python3
import os
import sys
import subprocess

# This script is located in scripts/ and should be run from the project root.
# Usage: python3 scripts/download_data.py

DATASETS = {
    "1": {
        "name": "PHerc0139 (Scroll 1)",
        "size": "~54 TB (Full) / ~1 GB (Sample)",
        "description": "Full training scroll data. Recommended: Start with the 1GB sample.",
        "script": "scripts/download_large_real_chunks.py"
    },
    "2": {
        "name": "PHerc0172 (Scroll 5)",
        "size": "~1.2 TB (Full) / ~1 GB (Sample)",
        "description": "Standard validation scroll data.",
        "script": "scripts/download_large_real_chunks_val.py"
    },
    "3": {
        "name": "PHerc0332 (Scroll 3)",
        "size": "~4.5 TB (Full) / ~1 GB (Sample)",
        "description": "Intact scroll data.",
        "script": "scripts/download_all_scrolls.py" # This script handles all, but can be filtered
    },
    "4": {
        "name": "PHerc. Paris 2 Fr 47",
        "size": "~104 GB (Compressed) / ~145 GB (Uncompressed)",
        "description": "Fragment 1 full volume from dl.ash2txt.org.",
        "script": "scripts/download_paris2fr47.py"
    },
    "5": {
        "name": "Cross-Sectional 1GB Slices (Scrolls 1, 3, 5)",
        "size": "~33 GB Total",
        "description": "11x 1GB depth divisions per scroll for high-diversity offline training.",
        "script": "scripts/download_scroll_divisions.py"
    },
    "6": {
        "name": "Download 1GB Samples for ALL Public Scrolls",
        "size": "~36 GB Total",
        "description": "Scans the entire S3 bucket and pulls 1GB from every available scroll volume.",
        "script": "scripts/download_all_scrolls.py"
    }
}

def prompt_user(dataset_id):
    ds = DATASETS.get(dataset_id)
    if not ds:
        print("Invalid selection.")
        return False
        
    print(f"\n--- Download Confirmation ---")
    print(f"Dataset:     {ds['name']}")
    print(f"Description: {ds['description']}")
    print(f"Estimated Size: {ds['size']}")
    print(f"\nWARNING: You are about to download a large amount of data.")
    print("Ensure you have enough disk space and check your internet plan for data caps.")
    
    resp = input(f"\nProceed with download? (y/N): ").lower()
    return resp in ['y', 'yes']

def run_script(dataset_id):
    script_path = DATASETS[dataset_id]['script']
    if not os.path.exists(script_path):
        # Check if we are running from within local_data/
        script_path = os.path.join("..", script_path)
        if not os.path.exists(script_path):
            print(f"Error: Could not find script {DATASETS[dataset_id]['script']}")
            return

    print(f"\nLaunching {script_path}...")
    try:
        # We use 'uv run' if available, else standard python
        cmd = ["python3", script_path]
        # For S3 scripts, we usually need boto3
        if "paris" not in script_path:
            cmd = ["uv", "run", "--with", "boto3", "python3", script_path]
            
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nDownload interrupted by user.")
    except subprocess.CalledProcessError as e:
        print(f"\nDownload failed with exit code {e.returncode}")

def main():
    print("========================================")
    print(" Vesuvius Autoresearch Data Downloader  ")
    print("========================================\n")
    print("This tool manages local data for offline training.")
    print("Datasets will be stored in the 'local_data/' directory.\n")
    
    print("Available offline datasets:")
    for k, v in sorted(DATASETS.items()):
        print(f"  [{k}] {v['name']} ({v['size']})")
    print("  [0] Exit")
    
    try:
        choice = input("\nEnter the number of the dataset to download: ")
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
        
    if choice == '0':
        sys.exit(0)
        
    if choice in DATASETS:
        if prompt_user(choice):
            run_script(choice)
        else:
            print("Download cancelled.")
    else:
        print("Invalid selection.")

if __name__ == "__main__":
    main()
