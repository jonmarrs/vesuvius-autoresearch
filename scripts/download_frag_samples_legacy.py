import os
import urllib.request
import re
from concurrent.futures import ThreadPoolExecutor
import sys

BASE_URL = "https://dl.ash2txt.org/fragments/"

FRAGS = [
    {"id": "Frag2", "name": "PHercParis2Fr143", "zarr": "54keV_3.24um_.zarr"},
    {"id": "Frag3", "name": "PHercParis1Fr34", "zarr": "54keV_3.24um_.zarr"},
    {"id": "Frag4", "name": "PHercParis1Fr39", "zarr": "54keV_3.24um_.zarr"},
    {"id": "Frag5", "name": "PHerc1667Cr1Fr3", "zarr": "70keV_3.24um_.zarr"},
    {"id": "Frag6", "name": "PHerc51Cr4Fr8", "zarr": "53keV_3.24um_.zarr"},
]

def get_chunk_list(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            # Extract links that are numbers or numbers with slash
            chunks = re.findall(r'href="(\d+)/?"', html)
            return sorted(list(set(chunks)), key=int)
    except Exception as e:
        print(f"Error listing chunks at {url}: {e}")
        return []

def download_file(url, out_path):
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return True
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(out_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        # print(f"Failed to download {url}: {e}")
        return False

def download_sample(frag, target_chunks=300):
    print(f"\n--- Sampling {frag['name']} ({frag['id']}) ---")
    sys.stdout.flush()
    
    prefix_url = f"{BASE_URL}{frag['id']}/{frag['name']}.volpkg/volumes_zarr/{frag['zarr']}/"
    array_url = f"{prefix_url}0/"
    local_dir = f"local_data/{frag['name']}/0/"
    os.makedirs(local_dir, exist_ok=True)
    
    # 1. Download metadata
    print(f"  Downloading metadata for {frag['name']}...")
    sys.stdout.flush()
    # .zgroup and .zattrs are at the Zarr root
    download_file(f"{prefix_url}.zgroup", os.path.join(os.path.dirname(local_dir.rstrip('/')), ".zgroup"))
    download_file(f"{prefix_url}.zattrs", os.path.join(os.path.dirname(local_dir.rstrip('/')), ".zattrs"))
    # .zarray is at the 0 level
    download_file(f"{array_url}.zarray", os.path.join(local_dir, ".zarray"))
        
    # 2. Get chunks.
    print(f"  Finding chunks for {frag['name']}...")
    sys.stdout.flush()
    z_dirs = get_chunk_list(array_url)
    if not z_dirs:
        print(f"  No Z directories found for {frag['name']}.")
        return
        
    # We'll take a sample from the middle Z
    mid_z = z_dirs[len(z_dirs)//2]
    y_url = f"{array_url}{mid_z}/"
    y_dirs = get_chunk_list(y_url)
    if not y_dirs:
        print(f"  No Y directories found for {frag['name']} at Z={mid_z}.")
        return
        
    mid_y = y_dirs[len(y_dirs)//2]
    x_url = f"{array_url}{mid_z}/{mid_y}/"
    x_chunks = get_chunk_list(x_url)
    
    print(f"  Found {len(x_chunks)} chunks in {mid_z}/{mid_y}/. Starting download...")
    sys.stdout.flush()
    
    tasks = []
    # Just download chunks in the middle Z/Y for now, then move to next Y if needed
    for y in y_dirs[len(y_dirs)//2:]:
        curr_x_url = f"{array_url}{mid_z}/{y}/"
        curr_x_chunks = get_chunk_list(curr_x_url)
        for x in curr_x_chunks:
            tasks.append((f"{curr_x_url}{x}", os.path.join(local_dir, mid_z, y, x)))
            if len(tasks) >= target_chunks:
                break
        if len(tasks) >= target_chunks:
            break
            
    print(f"  Queued {len(tasks)} chunks for download.")
    sys.stdout.flush()
    
    downloaded = 0
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(download_file, url, path) for url, path in tasks]
        for i, f in enumerate(futures):
            try:
                if f.result():
                    downloaded += 1
            except Exception as e:
                print(f"    Warning: chunk worker failed: {e}")
            if i % 50 == 0 and i > 0:
                print(f"    Progress: {i}/{len(tasks)} chunks.")
                sys.stdout.flush()
                
    print(f"  Finished {frag['name']}. Downloaded {downloaded} chunks.")
    sys.stdout.flush()

if __name__ == "__main__":
    for frag in FRAGS:
        try:
            download_sample(frag)
        except Exception as e:
            print(f"Error processing {frag['name']}: {e}")
    print("\nAll labeled fragment sampling complete.")
