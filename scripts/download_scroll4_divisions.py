import json
import math
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://dl.ash2txt.org/full-scrolls/Scroll4/PHerc1667.volpkg/volumes_zarr/20231117161658.zarr/0/"
OUT_BASE = "local_data/PHerc1667_Divisions/"


def get_chunk_list(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8")
            chunks = re.findall(r'href="(\d+)/?"', html)
            return sorted(list(set(chunks)), key=int)
    except Exception:
        return []


def download_file(url, out_path):
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return True
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(out_path, "wb") as f:
                f.write(response.read())
        return True
    except:
        return False


def download_divisions():
    print("--- Processing Scroll 4 (PHerc1667) ---")

    # 1. Download metadata
    print("  Downloading metadata...")
    for meta in [".zarray", ".zgroup", ".zattrs"]:
        download_file(f"{BASE_URL}{meta}", os.path.join(OUT_BASE, "meta", meta))

    # Read .zarray
    with open(os.path.join(OUT_BASE, "meta", ".zarray")) as f:
        zarray = json.load(f)
        shape = zarray["shape"]
        chunks = zarray["chunks"]

    z_max = shape[0]
    z_chunk = chunks[0]
    target_chunks = 512
    grid_size = math.ceil(target_chunks ** (1 / 3))  # ~8

    divisions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    for div in divisions:
        div_name = f"div_{int(div * 100)}"
        print(f"\n  Downloading Division {div_name}...")

        start_z_idx = int((z_max - (grid_size * z_chunk)) * div) // z_chunk
        start_z_idx = max(0, min(start_z_idx, (z_max // z_chunk) - grid_size))

        # Mid points
        mid_y_idx = (shape[1] // chunks[1]) // 2
        mid_x_idx = (shape[2] // chunks[2]) // 2
        start_y_idx = max(0, mid_y_idx - (grid_size // 2))
        start_x_idx = max(0, mid_x_idx - (grid_size // 2))

        out_dir = f"local_data/PHerc1667_Divisions/{div_name}/0/"

        tasks = []
        for z in range(start_z_idx, start_z_idx + grid_size):
            for y in range(start_y_idx, start_y_idx + grid_size):
                for x in range(start_x_idx, start_x_idx + grid_size):
                    url = f"{BASE_URL}{z}/{y}/{x}"
                    path = os.path.join(out_dir, str(z), str(y), str(x))
                    tasks.append((url, path))

        print(f"  Queued {len(tasks)} chunks for {div_name}.")
        downloaded = 0
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(download_file, url, path) for url, path in tasks]
            for i, f in enumerate(futures):
                if f.result():
                    downloaded += 1
                if i % 100 == 0 and i > 0:
                    print(f"    Progress: {i}/{len(tasks)} chunks.")
                    sys.stdout.flush()
        print(f"  Finished {div_name}: {downloaded} chunks.")


if __name__ == "__main__":
    download_divisions()
