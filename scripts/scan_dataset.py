"""Inspect an explicit training fragment; report counts over actual samples."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset_inspection import inspect_fragment, scan_main


def scan_dataset(
    uri="local_data/PHercParis2Fr47/surface_volume.zarr",
    labels="local_data/PHercParis2Fr47/inklabels.png",
    mask="local_data/PHercParis2Fr47/mask.png",
    **kwargs,
):
    return inspect_fragment(uri, labels, mask, **kwargs)


if __name__ == "__main__":
    scan_main()
