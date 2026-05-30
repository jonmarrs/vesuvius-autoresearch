import os

import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
bucket = "vesuvius-challenge-open-data"

# Get all scrolls from root prefix
resp = s3.list_objects_v2(Bucket=bucket, Prefix="", Delimiter="/")
scrolls = []
for obj in resp.get("CommonPrefixes", []):
    prefix = obj["Prefix"]
    # Filter to main scroll/fragment directories
    if (
        prefix.startswith("PHerc")
        and "Cr" not in prefix
        and "Fr" not in prefix
        and "Paris" not in prefix
    ):
        scrolls.append(prefix.strip("/"))

print(f"Found {len(scrolls)} candidate scrolls.")


def download_chunks_for_scroll(scroll_id, target_gb=1.0):
    # First, find a valid volume for this scroll
    volumes_prefix = f"{scroll_id}/volumes/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=volumes_prefix, Delimiter="/")

    valid_volume_prefix = None
    for obj in resp.get("CommonPrefixes", []):
        vol_prefix = obj["Prefix"]
        if vol_prefix.endswith("masked.zarr/"):
            valid_volume_prefix = f"{vol_prefix}0/"
            break

    if not valid_volume_prefix:
        print(
            f"  [{scroll_id}] No masked.zarr volume found in root. Trying samples/..."
        )
        volumes_prefix = f"samples/{scroll_id}/volumes/"
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=volumes_prefix, Delimiter="/")
        for obj in resp.get("CommonPrefixes", []):
            vol_prefix = obj["Prefix"]
            if vol_prefix.endswith("masked.zarr/"):
                valid_volume_prefix = f"{vol_prefix}0/"
                break

    if not valid_volume_prefix:
        print(f"  [{scroll_id}] Skipping: No valid Zarr volume found.")
        return False

    print(f"  [{scroll_id}] Found volume: {valid_volume_prefix}")
    out_dir = f"local_data/{scroll_id}_Large/0/"
    os.makedirs(out_dir, exist_ok=True)

    # Download metadata
    metadata_failures = 0
    for meta in [".zarray", ".zgroup", ".zattrs"]:
        key = f"{valid_volume_prefix}{meta}"
        out_path = os.path.join(out_dir, meta)
        try:
            s3.download_file(bucket, key, out_path)
        except Exception as exc:
            metadata_failures += 1
            print(f"  [{scroll_id}] Warning: failed to download metadata {key}: {exc}")

    # Download chunks up to target size
    target_bytes = target_gb * 1024 * 1024 * 1024
    downloaded_bytes = 0
    count = 0
    chunk_failures = 0

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

            size = obj["Size"]
            try:
                s3.download_file(bucket, key, out_path)
                downloaded_bytes += size
                count += 1
            except Exception as exc:
                chunk_failures += 1
                if chunk_failures <= 5:
                    print(
                        f"  [{scroll_id}] Warning: failed to download chunk {key}: {exc}"
                    )
                elif chunk_failures == 6:
                    print(
                        f"  [{scroll_id}] Warning: suppressing further chunk download failures"
                    )

            if downloaded_bytes >= target_bytes:
                print(
                    f"  [{scroll_id}] Success: Downloaded {downloaded_bytes / 1024 / 1024 / 1024:.2f} GB "
                    f"({count} chunks, metadata_failures={metadata_failures}, chunk_failures={chunk_failures})."
                )
                return True

    if downloaded_bytes > 0:
        print(
            f"  [{scroll_id}] Success (Partial): Downloaded {downloaded_bytes / 1024 / 1024 / 1024:.2f} GB "
            f"({count} chunks, metadata_failures={metadata_failures}, chunk_failures={chunk_failures})."
        )
        return True
    else:
        print(f"  [{scroll_id}] Failed: No chunks could be downloaded.")
        return False


# Download for all found scrolls
success_count = 0
for s in scrolls:
    if download_chunks_for_scroll(s, target_gb=1.0):
        success_count += 1

print(
    f"\nFinished. Successfully downloaded data for {success_count}/{len(scrolls)} scrolls."
)
