import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from scripts.labeling.label_artifacts import new_output, publish_new_file
from scripts.training.input_paths import validation_label_path

# Local imports
from vesuvius_autoresearch.core.checkpoint_tools import (
    load_tool_checkpoint,
    validate_batch,
    validate_ink_logits,
)
from vesuvius_autoresearch.core.inference import (
    DEPTH_MARGIN,
    depth_band_for,
    positive_integer,
    ridge_depth_context,
)
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def calculate_entropy(probs):
    """Calculate pixel-wise entropy: -p*log(p) - (1-p)*log(1-p)"""
    if not torch.isfinite(probs).all() or not ((probs >= 0) & (probs <= 1)).all():
        raise ValueError("probabilities must be finite in [0,1]")
    # 1e-8 underflows in float16, making endpoint terms 0 * log(0) = NaN.
    # xlogy defines those terms as zero; promote low-precision maps for scoring.
    probs = probs if probs.dtype == torch.float64 else probs.float()
    return -torch.xlogy(probs, probs) - torch.xlogy(1 - probs, 1 - probs)


def minimum_distance(value):
    try:
        result = float(value)
        if (
            isinstance(value, (bool, np.bool_))
            or not math.isfinite(result)
            or result < 0
        ):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("min_distance must be finite and nonnegative") from exc
    return result


def review_catalog(coords):
    catalog = np.asarray(coords)
    if not catalog.size:
        raise ValueError("no patches available for active learning")
    if (
        catalog.ndim != 2
        or catalog.shape[1] != 2
        or not np.issubdtype(catalog.dtype, np.integer)
        or (catalog < 0).any()
    ):
        raise ValueError(
            "patch catalog must contain nonnegative integer y/x coordinates"
        )
    return catalog.copy()


class ActiveLearningSampler:
    """
    Identifies high-uncertainty regions for SAM2-assisted human-in-the-loop cleaning.
    """

    def __init__(self, model, device="cuda", settings=None):
        self.model = model
        self.device = device
        self.settings = settings
        self.model.to(device)
        self.model.eval()

    def sample_uncertain_regions(self, dataloader, n_samples=10, *, min_distance=0):
        positive_integer(n_samples, "n_samples")
        min_distance = minimum_distance(min_distance)
        if getattr(dataloader.dataset, "jitter", False):
            raise ValueError("active-learning coordinates require jitter=False")
        # Coordinates are recovered by position in the evaluated catalog, so
        # sampler, batching, collation and worker delivery must all preserve order.
        # Duck-typed loaders without these attributes remain the caller's contract.
        sampler = getattr(dataloader, "sampler", None)
        if (
            sampler is not None
            and type(sampler) is not torch.utils.data.SequentialSampler
        ):
            raise ValueError(
                "sample_uncertain_regions needs a dataloader in dataset order; "
                "build it with shuffle=False, or the returned coordinates will "
                "not correspond to the patches that were scored."
            )

        batch_sampler = getattr(dataloader, "batch_sampler", None)
        if batch_sampler is not None and (
            type(batch_sampler) is not torch.utils.data.BatchSampler
            or type(batch_sampler.sampler) is not torch.utils.data.SequentialSampler
        ):
            raise ValueError(
                "active learning requires sequential batches in dataset order"
            )
        collate = getattr(dataloader, "collate_fn", None)
        if collate is not None and collate is not torch.utils.data.default_collate:
            raise ValueError(
                "active learning requires default collation to preserve dataset order"
            )
        if not getattr(dataloader, "in_order", True):
            raise ValueError("active learning requires worker batches in dataset order")
        catalog = review_catalog(getattr(dataloader.dataset, "valid_coords", None))
        uncertainties = []

        print(f"Sampling {n_samples} high-uncertainty regions...")

        offset = 0
        with torch.no_grad():
            for x, _, _ in tqdm(dataloader):
                x = x.to(self.device)
                if self.settings is not None:
                    # main() reads training's depth context for ridge models;
                    # validate_batch checks it and gives the model the centre.
                    x = validate_batch(
                        x, self.settings, buffered=bool(self.settings["use_ridges"])
                    )
                if (
                    x.ndim != 5
                    or x.shape[0] < 1
                    or not x.is_floating_point()
                    or not torch.isfinite(x).all()
                ):
                    raise ValueError(
                        "input must be a finite floating-point B/C/Z/H/W tensor"
                    )
                if offset + len(x) > len(catalog):
                    raise ValueError(
                        "loader emitted more patches than the patch catalog"
                    )

                # Ink logits only. The QC head is trained to predict the patch's
                # mean fiber target (train.py's loss_qc), not the model's
                # confidence, so 1 - sigmoid(qc) ranked fiber-poor patches as
                # uncertain.
                outputs = self.model(x)
                out_ink = outputs[0] if isinstance(outputs, tuple) else outputs
                validate_ink_logits(out_ink, x)
                probs = torch.sigmoid(out_ink)

                # Prediction entropy (ambiguity); out_ink is [B, 1, H, W].
                score = calculate_entropy(probs).mean(dim=tuple(range(1, probs.ndim)))

                uncertainties.append(score.cpu().numpy())

                offset += len(x)

        if not uncertainties:
            raise ValueError("no patches available for active learning")
        uncertainties = np.concatenate(uncertainties)
        if not np.isfinite(uncertainties).all():
            raise ValueError("uncertainty scores must be finite")
        if not np.array_equal(np.asarray(dataloader.dataset.valid_coords), catalog):
            raise ValueError("patch catalog changed during scoring")

        # Stable descending scores: ties retain evaluated catalog order.
        ranked = np.argsort(-uncertainties, kind="stable")
        selected = []
        positions = []
        for index in ranked:
            y, x = map(int, catalog[index])
            if min_distance and any(
                math.hypot(y - previous_y, x - previous_x) < min_distance
                for previous_y, previous_x in positions
            ):
                continue
            selected.append(index)
            positions.append((y, x))
            if len(selected) == n_samples:
                break
        return catalog[selected], uncertainties[selected]


