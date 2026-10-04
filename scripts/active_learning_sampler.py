import argparse
import json
import os
from datetime import datetime

import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

# Local imports
from vesuvius_autoresearch.core.checkpoint_tools import (
    load_tool_checkpoint,
    validate_batch,
    validate_ink_logits,
)
from vesuvius_autoresearch.core.inference import positive_integer
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def calculate_entropy(probs):
    """Calculate pixel-wise entropy: -p*log(p) - (1-p)*log(1-p)"""
    if not torch.isfinite(probs).all() or not ((probs >= 0) & (probs <= 1)).all():
        raise ValueError("probabilities must be finite in [0,1]")
    eps = 1e-8
    entropy = -probs * torch.log(probs + eps) - (1 - probs) * torch.log(1 - probs + eps)
    return entropy


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

    def sample_uncertain_regions(self, dataloader, n_samples=10):
        positive_integer(n_samples, "n_samples")
        if getattr(dataloader.dataset, "jitter", False):
            raise ValueError("active-learning coordinates require jitter=False")
        uncertainties = []
        all_indices = []

        # Positions are recovered as `dataset.valid_coords[i * batch_size + k]`,
        # which is only the patch that was scored if the loader emits samples in
        # dataset order. Under a shuffling sampler the arithmetic still produces
        # in-range indices, so the failure would be silent: plausible-looking
        # coordinates pointing at patches the model never saw.
        # Inverted deliberately: an earlier version enumerated RandomSampler and
        # checked `dataloader.shuffle`, which no DataLoader exposes, so half the
        # condition was dead and SubsetRandomSampler, WeightedRandomSampler and
        # DistributedSampler(shuffle=True) all slipped through. Requiring
        # sequential order rejects every shuffling variant instead.
        # A loader with no `.sampler` cannot be introspected (duck-typed test
        # doubles); only an explicit non-sequential sampler is rejected.
        sampler = getattr(dataloader, "sampler", None)
        if sampler is not None and not isinstance(
            sampler, torch.utils.data.SequentialSampler
        ):
            raise ValueError(
                "sample_uncertain_regions needs a dataloader in dataset order; "
                "build it with shuffle=False, or the returned coordinates will "
                "not correspond to the patches that were scored."
            )

        batch_sampler = getattr(dataloader, "batch_sampler", None)
        if batch_sampler is not None and (
            type(batch_sampler) is not torch.utils.data.BatchSampler
            or not isinstance(batch_sampler.sampler, torch.utils.data.SequentialSampler)
        ):
            raise ValueError(
                "active learning requires sequential batches in dataset order"
            )

        print(f"Sampling {n_samples} high-uncertainty regions...")

        offset = 0
        with torch.no_grad():
            for i, (x, _, _) in enumerate(tqdm(dataloader)):
                x = x.to(self.device)
                if self.settings is not None:
                    validate_batch(x, self.settings)
                if (
                    x.ndim != 5
                    or not x.is_floating_point()
                    or not torch.isfinite(x).all()
                ):
                    raise ValueError(
                        "input must be a finite floating-point B/C/Z/H/W tensor"
                    )

                # Forward pass - support multi-output
                outputs = self.model(x, return_qc=True)
                if isinstance(outputs, tuple):
                    if len(outputs) != 2:
                        raise ValueError("model must return ink and QC logits")
                    out_ink, qc = outputs[0], outputs[1]
                else:
                    out_ink = outputs
                    # Dummy QC if model doesn't have it
                    qc = torch.ones((x.shape[0], 1), device=self.device)

                validate_ink_logits(out_ink, x)
                if (
                    not isinstance(qc, torch.Tensor)
                    or tuple(qc.shape) != (len(x), 1)
                    or not qc.is_floating_point()
                    or not torch.isfinite(qc).all()
                ):
                    raise ValueError("QC logits must be finite with shape (batch, 1)")
                probs = torch.sigmoid(out_ink)

                # Metric 1: Prediction Entropy (ambiguity)
                # out_ink might be 4D [B, 1, H, W] or 5D [B, 1, Z, H, W]
                # dataset returns [B, 1, Z, H, W] usually
                entropy = calculate_entropy(probs).mean(dim=tuple(range(1, probs.ndim)))

                # Metric 2: QC Confidence (model's own estimate of quality)
                # Lower QC value = higher uncertainty
                qc_uncertainty = 1.0 - torch.sigmoid(qc).squeeze()
                if qc_uncertainty.ndim == 0:
                    qc_uncertainty = qc_uncertainty.unsqueeze(0)

                # Combined Uncertainty Score
                score = 0.7 * entropy + 0.3 * qc_uncertainty

                uncertainties.append(score.cpu().numpy())

                # Track original indices
                batch_size = x.shape[0]
                indices = np.arange(offset, offset + batch_size)
                offset += batch_size
                all_indices.append(indices)

        if not uncertainties:
            raise ValueError("no patches available for active learning")
        uncertainties = np.concatenate(uncertainties)
        all_indices = np.concatenate(all_indices)

        # Get indices of top N uncertain regions
        top_n_idx = np.argsort(uncertainties)[-n_samples:][::-1]

        final_indices = all_indices[top_n_idx]
        final_scores = uncertainties[top_n_idx]

        # Map indices back to coordinates from the dataset
        coords = []
        for idx in final_indices:
            coords.append(dataloader.dataset.valid_coords[idx])

        return np.array(coords), final_scores


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


