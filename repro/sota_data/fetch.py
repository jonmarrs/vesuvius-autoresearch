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
    entries = {
        e["name"].rstrip("/").rsplit("/", 1)[-1]: e for e in fs.ls(src, detail=True)
    }
    if entries.get("layers", {}).get("type") != "directory":
        raise ValueError(f"{src}: no layers/ to fetch")
    # Named as convert's globs (*inklabels*, *mask*, case-sensitive) will find them.
    wanted = [n for n in entries if "inklabels" in n or "mask" in n]
    for name in wanted:
        if entries[name].get("type") != "file":
            raise ValueError(f"{src}/{name} is not a file; convert reads one file")
    os.makedirs(out_dir, exist_ok=True)
    # The trailing "/" copies layers/'s contents into out_dir/layers. Until 2026-10-16
    # the whole segment was copied into the existing out_dir, which fsspec nests as
    # out_dir/<segment>/, so the layers were not where the returned path said.
    fs.get(entries["layers"]["name"].rstrip("/") + "/", os.path.join(out_dir, "layers"),
           recursive=True)
    for name in wanted:
        fs.get(entries[name]["name"], os.path.join(out_dir, name))
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python -m repro.sota_data.fetch <s3_seg_prefix> <out_dir>")
    fetch_segment(sys.argv[1], sys.argv[2])
    print("fetched to", sys.argv[2])
