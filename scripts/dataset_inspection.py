"""Strict local sample inspection, separate from training and model evaluation."""

import argparse
import hashlib
import json
import sys
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import torch

from scripts.candidate_artifacts import integer
from scripts.export_for_production import sha256_file
from scripts.labeling.label_artifacts import volume
from scripts.pseudo_label_artifacts import MAX_LABEL_PIXELS, read_png
from vesuvius_autoresearch.core.checkpoint_tools import validate_batch

MAX_SAMPLES = 10000
MAX_PATCH_VOXELS = 64**3


def sample_limit(value):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("samples must be a positive integer")
    count = integer(value, "samples", 1)
    if count > MAX_SAMPLES:
        raise ValueError(f"samples must not exceed {MAX_SAMPLES}")
    return count


def unchanged_inputs(metadata):
    for path, digest in metadata["input_sha256"].items():
        if sha256_file(path) != digest:
            raise ValueError(
                "an inspection mask or label changed while reading samples"
            )


@contextmanager
def inspection_dataset(
    uri,
    labels,
    mask,
    *,
    patch_size=64,
    num_layers=16,
    require_ink=False,
    max_pixels=MAX_LABEL_PIXELS,
):
    """Validate geometry before building the existing dataset with private caches."""
    size, layers = (
        integer(patch_size, "patch_size", 1),
        integer(num_layers, "num_layers", 1),
    )
    limit = integer(max_pixels, "max_pixels", 1)
    if size * size * layers > MAX_PATCH_VOXELS:
        raise ValueError(
            f"requested CT patch exceeds {MAX_PATCH_VOXELS} voxels; reduce patch size or depth"
        )
    uri, labels, mask = (Path(path).resolve() for path in (uri, labels, mask))
    _, ct = volume(uri)
    if ct.shape[1] * ct.shape[2] > limit:
        raise ValueError(
            "volume plane exceeds max_pixels; use an explicit bounded crop"
        )
    if ct.shape[0] < layers or min(ct.shape[1:]) < size:
        raise ValueError("volume cannot provide the requested patch and depth")
    if ct.dtype not in (np.dtype("uint8"), np.dtype("uint16")) and ct.dtype.kind != "f":
        raise ValueError("inspection supports uint8, uint16, or normalized floating CT")
    metadata = {
        "uri": str(uri),
        "labels": str(labels),
        "mask": str(mask),
        "shape_zyx": list(ct.shape),
        "input_sha256": {str(path): sha256_file(path) for path in (labels, mask)},
        "patch_size": size,
        "num_layers": layers,
        "seed": 7,
        "jitter": False,
        "require_ink": require_ink,
        "strict_reads": True,
        "use_ridges": False,
        "max_pixels": limit,
        "max_patch_voxels": MAX_PATCH_VOXELS,
        "ct_content_hashed": False,
    }
    read_png(labels, kind="binary", shape=ct.shape[1:], max_pixels=limit)
    region = read_png(mask, kind="binary", shape=ct.shape[1:], max_pixels=limit)
    if not region.any():
        raise ValueError("inspection mask must contain positive pixels")
    with (
        redirect_stdout(sys.stderr),
        TemporaryDirectory(prefix="vesuvius-inspect-") as cache,
    ):
        from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

        dataset = VesuviusLabeledDataset(
            str(uri),
            str(labels),
            str(mask),
            size,
            layers,
            seed=7,
            cache_dir=cache,
            require_ink=require_ink,
            jitter=False,
            strict_reads=True,
            use_ridges=False,
            use_lasagna=False,
        )
        yield dataset, metadata
        unchanged_inputs(metadata)
        _, current = volume(uri)
        if tuple(current.shape) != tuple(metadata["shape_zyx"]):
            raise ValueError("volume shape changed while inspecting")