def main():
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
        type=int,
        default=20,
        help="Number of uncertain patches to sample",
    )
    parser.add_argument(
        "--patches_json",
        type=str,
        default=None,
        help="Path to pre-computed optimal patches.json (from vesuvius.find_patches) to override runtime dataset scanning.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/active_learning_queue.json",
        help="Path to export review queue",
    )
    args = parser.parse_args()
    positive_integer(args.n_samples, "n_samples")
    if args.patches_json and not os.path.isfile(args.patches_json):
        raise FileNotFoundError(args.patches_json)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Active Learning Sampler: Running on {device}")

    # 1. Load Checkpoint Metadata
    model, arch_kwargs, _ = load_tool_checkpoint(args.checkpoint, device)

    sampler = ActiveLearningSampler(model, device=device, settings=arch_kwargs)

    # 2. Setup Dataset
    labels_path = args.labels
    if labels_path is None:
        base_dir = os.path.dirname(args.volume)
        labels_path = os.path.join(base_dir, "inklabels_refined.png")
        if not os.path.exists(labels_path):
            labels_path = os.path.join(base_dir, "inklabels_filled.png")
            if not os.path.exists(labels_path):
                labels_path = os.path.join(base_dir, "inklabels.png")

        if not os.path.exists(labels_path) and "surface_volume.zarr" in args.volume:
            frag_name = args.volume.split("/")[-2]
            labels_path = f"local_data/{frag_name}/inklabels_refined.png"
            if not os.path.exists(labels_path):
                labels_path = f"local_data/{frag_name}/inklabels_filled.png"
                if not os.path.exists(labels_path):
                    labels_path = f"local_data/{frag_name}/inklabels.png"

    print(f"Using labels from: {labels_path}")

    dataset = VesuviusLabeledDataset(
        args.volume,
        labels_path,
        patch_size=arch_kwargs["patch_size"],
        num_layers=arch_kwargs["num_layers"],
        use_ridges=arch_kwargs["use_ridges"],
        ridge_sigma=arch_kwargs["ridge_sigma"],
        require_ink=False,
        jitter=False,
        strict_reads=True,
        patches_json=args.patches_json,
    )

    catalog = np.asarray(dataset.valid_coords)
    size = arch_kwargs["patch_size"]
    if (
        catalog.ndim != 2
        or catalog.shape[1] != 2
        or not len(catalog)
        or not np.issubdtype(catalog.dtype, np.integer)
        or (catalog < 0).any()
        or (catalog[:, 0] > dataset.shape[1] - size).any()
        or (catalog[:, 1] > dataset.shape[2] - size).any()
    ):
        raise ValueError(
            "patch catalog must contain nonempty in-bounds integer y/x coordinates"
        )

    all_coords = catalog

    max_eval_patches = 5000
    if len(all_coords) > max_eval_patches:
        print(
            f"Subsampling {max_eval_patches} patches from {len(all_coords)} total valid patches..."
        )
        idx = np.random.default_rng(42).choice(
            len(all_coords), max_eval_patches, replace=False
        )
        dataset.valid_coords = all_coords[idx]

    dataloader = DataLoader(dataset, batch_size=8, shuffle=False)

    # 3. Sample Uncertain Regions
    coords, scores = sampler.sample_uncertain_regions(
        dataloader, n_samples=args.n_samples
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

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "checkpoint": args.checkpoint,
                "volume": args.volume,
                "inference_settings": arch_kwargs,
                "queue": queue,
            },
            f,
            indent=4,
            allow_nan=False,
        )

    print(f"\nSuccess: Exported {len(queue)} patches to review queue: {args.output}")
    print("These regions are ready for interactive cleaning via vc_proofreader.")


if __name__ == "__main__":
    main()
