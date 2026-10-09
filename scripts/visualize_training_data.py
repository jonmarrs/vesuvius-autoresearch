"""Plot validated CT/ink samples without losing depth or reading outside inputs."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset_inspection import (
    inspection_dataset,
    sample_limit,
    summarize_samples,
    unchanged_inputs,
    validated_samples,
)
from scripts.labeling.label_artifacts import new_output, publish_new_file
from scripts.pseudo_label_artifacts import MAX_LABEL_PIXELS


def visualize_training_samples(
    uri,
    label_path,
    mask_path=None,
    num_samples=5,
    patch_size=128,
    num_layers=12,
    *,
    output_path=None,
    max_pixels=MAX_LABEL_PIXELS,
):
    count = sample_limit(num_samples)
    if count > 32:
        raise ValueError("visualization supports at most 32 samples")
    if mask_path is None:
        raise ValueError("visualization requires an explicit region mask")
    if output_path is None:
        output_path = (
            Path("reports/figures/training_samples")
            / f"samples_{Path(uri).resolve().parent.name}.png"
        )
    output = new_output(output_path, uri, label_path, mask_path)
    if output.suffix.lower() != ".png":
        raise ValueError("visualization output must be a new .png file")
    with inspection_dataset(
        uri,
        label_path,
        mask_path,
        patch_size=patch_size,
        num_layers=num_layers,
        max_pixels=max_pixels,
    ) as (dataset, metadata):
        records = list(validated_samples(dataset, count))
        report = summarize_samples(records, metadata, count, len(dataset))
    # FigureCanvasAgg avoids a global pyplot backend or persistent figure registry.
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(12, 3.5 * len(records)))
    FigureCanvasAgg(figure)
    axes = figure.subplots(len(records), 3, squeeze=False)
    try:
        for row, sample in enumerate(records):
            ct = sample["ct"][0]
            middle = ct.shape[0] // 2
            plane = ct[middle]
            region = sample["region"]
            labels = np.ma.array(sample["target"].astype(float), mask=~region)
            y, x = sample["coordinate_yx"]
            axes[row, 0].imshow(plane, cmap="gray", vmin=0, vmax=1)
            axes[row, 0].set_title(
                f"Sample {sample['index']} · y={y}, x={x} · middle CT slice"
            )
            axes[row, 1].imshow(labels, cmap="viridis", vmin=0, vmax=1)
            axes[row, 1].set_title("Binary ink labels inside requested mask")
            axes[row, 2].imshow(plane, cmap="gray", vmin=0, vmax=1)
            axes[row, 2].imshow(labels, cmap="viridis", vmin=0, vmax=1, alpha=0.4)
            axes[row, 2].set_title("Requested label overlay")
            for panel in axes[row]:
                panel.axis("off")
        figure.tight_layout()
        with publish_new_file(output, uri, label_path, mask_path) as staging:
            figure.savefig(
                staging,
                dpi=120,
                metadata={"Description": json.dumps(report, allow_nan=False)},
            )
            with Image.open(staging) as image:
                image.verify()
            unchanged_inputs(metadata)
    finally:
        figure.clear()
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--mask", required=True)
    parser.add_argument("--out", required=True, help="new, source-disjoint PNG")
    parser.add_argument(
        "--num", type=int, default=5, help="plot up to this many samples, at most 32"
    )
    parser.add_argument("--patch-size", "--patch_size", type=int, default=64)
    parser.add_argument("--num-layers", "--layers", type=int, default=16)
    parser.add_argument("--max-pixels", type=int, default=MAX_LABEL_PIXELS)
    args = parser.parse_args(argv)
    try:
        output = visualize_training_samples(
            args.uri,
            args.labels,
            args.mask,
            args.num,
            args.patch_size,
            args.num_layers,
            output_path=args.out,
            max_pixels=args.max_pixels,
        )
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"dataset visualization: {exc}\n")
    print(
        json.dumps(
            {
                "status": "VISUALIZED",
                "scope": "catalog_sample_plot",
                "output": str(output),
            },
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
