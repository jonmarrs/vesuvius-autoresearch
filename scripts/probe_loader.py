from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def probe_data():
    uri = "local_data/PHercParis2Fr47/surface_volume.zarr"
    labels = "local_data/PHercParis2Fr47/inklabels.png"
    mask = "local_data/PHercParis2Fr47/mask.png"

    ds = VesuviusLabeledDataset(uri, labels, mask, patch_size=64, num_layers=16)

    print(f"Dataset size: {len(ds)}")

    # Get a few samples
    for i in range(5):
        x, target = ds[i]
        print(f"Sample {i}:")
        print(
            f"  x shape: {x.shape}, max: {x.max():.4f}, min: {x.min():.4f}, mean: {x.mean():.4f}"
        )
        if target is not None:
            print(
                f"  target shape: {target.shape}, max: {target.max():.4f}, min: {target.min():.4f}, sum: {target.sum():.4f}"
            )


if __name__ == "__main__":
    probe_data()
