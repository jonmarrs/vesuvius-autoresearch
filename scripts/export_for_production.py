#!/usr/bin/env python3
"""Export a recorded checkpoint envelope; inference compatibility is separate.

Local architectures are reconstructed with complete weights on CPU. Legacy
primus_lejepa envelopes receive structural checks only; they are not converted
into villa's native train_py format. Only trusted local checkpoints may be read.
"""

import argparse
import hashlib
import json
import math
import pickle
import sys
from numbers import Real
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.labeling.label_artifacts import new_output, publish_new_file
from vesuvius_autoresearch.core.checkpoint_tools import build_tool_model
from vesuvius_autoresearch.core.inference import positive_integer

CHECKPOINT_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    EOFError,
    pickle.UnpicklingError,
    ImportError,
)
METRIC_NAMES = (
    "val_bpb",
    "val_f1",
    "val_f1_threshold",
    "ap_prevalence_lift",
    "roc_auc",
    "val_positive_rate",
    "avg_mean_ap",
    "avg_centerline_dice",
    "avg_skel_dist",
    "avg_cc_diff",
)
PROVENANCE_NAMES = (
    "pretrained_lejepa_checkpoint",
    "pretrained_lejepa_sha",
    "finetune_config_path",
    "finetune_config_sha",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkpoint_contract(checkpoint, *, verify_model=True):
    """Validate the envelope's actual data; never infer architecture from key order."""
    if not isinstance(checkpoint, dict):
        raise ValueError("checkpoint must be an object")
    config = checkpoint.get("config")
    if not isinstance(config, dict):
        raise ValueError("checkpoint must contain a recorded config object")
    json.dumps(config, allow_nan=False)
    architecture = config.get("architecture")
    if not isinstance(architecture, str) or not architecture:
        raise ValueError("checkpoint must record its architecture; no prefix guessing")
    state = checkpoint.get("model_state_dict")
    if not isinstance(state, dict) or not state:
        raise ValueError("checkpoint must contain nonempty model_state_dict weights")
    for name, tensor in state.items():
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(tensor, torch.Tensor)
            or tensor.layout != torch.strided
            or tensor.is_quantized
            or tensor.is_complex()
            or not torch.isfinite(tensor).all()
        ):
            raise ValueError(f"weight {name!r} must be a finite real dense tensor")
    if architecture == "primus_lejepa":
        positive_integer(config.get("patch_size"), "recorded patch_size")
        if not any(name.startswith("shared_encoder.") for name in state):
            raise ValueError("primus_lejepa weights must contain shared_encoder.*")
        validation = "STRUCTURE_ONLY"
    else:
        if verify_model:
            build_tool_model(checkpoint)
        validation = "STRICT_LOCAL_MODEL_LOAD"
    metrics = {name: checkpoint[name] for name in METRIC_NAMES if name in checkpoint}
    for name, value in metrics.items():
        if value is not None and (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            raise ValueError(f"recorded metric {name} must be finite or null")
    return state, config, metrics, validation


def validate_envelope(checkpoint, *, verify_model=True):
    """Validate exported structure and local weights; this never verifies inference."""
    _, config, metrics, validation = checkpoint_contract(
        checkpoint, verify_model=verify_model
    )
    metadata = checkpoint.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("exported checkpoint must contain metadata")
    if (
        metadata.get("version") != "checkpoint-envelope-v1"
        or metadata.get("framework") != "vesuvius-autoresearch"
        or metadata.get("architecture") != config["architecture"]
        or metadata.get("weights_validation") != validation
        or metadata.get("inference_verified") is not False
        or metadata.get("submittable", False) is not None
        or metadata.get("metrics") != metrics
        or metadata.get("val_bpb") != metrics.get("val_bpb")
    ):
        raise ValueError(
            "export metadata disagrees with the checkpoint envelope contract"
        )
    digest = metadata.get("source_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise ValueError("export must identify the source checkpoint SHA-256")
    if (
        not isinstance(metadata.get("source_checkpoint"), str)
        or not metadata["source_checkpoint"]
    ):
        raise ValueError("export must identify the source checkpoint path")
    for name in PROVENANCE_NAMES:
        if metadata.get(name) != config.get(name):
            raise ValueError(f"export provenance {name} disagrees with recorded config")
    json.dumps(metadata, allow_nan=False)
    return checkpoint


def export_checkpoint(input_path, output_path):
    source = Path(input_path).resolve()
    output = new_output(output_path, source)
    if not source.is_file():
        raise FileNotFoundError(f"checkpoint not found: {source}")
    digest = sha256_file(source)
    checkpoint = torch.load(source, map_location="cpu", weights_only=False)
    if (
        isinstance(checkpoint, dict)
        and "model_state_dict" not in checkpoint
        and "state_dict" in checkpoint
    ):
        checkpoint = {**checkpoint, "model_state_dict": checkpoint["state_dict"]}
    elif (
        isinstance(checkpoint, dict)
        and "model_state_dict" in checkpoint
        and "state_dict" in checkpoint
    ):
        raise ValueError(
            "checkpoint has ambiguous weight keys; select one recorded weight set"
        )
    state, config, metrics, validation = checkpoint_contract(checkpoint)
    metadata = {
        "version": "checkpoint-envelope-v1",
        "framework": "vesuvius-autoresearch",
        "architecture": config["architecture"],
        "val_bpb": metrics.get("val_bpb"),
        "metrics": metrics,
        "source_checkpoint": str(source),
        "source_sha256": digest,
        "weights_validation": validation,
        "inference_verified": False,
        "submittable": None,
        "provenance_verification": "recorded config only; external lineage unverified",
        **{name: config[name] for name in PROVENANCE_NAMES if name in config},
    }
    exported = {
        "model_state_dict": state,
        "config": config,
        "metadata": metadata,
        **metrics,
    }
    validate_envelope(exported, verify_model=False)
    if sha256_file(source) != digest:
        raise ValueError("source checkpoint changed during validation")
    with publish_new_file(output, source) as staging:
        torch.save(exported, staging)
        validate_envelope(
            torch.load(staging, map_location="cpu", weights_only=False),
        )
    print(f"Checkpoint envelope exported: {output}")
    print(
        f"Weights: {validation}; inference compatibility and submission eligibility unverified"
    )
    return exported


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="best_model.pt")
    parser.add_argument("--output", required=True, help="New checkpoint envelope path")
    args = parser.parse_args(argv)
    try:
        export_checkpoint(args.input, args.output)
    except CHECKPOINT_ERRORS as exc:
        parser.exit(1, f"Checkpoint export failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
