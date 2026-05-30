#!/usr/bin/env python3
"""
Vesuvius Autoresearch: Export for Production
Maps a training checkpoint into the official Grand Prize inference envelope
(villa/ink-detection/optimized_inference). Detects architecture from the
state-dict key prefix so it covers both the autoresearch TimeSformer/ResNet3D
contract and a LeJEPA-fine-tuned Primus checkpoint.

Usage:
  uv run scripts/export_for_production.py --input best_model.pt --output production_model.pt
"""

import argparse
import hashlib
import json
import os
import sys

import torch

# Map architecture name -> expected first-key prefix in model_state_dict.
ARCHITECTURE_STATE_DICT_PREFIXES = {
    "timesformer": "backbone.",
    "resnet3d_decoder": "encoder.",
    "resnet3d-50": "encoder.",
    "primus_lejepa": "shared_encoder.",
}


def detect_architecture(state_dict, declared=None):
    """Infer architecture from a state-dict's first-key prefix.

    If a declared architecture is provided AND matches the observed prefix, it
    wins. Otherwise we fall back to the prefix-derived value. Returns None if
    no known prefix is present.
    """
    if not state_dict:
        return declared
    first_key = next(iter(state_dict.keys()))
    inferred = None
    for arch, prefix in ARCHITECTURE_STATE_DICT_PREFIXES.items():
        if first_key.startswith(prefix):
            inferred = arch
            break
    if declared and declared in ARCHITECTURE_STATE_DICT_PREFIXES:
        return declared
    return inferred or declared


def _sha256_of_file(path):
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_finetune_marker():
    """Pull pretrain SHA + finetune config path from the launcher's marker."""
    marker = os.path.join("reports", "finetune_lejepa_run.json")
    if not os.path.exists(marker):
        return {}
    try:
        with open(marker) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def export_checkpoint(input_path, output_path):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"{input_path} not found")

    print("--- Vesuvius Autoresearch Production Export ---")
    print(f"Converting: {input_path} -> {output_path}")

    checkpoint = torch.load(input_path, map_location="cpu", weights_only=False)

    state_dict = checkpoint.get("model_state_dict") or checkpoint.get("state_dict")
    if not isinstance(state_dict, dict) or not state_dict:
        raise ValueError(
            f"{input_path}: no usable state_dict found (expected model_state_dict or state_dict)."
        )

    config = dict(checkpoint.get("config", {}) or {})
    declared_arch = config.get("architecture")
    architecture = detect_architecture(state_dict, declared_arch)
    if architecture is None:
        first_key = next(iter(state_dict.keys()), "<empty>")
        raise ValueError(
            f"Could not detect architecture from state_dict prefix (first key: {first_key}). "
            f"Known prefixes: {ARCHITECTURE_STATE_DICT_PREFIXES}"
        )
    config["architecture"] = architecture

    metadata = {
        "version": "v2.5.0-DINO",
        "framework": "vesuvius-autoresearch",
        "val_bpb": checkpoint.get("val_bpb", config.get("val_bpb", 0.0)),
        "architecture": architecture,
    }

    if architecture == "primus_lejepa":
        ft = _load_finetune_marker()
        pretrain_sha = _sha256_of_file(ft.get("pretrained_lejepa_checkpoint"))
        ft_config_sha = _sha256_of_file(ft.get("config_path"))
        config.setdefault(
            "pretrained_lejepa_checkpoint", ft.get("pretrained_lejepa_checkpoint")
        )
        config.setdefault("pretrained_lejepa_sha", pretrain_sha)
        config.setdefault("finetune_config_path", ft.get("config_path"))
        config.setdefault("finetune_config_sha", ft_config_sha)
        config.setdefault("patch_size", (ft.get("patch_size") or [32, 64, 64])[-1])
        metadata["pretrained_lejepa_sha"] = pretrain_sha
        metadata["finetune_config_sha"] = ft_config_sha

    prod_state = {
        "model_state_dict": state_dict,
        "config": config,
        "metadata": metadata,
    }

    torch.save(prod_state, output_path)
    print(f"Architecture: {architecture}")
    print("Success! Model exported. Envelope: {model_state_dict, config, metadata}.")
    return prod_state


def main():
    parser = argparse.ArgumentParser(
        description="Map Vesuvius-DINO to Grand Prize Inference Format"
    )
    parser.add_argument(
        "--input", type=str, default="best_model.pt", help="Path to our best_model.pt"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path for the production-ready weight file",
    )
    args = parser.parse_args()

    try:
        export_checkpoint(args.input, args.output)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
