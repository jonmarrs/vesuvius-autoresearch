import os
import urllib.request


def download_chunk(bucket_url, chunk_key, output_filename):
    url = f"{bucket_url}/{chunk_key}"
    print(f"Downloading {url} ...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            compressed_data = response.read()
            # The zarr chunks are usually compressed with blosc.
            # However, for simply saving them as binary blobs, we can just save the raw data
            # Or we can let tensorstore handle it later. Let's just save the raw chunk file.
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, "wb") as f:
                f.write(compressed_data)
        print(f"Saved to {output_filename}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


# Base URLs (using the public S3 bucket via https to avoid needing boto3/awscli)
BASE_URL = "https://vesuvius-challenge-open-data.s3.amazonaws.com"


# We need the metadata files for tensorstore to read the local directory as a zarr store
def download_metadata(prefix, out_dir):
    meta_files = [".zarray", ".zgroup", ".zattrs"]
    for mf in meta_files:
        url = f"{BASE_URL}/{prefix}/{mf}"
        out_path = os.path.join(out_dir, mf)
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(response.read())
            print(f"Downloaded metadata: {mf}")
        except Exception as exc:
            print(f"Warning: failed to download metadata {url}: {exc}")


# Scroll 1: PHerc0139 (Training)
# "s3://vesuvius-challenge-open-data/PHerc0139/volumes/20260102150214-2.399um-0.2m-78keV-masked.zarr/0/"
# Scroll 4: PHerc1667 (Validation) - Let's use the one we found earlier
# "s3://vesuvius-challenge-open-data/samples/PHerc1667/volumes/20231117161658-7.910um-53keV-masked.zarr/0/"

# Setup local directories
local_train_dir = "local_data/PHerc0139_chunk/0"
local_val_dir = "local_data/PHerc1667_chunk/0"

os.makedirs(local_train_dir, exist_ok=True)
os.makedirs(local_val_dir, exist_ok=True)

# 1. Download metadata
print("Downloading Training Metadata...")
download_metadata(
    "PHerc0139/volumes/20260102150214-2.399um-0.2m-78keV-masked.zarr",
    "local_data/PHerc0139_chunk",
)
download_metadata(
    "PHerc0139/volumes/20260102150214-2.399um-0.2m-78keV-masked.zarr/0", local_train_dir
)

print("\nDownloading Validation Metadata...")
download_metadata(
    "samples/PHerc1667/volumes/20231117161658-7.910um-53keV-masked.zarr",
    "local_data/PHerc1667_chunk",
)
download_metadata(
    "samples/PHerc1667/volumes/20231117161658-7.910um-53keV-masked.zarr/0",
    local_val_dir,
)

# 2. Download a few chunks (Z/Y/X)
# Zarr chunk files are named like "0/0/0", "0/0/1", etc.
# We'll try to download a small grid, e.g., z=10, y=10..12, x=10..12

print("\nDownloading Training Chunks...")
for y in range(10, 12):
    for x in range(10, 12):
        chunk_key = f"PHerc0139/volumes/20260102150214-2.399um-0.2m-78keV-masked.zarr/0/10/{y}/{x}"
        out_path = os.path.join(local_train_dir, f"10/{y}/{x}")
        download_chunk(BASE_URL, chunk_key, out_path)

print("\nDownloading Validation Chunks...")
for y in range(5, 7):
    for x in range(5, 7):
        chunk_key = f"samples/PHerc1667/volumes/20231117161658-7.910um-53keV-masked.zarr/0/5/{y}/{x}"
        out_path = os.path.join(local_val_dir, f"5/{y}/{x}")
        download_chunk(BASE_URL, chunk_key, out_path)

print("\nDone. Check the local_data directory.")
