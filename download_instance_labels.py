import os
import requests
import zipfile
from tqdm import tqdm

URL = "https://dl.ash2txt.org/full-scrolls/Scroll1/PHercParis4.volpkg/volumetric-instance-labels/instance-labels-harmonized.zip"
OUT_DIR = "local_data/volumetric-instance-labels"
ZIP_PATH = os.path.join(OUT_DIR, "instance-labels-harmonized.zip")

def download_file(url, path):
    print(f"Downloading {url} to {path}...")
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1 MB
    
    with open(path, 'wb') as f, tqdm(
        total=total_size, unit='iB', unit_scale=True, desc="Download"
    ) as progress_bar:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(ZIP_PATH):
        download_file(URL, ZIP_PATH)
    else:
        print(f"Zip already exists at {ZIP_PATH}")

    print("Extracting...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(OUT_DIR)
    
    print(f"Success! Data extracted to {OUT_DIR}")

if __name__ == "__main__":
    main()
