# repro/sota_data/fetch.py
"""Download one segment's layers + ink label + mask from the open bucket to local disk.
Operational. Anonymous S3."""
import os
import sys

import s3fs

BUCKET = "vesuvius-challenge-open-data"


def fetch_segment(s3_seg_prefix, out_dir):
    """s3_seg_prefix: bucket-relative path to the segment dir (contains layers/ + label)."""
    fs = s3fs.S3FileSystem(anon=True)
    os.makedirs(out_dir, exist_ok=True)
    src = f"{BUCKET}/{s3_seg_prefix}".rstrip("/")
    fs.get(src, out_dir, recursive=True)
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python -m repro.sota_data.fetch <s3_seg_prefix> <out_dir>")
    fetch_segment(sys.argv[1], sys.argv[2])
    print("fetched to", sys.argv[2])
