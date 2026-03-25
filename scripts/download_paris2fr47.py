import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import time

BASE_URL = "https://dl.ash2txt.org/fragments/Frag1/PHercParis2Fr47.volpkg/volumes_zarr/54keV_3.24um_.zarr/0/"
OUT_DIR = "local_data/PHercParis2Fr47/0/"
os.makedirs(OUT_DIR, exist_ok=True)

def download_chunk(task):
    z, y, x = task
    url = f"{BASE_URL}{z}/{y}/{x}"
    out_path = os.path.join(OUT_DIR, str(z), str(y), str(x))
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return True
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            with open(out_path, 'wb') as f:
                f.write(response.read())
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Empty space chunk
            return True
        return False
    except Exception as e:
        return False

def download_all():
    print("Downloading metadata...")
    for meta in ['.zarray', '.zgroup', '.zattrs']:
        url = f"{BASE_URL}{meta}"
        out_path = os.path.join(OUT_DIR, meta)
        if not os.path.exists(out_path):
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req) as response:
                    with open(out_path, 'wb') as f:
                        f.write(response.read())
            except: pass

    tasks = []
    # Shape is 7219, 1399, 7198 with 128 chunks
    # Max indices: Z=57, Y=11, X=57
    for z in range(57):
        for y in range(11):
            for x in range(57):
                tasks.append((z, y, x))
                
    print(f"Starting download of {len(tasks)} chunks (~104 GB)...")
    success_count = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(download_chunk, tasks)
        for i, res in enumerate(results):
            if res:
                success_count += 1
            if i % 1000 == 0 and i > 0:
                print(f"Progress: {i}/{len(tasks)} chunks processed.")

    print(f"Finished downloading Paris 2 Fr 47. Successfully processed {success_count}/{len(tasks)} chunks.")

if __name__ == '__main__':
    download_all()