def validated_samples(dataset, count):
    """Read first catalog entries, report their real masks and unjittered origins."""
    requested = sample_limit(count)
    if getattr(dataset, "jitter", True) or not getattr(dataset, "strict_reads", False):
        raise ValueError("inspection requires unjittered samples and strict reads")
    actual = min(requested, len(dataset))
    if not actual:
        raise ValueError("dataset has no available samples")
    size, layers = dataset.patch_size, dataset.num_layers
    settings = {"patch_size": size, "num_layers": layers, "use_ridges": False}
    for index in range(actual):
        coordinate = np.asarray(dataset.valid_coords[index])
        if coordinate.shape != (2,) or coordinate.dtype.kind not in "iu":
            raise ValueError("catalog coordinates must be integer y/x pairs")
        y, x = (int(value) for value in coordinate)
        if not (
            0 <= y <= dataset.shape[1] - size and 0 <= x <= dataset.shape[2] - size
        ):
            raise ValueError("catalog patch exceeds volume bounds")
        region = np.asarray(dataset.mask[y : y + size, x : x + size])
        if (
            region.shape != (size, size)
            or not np.isin(region, [0, 1]).all()
            or not region.any()
        ):
            raise ValueError(
                "catalog patch must contain aligned binary requested pixels"
            )
        sample = dataset[index]
        if not isinstance(sample, (tuple, list)) or len(sample) != 3:
            raise ValueError(
                "dataset sample must contain CT, ink target, and fiber target"
            )
        ct, target, _ = sample
        if not isinstance(ct, torch.Tensor):
            raise ValueError("CT sample must be a tensor")
        validate_batch(ct.unsqueeze(0), settings)
        if not ((ct >= 0) & (ct <= 1)).all():
            raise ValueError("CT sample must be normalized to [0,1]")
        if (
            not isinstance(target, torch.Tensor)
            or tuple(target.shape) != (size, size)
            or not torch.isfinite(target).all()
            or not ((target == 0) | (target == 1)).all()
        ):
            raise ValueError("ink target must be aligned, finite, and binary")
        yield {
            "index": index,
            "coordinate_yx": [y, x],
            "ct": ct.detach().cpu().numpy(),
            "target": target.detach().cpu().numpy().astype(bool),
            "region": region.astype(bool),
        }


def summarize_samples(records, metadata, count, available):
    densities, means, coords, outside = [], [], [], []
    for sample in records:
        region = sample["region"]
        densities.append(int((sample["target"] & region).sum()))
        means.append(float(sample["ct"][0][:, region].mean()))
        coords.append(sample["coordinate_yx"])
        outside.append(int((~region).sum()))
    return {
        "schema": "dataset-inspection-v1",
        "status": "INSPECTED",
        "scope": "catalog_sample_statistics",
        **metadata,
        "requested_samples": sample_limit(count),
        "available_samples": available,
        "sampled_samples": len(densities),
        "selection": "first catalog entries; not a population estimate",
        "coordinates_preview_yx": coords[:10],
        "coordinates_sha256": hashlib.sha256(
            json.dumps(coords, separators=(",", ":")).encode()
        ).hexdigest(),
        "samples_with_ink_in_mask": sum(value > 0 for value in densities),
        "samples_with_masked_ct_mean_above_0_01": sum(value > 0.01 for value in means),
        "masked_ink_pixels": {
            "min": min(densities),
            "mean": float(np.mean(densities)),
            "max": max(densities),
            "above_10": sum(value > 10 for value in densities),
            "above_50": sum(value > 50 for value in densities),
            "above_100": sum(value > 100 for value in densities),
        },
        "samples_with_context_outside_mask": sum(value > 0 for value in outside),
        "context_yx_pixels_outside_mask_across_samples": sum(outside),
        "full_volume_statistics": False,
        "patch_independence_verified": False,
    }


def sample_report(dataset, metadata, count):
    return summarize_samples(
        validated_samples(dataset, count), metadata, count, len(dataset)
    )


def inspect_fragment(
    uri,
    labels,
    mask,
    *,
    samples=1000,
    patch_size=64,
    num_layers=16,
    require_ink=False,
    max_pixels=MAX_LABEL_PIXELS,
):
    sample_limit(samples)
    with inspection_dataset(
        uri,
        labels,
        mask,
        patch_size=patch_size,
        num_layers=num_layers,
        require_ink=require_ink,
        max_pixels=max_pixels,
    ) as (dataset, metadata):
        result = sample_report(dataset, metadata, samples)
    return result


def scan_main(*, default_samples=1000, require_ink=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--uri", required=True, help="local CT Zarr array or explicit level-0 group"
    )
    parser.add_argument("--labels", required=True, help="aligned binary ink PNG")
    parser.add_argument("--mask", required=True, help="aligned binary region PNG")
    parser.add_argument(
        "--samples",
        type=int,
        default=default_samples,
        help="inspect up to this many catalog entries",
    )
    parser.add_argument("--patch-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=16)
    parser.add_argument("--max-pixels", type=int, default=MAX_LABEL_PIXELS)
    args = parser.parse_args()
    try:
        result = inspect_fragment(
            args.uri,
            args.labels,
            args.mask,
            samples=args.samples,
            patch_size=args.patch_size,
            num_layers=args.num_layers,
            require_ink=require_ink,
            max_pixels=args.max_pixels,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"dataset inspection: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
