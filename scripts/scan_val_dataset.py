"""Inspect an explicit validation fragment; inspection cannot attest to lineage."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset_inspection import inspect_fragment, scan_main


def scan_val_dataset(
    uri="local_data/PHercParis2Fr143/surface_volume.zarr",
    labels="local_data/PHercParis2Fr143/inklabels.png",
    mask="local_data/PHercParis2Fr143/mask.png",
    **kwargs,
):
    return inspect_fragment(uri, labels, mask, **kwargs)


if __name__ == "__main__":
    scan_main()
