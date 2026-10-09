"""Report masked ink counts on the label-conditioned patch catalog."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset_inspection import inspect_fragment, scan_main


def scan_ink_density(
    uri="local_data/PHercParis2Fr143/surface_volume.zarr",
    labels="local_data/PHercParis2Fr143/inklabels.png",
    mask="local_data/PHercParis2Fr143/mask.png",
    **kwargs,
):
    kwargs.setdefault("samples", 2000)
    return inspect_fragment(uri, labels, mask, require_ink=True, **kwargs)


if __name__ == "__main__":
    scan_main(default_samples=2000, require_ink=True)
