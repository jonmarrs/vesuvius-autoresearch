import os

import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
bucket = "vesuvius-challenge-open-data"


def download_chunks(prefix, out_dir, target_gb=1.0):
    os.makedirs(out_dir, exist_ok=True)

    # Download metadata files
    for meta in [".zarray", ".zgroup", ".zattrs"]:
        key = f"{prefix}{meta}"
        out_path = os.path.join(out_dir, meta)
        try:
            s3.download_file(bucket, key, out_path)
            print(f"Downloaded {key}")
        except Exception as e:
            print(f"Warning: failed to download metadata {key}: {e}")

    target_bytes = target_gb * 1024 * 1024 * 1024
    downloaded_bytes = 0
    count = 0

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if (
                key.endswith(".zarray")
                or key.endswith(".zattrs")
                or key.endswith(".zgroup")
            ):
                continue

            rel_path = key[len(prefix) :]
            out_path = os.path.join(out_dir, rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            size = obj["Size"]
            print(f"Downloading {key} -> {out_path} ({size / 1024 / 1024:.2f} MB)")
            try:
                s3.download_file(bucket, key, out_path)
                downloaded_bytes += size
                count += 1
            except Exception as e:
                print(f"Failed to download {key}: {e}")

            if downloaded_bytes >= target_bytes:
                print(
                    f"\nReached target size ({downloaded_bytes / 1024 / 1024 / 1024:.2f} GB) after {count} chunks."
                )
                return

    print(
        f"\nFinished. Downloaded {downloaded_bytes / 1024 / 1024 / 1024:.2f} GB total ({count} chunks)."
    )


# PHerc1667 (Scroll 4) for Validation - using the path we found
print("\nDownloading ~1GB of PHerc1667 (Scroll 4) validation data...")
download_chunks(
    "samples/PHerc1667/volumes/20231117161658-7.910um-53keV-masked.zarr/0/",
    "local_data/RealScroll_4_Large/0/",
    target_gb=1.0,
)

print("\nDone!")
