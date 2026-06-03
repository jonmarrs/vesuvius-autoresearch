import os
import sys

sys.path.append(os.getcwd())
import argparse

import matplotlib.pyplot as plt

from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def visualize_training_samples(
    uri, label_path, mask_path=None, num_samples=5, patch_size=128, num_layers=12
):
    print("Initializing dataset for visualization...")
    print(f"Volume: {uri}")
    print(f"Labels: {label_path}")

    dataset = VesuviusLabeledDataset(
        volume_uri=uri,
        labels_path=label_path,
        mask_path=mask_path,
        patch_size=patch_size,
        num_layers=num_layers,
    )

    data_iter = iter(dataset)

    os.makedirs("reports/figures/training_samples", exist_ok=True)

    fig, axes = plt.subplots(num_samples, 3, figsize=(15, 4 * num_samples))
    if num_samples == 1:
        axes = [axes]

    print(f"Sampling {num_samples} patches...")

    for i in range(num_samples):
        # Fetch a sample
        vol_patch, label_patch = next(data_iter)

        # vol_patch is [1, Z, H, W]
        # label_patch is [1, 1, H, W]

        vol_np = vol_patch.squeeze().numpy()  # [Z, H, W]
        label_np = label_patch.squeeze().numpy()  # [H, W]

        # 1. Show middle slice of volume
        mid_z = num_layers // 2
        axes[i][0].imshow(vol_np[mid_z], cmap="gray")
        axes[i][0].set_title(f"Sample {i + 1}: Volume Slice (Z={mid_z})")
        axes[i][0].axis("off")

        # 2. Show Label
        axes[i][1].imshow(label_np, cmap="jet")
        axes[i][1].set_title(f"Sample {i + 1}: Ground Truth Ink")
        axes[i][1].axis("off")

        # 3. Show Overlay
        axes[i][2].imshow(vol_np[mid_z], cmap="gray")
        axes[i][2].imshow(label_np, cmap="jet", alpha=0.4)
        axes[i][2].set_title(f"Sample {i + 1}: Overlay")
        axes[i][2].axis("off")

    plt.tight_layout()
    out_path = f"reports/figures/training_samples/samples_{os.path.basename(uri.rstrip('/'))}.png"
    plt.savefig(out_path, dpi=150)
    print(f"Saved training sample visualization to: {out_path}")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize samples from a labeled Vesuvius dataset"
    )
    parser.add_argument(
        "--uri",
        type=str,
        default="local_data/PHercParis2Fr47/surface_volume/",
        help="Path to volume data",
    )
    parser.add_argument(
        "--labels",
        type=str,
        default="local_data/PHercParis2Fr47/inklabels.png",
        help="Path to labels PNG",
    )
    parser.add_argument(
        "--mask",
        type=str,
        default="local_data/PHercParis2Fr47/mask.png",
        help="Path to mask PNG",
    )
    parser.add_argument(
        "--num", type=int, default=5, help="Number of samples to visualize"
    )
    parser.add_argument("--patch_size", type=int, default=128, help="Patch size")
    parser.add_argument("--layers", type=int, default=12, help="Number of layers")

    args = parser.parse_args()

    visualize_training_samples(
        uri=args.uri,
        label_path=args.labels,
        mask_path=args.mask if os.path.exists(args.mask) else None,
        num_samples=args.num,
        patch_size=args.patch_size,
        num_layers=args.layers,
    )
