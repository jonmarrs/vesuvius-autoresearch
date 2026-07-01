# repro/sota_data/discover.py
"""List the open Vesuvius data bucket to find Scroll-1 / PHerc Paris 4 segments that have a
surface volume (layers/) and an ink label. Operational: run it, read the output, pick a
target. Anonymous S3, no credentials."""
import sys

import s3fs

BUCKET = "vesuvius-challenge-open-data"


def list_prefix(prefix=""):
    fs = s3fs.S3FileSystem(anon=True)
    path = f"{BUCKET}/{prefix}".rstrip("/")
    return fs.ls(path, detail=False)


def classify(fs, seg_prefix):
    """Return (has_layers, has_ink) for a candidate segment prefix."""
    try:
        entries = fs.ls(seg_prefix, detail=False)
    except Exception:
        return (False, False)
    names = [e.rsplit("/", 1)[-1].lower() for e in entries]
    has_layers = any(n in ("layers", "surface_volume") for n in names)
    has_ink = any("inklabel" in n for n in names)
    return (has_layers, has_ink)


if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    for entry in list_prefix(prefix):
        print(entry)