def identify_uncertain_patches(probs, threshold=0.2):
    """
    Identifies high-entropy (uncertain) regions in a probability map.
    probs: (H, W) or (C, H, W) tensor
    """
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("uncertainty threshold must be finite in [0,1]")
    if isinstance(probs, np.ndarray):
        probs = torch.from_numpy(probs)

    entropy = calculate_entropy(probs)
    if entropy.dim() == 3:
        entropy = entropy.mean(dim=0)

    # Normalize entropy to [0, 1]
    max_entropy = -0.5 * np.log(0.5) - (1 - 0.5) * np.log(1 - 0.5)
    entropy /= max_entropy

    return (entropy > threshold).float()


def export_for_proofreader(mask, output_path):
    """
    Exports a binary mask to a Zarr volume for the proofreader tool.
    """
    import zarr

    if isinstance(mask, torch.Tensor):
        mask = mask.cpu().numpy()

    # Ensure 3D [Z, H, W]
    if mask.ndim == 2:
        mask = mask[np.newaxis, ...]

    # If 4D [C, Z, H, W], take first channel
    if mask.ndim == 4:
        mask = mask[0]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    z = zarr.open(
        output_path, mode="w", shape=mask.shape, chunks=(1, 64, 64), dtype="f4"
    )
    z[:] = mask
    print(f"Exported uncertainty mask for proofreading: {output_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Active Learning Sampler for Vesuvius Autoresearch"
    )
    parser.add_argument(
        "--checkpoint", type=str, required=True, help="Path to best_model.pt"
    )
    parser.add_argument(
        "--volume", type=str, required=True, help="URI to the Zarr volume"
    )
    parser.add_argument(
        "--labels",
        type=str,
        default=None,
        help="Optional path to labels (if not in volume dir)",
    )
    parser.add_argument(
        "--n_samples",
        "--n-samples",
        type=int,
        default=20,
        help="Number of uncertain patches to sample",
    )
    parser.add_argument(
        "--patches_json",
        "--patches-json",
        type=str,
        default=None,
        help="Path to pre-computed optimal patches.json (from vesuvius.find_patches) to override runtime dataset scanning.",
    )
    parser.add_argument(
        "--min-distance",
        type=float,
        default=0,
        help="Minimum Euclidean distance between selected patch centers in source pixels (default: 0).",
    )
    parser.add_argument(
        "--max-eval-patches",
        type=int,
        default=5000,
        help="Maximum catalog patches to score, from 1 to 5000 (default: 5000).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="New review queue JSON path (default: a timestamped file under reports/).",
    )
    args = parser.parse_args(argv)
    positive_integer(args.n_samples, "n_samples")
    distance = minimum_distance(args.min_distance)
    positive_integer(args.max_eval_patches, "max_eval_patches")
    if args.max_eval_patches > 5000:
        raise ValueError("max_eval_patches must not exceed 5000")
    if args.patches_json and not os.path.isfile(args.patches_json):
        raise FileNotFoundError(args.patches_json)

    labels_path = args.labels or validation_label_path(args.volume)
    if (
        not args.labels
        and not os.path.exists(labels_path)
        and "surface_volume.zarr" in args.volume
    ):
        fragment = Path(args.volume.rstrip("/")).parent.name
        labels_path = validation_label_path(
            f"local_data/{fragment}/surface_volume.zarr"
        )
    sources = [args.checkpoint, labels_path]
    volume_uri = urlsplit(args.volume)
    if os.path.exists(args.volume) or not volume_uri.scheme:
        sources.append(args.volume)
    elif volume_uri.scheme == "file":
        if volume_uri.netloc not in {"", "localhost"}:
            raise ValueError("file URI must refer to the local host")
        sources.append(unquote(volume_uri.path))
    if args.patches_json:
        sources.append(args.patches_json)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = new_output(
        args.output or f"reports/active_learning_queue_{stamp}.json", *sources
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Active Learning Sampler: Running on {device}")

    # 1. Load Checkpoint Metadata
    model, arch_kwargs, chk = load_tool_checkpoint(args.checkpoint, device)

    sampler = ActiveLearningSampler(model, device=device, settings=arch_kwargs)

    # 2. Setup Dataset
    print(f"Using labels from: {labels_path}")

    depth_band = depth_band_for(chk["config"], args.volume)
    dataset = VesuviusLabeledDataset(
        args.volume,
        labels_path,
        patch_size=arch_kwargs["patch_size"],
        # Ridges over training's depth context; centre_window crops the window.
        num_layers=arch_kwargs["num_layers"]
        + (2 * DEPTH_MARGIN if arch_kwargs["use_ridges"] else 0),
        use_ridges=arch_kwargs["use_ridges"],
        ridge_sigma=arch_kwargs["ridge_sigma"],
        require_ink=False,
        jitter=False,
        strict_reads=True,
        patches_json=args.patches_json,
        # The slices the checkpoint was trained on, on its own volumes (None:
        # the whole depth; see depth_band_for); the context margin applies only
        # to ridge models' reads.
        depth_band=depth_band,
        depth_margin=DEPTH_MARGIN if arch_kwargs["use_ridges"] else 0,
    )

    catalog = review_catalog(dataset.valid_coords)
    size = arch_kwargs["patch_size"]
    if (catalog[:, 0] > dataset.shape[1] - size).any() or (
        catalog[:, 1] > dataset.shape[2] - size
    ).any():
        raise ValueError(
            "patch catalog must contain nonempty in-bounds integer y/x coordinates"
        )

    all_coords = catalog

    max_eval_patches = args.max_eval_patches
    if len(all_coords) > max_eval_patches:
        print(
            f"Subsampling {max_eval_patches} patches from {len(all_coords)} total valid patches..."
        )
        idx = np.random.default_rng(42).choice(
            len(all_coords), max_eval_patches, replace=False
        )
        dataset.valid_coords = all_coords[np.sort(idx)]

    dataloader = DataLoader(dataset, batch_size=8, shuffle=False)

    # 3. Sample Uncertain Regions
    coords, scores = sampler.sample_uncertain_regions(
        dataloader, n_samples=args.n_samples, min_distance=distance
    )

    # 4. Export Review Queue
    queue = []
    for i in range(len(coords)):
        y, x = coords[i]
        queue.append(
            {
                "rank": i + 1,
                "y_x": [int(y), int(x)],
                "uncertainty_score": float(scores[i]),
                "status": "pending_manual_review",
            }
        )

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checkpoint": args.checkpoint,
        "volume": args.volume,
        "labels": labels_path,
        "inference_settings": arch_kwargs,
        # Was 0.7 * entropy + 0.3 * (1 - sigmoid(qc)) before 2026-10-13.
        "uncertainty_score_definition": "mean prediction entropy",
        "ridge_depth_context": ridge_depth_context(arch_kwargs["use_ridges"]),
        "depth_band": depth_band,
        "selection": {
            "method": "descending_entropy_with_greedy_minimum_distance",
            "score_unit": "nats",
            "tie_break": "evaluated catalog order",
            "min_distance_pixels": distance,
            "requested_samples": args.n_samples,
            "returned_samples": len(queue),
            "catalog_patch_count": len(all_coords),
            "evaluated_patch_count": len(dataset.valid_coords),
            "max_eval_patches": max_eval_patches,
            "subsample_seed": 42 if len(all_coords) > max_eval_patches else None,
        },
        "queue": queue,
    }
    with publish_new_file(output, *sources) as staging:
        with staging.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, allow_nan=False)

    print(f"\nExported {len(queue)} of {args.n_samples} requested patches to: {output}")
    print(
        "Queue entries are suggestions for manual inspection, not accuracy measurements."
    )
    return output


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Active learning failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
