"""Finding 86's control: is protocol v2's val_f1 for best_model.pt distinguishable
from predictions that carry no information about ink, on the same sample?

Read-only. Mirrors scripts/reevaluate_best_model.py's pipeline (same validation
dataset, seed 42, checkpoint and input settings) and scores three predictors
with the detector's metric contract on the pooled pixels:

- the model,
- a constant "every pixel is ink" predictor (F1 = 2p/(1+p) at every threshold),
- the model's own probabilities randomly permuted across pixels (same score
  distribution, no spatial information).

    uv run python scripts/loop_v2_constant_control.py \
        --out reports/loop_v2_constant_control.json
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import torch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "scripts", "training"))

from train import (  # noqa: E402
    ExperimentConfig,
    build_validation_dataset,
    collect_validation_predictions,
    pooled_segmentation_metrics,
)

from scripts.reevaluate_best_model import RECORDED_INPUT_SETTINGS  # noqa: E402
from scripts.training.promotion import VALIDATION_PROTOCOL  # noqa: E402
from vesuvius_autoresearch.core.checkpoint_tools import (  # noqa: E402
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
)
from vesuvius_autoresearch.detector.metrics import segmentation_metrics  # noqa: E402

KEYS = (
    "val_f1",
    "best_threshold",
    "precision",
    "recall",
    "pred_positive_rate",
    "average_precision",
    "ap_prevalence_lift",
    "roc_auc",
)


def card(metrics):
    return {k: float(metrics.get(k, float("nan"))) for k in KEYS}


def main(out_path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    config = ExperimentConfig.load("config.json")
    model, settings, chk = load_tool_checkpoint("best_model.pt", device)
    for name, value in settings.items():
        setattr(config, name, value)
    stored = chk.get("config", {})
    for name in RECORDED_INPUT_SETTINGS:
        if name in stored:
            setattr(config, name, stored[name])

    val_ds = build_validation_dataset(config)

    def probabilities(net, x):
        return ink_probabilities(net, validate_batch(x, settings))

    torch.manual_seed(42)
    all_probs, all_targets, diag = collect_validation_predictions(
        model,
        val_ds,
        config.num_layers,
        device,
        batch_size=config.batch_size,
        amp_enabled=device.type == "cuda",
        probabilities=probabilities,
    )
    if not diag["complete"]:
        raise RuntimeError("incomplete validation sample; no control computed")

    probs = torch.cat(all_probs).float().numpy().ravel()
    labels = (torch.cat(all_targets).float().numpy().ravel() > 0.5).astype(np.uint8)
    mask = np.ones_like(labels, dtype=bool)
    prevalence = float(labels.mean())

    with open("best_model.pt", "rb") as f:
        checkpoint_sha256 = hashlib.sha256(f.read()).hexdigest()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_REPO
    ).stdout.strip()

    result = {
        "protocol": VALIDATION_PROTOCOL,
        "checkpoint_sha256": checkpoint_sha256,
        "stored_val_protocol": chk.get("val_protocol"),
        # What v1 recorded about its own sample, so the margins can be compared.
        "stored": {
            k: chk.get(k)
            for k in (
                "val_f1",
                "val_f1_threshold",
                "val_positive_rate",
                "ap_prevalence_lift",
                "roc_auc",
            )
        },
        "git_commit": commit,
        "use_lasagna_requested": bool(config.use_lasagna),
        "requested_patches": diag["requested_patches"],
        "usable_patches": diag["usable_patches"],
        "n_pixels": int(labels.size),
        "ink_prevalence": prevalence,
        "all_ink_f1_formula": 2 * prevalence / (1 + prevalence),
        "model": card(pooled_segmentation_metrics(all_probs, all_targets)),
        "constant_all_ink": card(
            segmentation_metrics(np.ones_like(probs), labels, mask)
        ),
        "model_probs_permuted": card(
            segmentation_metrics(
                np.random.default_rng(0).permutation(probs), labels, mask
            )
        ),
    }
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="JSON path to write")
    main(parser.parse_args().out)
