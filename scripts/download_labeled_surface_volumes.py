import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import sys
import time

# Target layers 16 to 48 (32 layers)
TARGET_LAYERS = range(16, 49) 

DATASETS = [
    {
        "name": "Frag1 (PHercParis2Fr47)",
        "base_url": "https://dl.ash2txt.org/fragments/Frag1/PHercParis2Fr47.volpkg/working/54keV_exposed_surface/surface_volume/",
        "local_dir": "local_data/PHercParis2Fr47/surface_volume/",
        "file_pattern": "{:02d}.tif"
    },
    {
        "name": "Frag2 (PHercParis2Fr143)",
        "base_url": "https://dl.ash2txt.org/fragments/Frag2/PHercParis2Fr143.volpkg/working/54keV_exposed_surface/surface_volume/",
        "local_dir": "local_data/PHercParis2Fr143/surface_volume/",
        "file_pattern": "{:02d}.tif"
    },
    {
        "name": "Frag5 (PHerc1667Cr1Fr3)",
        "base_url": "https://dl.ash2txt.org/fragments/Frag5/PHerc1667Cr1Fr3.volpkg/working/PHerc1667Cr01Fr03_70keV_3.24um/surface_processing/surface_volume/",
        "local_dir": "local_data/PHerc1667Cr1Fr3/surface_volume/",
        "file_pattern": "{:02d}.tif"
    },
    {
        "name": "Scroll1 Monster (20231012184424)",
        "base_url": "https://dl.ash2txt.org/full-scrolls/Scroll1/PHercParis4.volpkg/paths/20231012184424/layers/",
        "local_dir": "local_data/PHercParis4_Monster/layers/",
        "file_pattern": "{:02d}.tif"
    },
    {
        "name": "Scroll4 Segment (20231210132040)",
        "base_url": "https://dl.ash2txt.org/full-scrolls/Scroll4/PHerc1667.volpkg/paths/20231210132040/layers/",
        "local_dir": "local_data/PHerc1667_Labeled/layers/",
        "file_pattern": "{:03d}.tif"
    }
]

def download_file(url, out_path):
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return True
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as response:
            with open(out_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return False

def process_dataset(ds):
    print(f"\n>>> Starting {ds['name']}...")
    sys.stdout.flush()
    tasks = []
    for i in TARGET_LAYERS:
        filename = ds['file_pattern'].format(i)
        url = f"{ds['base_url']}{filename}"
        path = os.path.join(ds['local_dir'], filename)
        tasks.append((url, path))
    
    print(f"    Downloading {len(tasks)} layers for {ds['name']}...")
    sys.stdout.flush()
    
    # Using smaller workers to avoid overwhelming server or bandwidth
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda x: download_file(*x), tasks))
    
    success = sum(results)
    print(f"    Finished {ds['name']}. Success: {success}/{len(tasks)}")
    sys.stdout.flush()

if __name__ == "__main__":
    for ds in DATASETS:
        process_dataset(ds)

# Adding Frag 6
if __name__ == "__main__":
    ds6 = {
        "name": "Frag6 (PHerc51Cr4Fr8)",
        "base_url": "https://dl.ash2txt.org/fragments/Frag6/PHerc51Cr4Fr8.volpkg/working/PHerc0051Cr04Fr08_53keV_3.24um/surface_processing/surface_volume/",
        "local_dir": "local_data/PHerc51Cr4Fr8/surface_volume/",
        "file_pattern": "{:02d}.tif"
    }
    process_dataset(ds6)
