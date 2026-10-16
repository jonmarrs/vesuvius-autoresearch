# repro/sota_data/fetch.py
"""Download one segment's layers + ink label + mask from the open bucket to local disk.
Operational. Anonymous S3."""
import os
import sys

import s3fs

BUCKET = "vesuvius-challenge-open-data"


def fetch_segment(s3_seg_prefix, out_dir):
    """s3_seg_prefix: bucket-relative path to the segment dir (contains layers/ + label).

    Fetches layers/ and the files named *inklabels* or *mask* into out_dir, the
    directory convert.convert_surface_volume reads. Nothing else: a SOTA segment's
    prefix also holds surface-volume zarrs of hundreds of GB.
    """
    fs = s3fs.S3FileSystem(anon=True)
    src = f"{BUCKET}/{s3_seg_prefix}".rstrip("/")
    entries = {e.rstrip("/").rsplit("/", 1)[-1]: e for e in fs.ls(src, detail=False)}
    if "layers" not in entries:
        raise ValueError(f"{src}: no layers/ to fetch")
    os.makedirs(out_dir, exist_ok=True)
    # The trailing "/" copies layers/'s contents into out_dir/layers. Until 2026-10-16
    # the whole segment was copied into the existing out_dir, which fsspec nests as
    # out_dir/<segment>/, so the layers were not where the returned path said.
    fs.get(entries["layers"].rstrip("/") + "/", os.path.join(out_dir, "layers"),
           recursive=True)
    for name, entry in entries.items():
        if "inklabels" in name.lower() or "mask" in name.lower():
            fs.get(entry, os.path.join(out_dir, name))
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python -m repro.sota_data.fetch <s3_seg_prefix> <out_dir>")
    fetch_segment(sys.argv[1], sys.argv[2])
    print("fetched to", sys.argv[2])
