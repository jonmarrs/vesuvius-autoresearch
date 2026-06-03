import os

import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
bucket = "vesuvius-challenge-open-data"

FRAGS = [
    "PHercParis2Fr143",
    "PHercParis1Fr34",
    "PHercParis1Fr39",
    "PHerc1667Cr1Fr3",
    "PHerc51Cr4Fr8",
]


def download_chunks(scroll_id, target_gb=1.0):
    print(f"Processing {scroll_id}...")
    prefix = f"{scroll_id}/volumes/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    valid_volume_prefix = None
    for obj in resp.get("CommonPrefixes", []):
        vol_prefix = obj["Prefix"]
        if vol_prefix.endswith("masked.zarr/"):
            valid_volume_prefix = f"{vol_prefix}0/"
            break

    if not valid_volume_prefix:
        print(f"  No masked.zarr found for {scroll_id}")
        return False

    out_dir = f"local_data/{scroll_id}_Large/0/"
    os.makedirs(out_dir, exist_ok=True)

    # Download metadata
    for meta in [".zarray", ".zgroup", ".zattrs"]:
        key = f"{valid_volume_prefix}{meta}"
        out_path = os.path.join(out_dir, meta)
        try:
            s3.download_file(bucket, key, out_path)
        except Exception as exc:
            print(f"  Warning: failed to download metadata {key}: {exc}")

    target_bytes = target_gb * 1024 * 1024 * 1024
    downloaded_bytes = 0
    count = 0

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=valid_volume_prefix)

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if (
                key.endswith(".zarray")
                or key.endswith(".zattrs")
                or key.endswith(".zgroup")
            ):
                continue

            rel_path = key[len(valid_volume_prefix) :]
            out_path = os.path.join(out_dir, rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            try:
                s3.download_file(bucket, key, out_path)
                downloaded_bytes += obj["Size"]
                count += 1
            except Exception as exc:
                print(f"  Warning: failed to download {key}: {exc}")

            if downloaded_bytes >= target_bytes:
                print(f"  Downloaded {downloaded_bytes / 1024 / 1024 / 1024:.2f} GB.")
                return True
    return True


def main():
    for f in FRAGS:
        download_chunks(f)


if __name__ == "__main__":
    main()
