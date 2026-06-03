import numpy as np

from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def scan_ink_density():
    uri = "local_data/PHercParis2Fr143/surface_volume.zarr"
    labels = "local_data/PHercParis2Fr143/inklabels.png"
    mask = "local_data/PHercParis2Fr143/mask.png"

    ds = VesuviusLabeledDataset(
        uri, labels, mask, patch_size=64, num_layers=16, require_ink=True
    )

    densities = []
    for i in range(min(2000, len(ds))):
        _, target = ds[i]
        densities.append(target.sum().item())

    densities = np.array(densities)
    print("Ink pixel counts per patch (min 1 pixel):")
    print(f"  Mean: {densities.mean():.1f}")
    print(f"  Max: {densities.max():.1f}")
    print(f"  > 10 pixels: {np.sum(densities > 10)}")
    print(f"  > 50 pixels: {np.sum(densities > 50)}")
    print(f"  > 100 pixels: {np.sum(densities > 100)}")


if __name__ == "__main__":
    scan_ink_density()
