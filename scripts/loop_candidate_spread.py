"""How far does a detector-quality model stand out from the loop's ordinary
candidates, on the loop's sample (A) and with the draw's ink-free patches kept (C)?

Finding 88 measured the detector-minus-incumbent gap under each sample against the
loop's fixed tolerance (0.03). A gap matters only relative to the spread of the
scores the loop actually produces, and that spread may differ between samples.

Read-only, CPU only, one thread. Scores loop candidates (each cycle's
last_model.pt, copied by scripts/snapshot_loop_candidates.sh before the next
cycle overwrote it) on all 400 patches of the loop's seed-42 draw:
  A = its ink-containing patches, pooled: the loop's own val_f1. Each candidate's
      stored val_f1 (scored on the GPU under autocast) must be reproduced within
      1e-3, else the run aborts;
  C = all 400 patches, pooled.
The incumbent is scored the same way and must reproduce finding 88's saved
numbers (reports/detector_on_loop_sample.json, reports/detector_on_full_v2_sample.json).

Pre-registered (committed before the first run): the first 10 snapshots by name
(candidate_20261013-155821 and the 9 after it), none excluded.
  spread_P = sample SD of the 10 candidates' val_f1 under protocol P;
  gap_P    = detector val_f1 - incumbent val_f1 under P, from finding 88's saved
             measurements (single-window detector);
  ratio_P  = gap_P / spread_P.
Reading:
  ratio_C >= 2 * ratio_A: C separates a detector-quality model from the loop's
      ordinary candidates better; finding 88's recommendation stands;
  ratio_A >= 2 * ratio_C: A separates better once the tolerance is scaled to its
      spread; finding 88's "only keeping the ink-free patches separates them" is
      wrong and is corrected;
  otherwise: comparable; what differs between the samples is scale, and the
      defect is a tolerance not matched to the spread of either.
Also reported, not read: each candidate's margin over the incumbent under both
samples; whether the loop's rule (val_f1 > incumbent + 0.03, AP lift > 1.02)
would promote any of them under C; the same ratios for ROC AUC and AP lift.
Caveat: the spread mixes the candidates' config differences with run-to-run
noise (each cycle draws a fresh training-order seed); it is not the
identical-config noise probe (scripts/f1_noise_probe.py).

    CUDA_VISIBLE_DEVICES= UV_NO_SYNC=1 uv run python scripts/loop_candidate_spread.py \
        --candidates local_data/loop_candidates --out reports/loop_candidate_spread.json [--wait]
"""

import argparse
import glob
import json
import os
import statistics
import subprocess
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # before torch: never touch the loop's GPU

import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch.utils.data import default_collate  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "scripts", "training"))

from train import (  # noqa: E402
    DEPTH_MARGIN,
    LIFT_MARGIN,
    ExperimentConfig,
    build_validation_dataset,
)

from scripts.detector_on_loop_sample import card, sha256  # noqa: E402
from scripts.reevaluate_best_model import RECORDED_INPUT_SETTINGS  # noqa: E402
from scripts.training.promotion import (  # noqa: E402
    validation_indices,
    validation_protocol,
)
from vesuvius_autoresearch.core.checkpoint_tools import (  # noqa: E402
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
)

CANDIDATES = 10
FIRST = "candidate_20261013-155821.pt"
REPRODUCE = 1e-3  # stored (GPU, autocast) vs recomputed (CPU) val_f1
TOLERANCE = 0.03  # train.F1_NOISE_TOLERANCE
BATCH = 4
SAMPLE_A = "reports/detector_on_loop_sample.json"
SAMPLE_C = "reports/detector_on_full_v2_sample.json"


def input_key(settings, stored):
    recorded = tuple(stored.get(name) for name in RECORDED_INPUT_SETTINGS)
    return tuple(sorted(settings.items())), recorded


def patches(settings, stored, cache):
    """The draw's 400 (input, target) pairs under a checkpoint's input settings."""
    key = input_key(settings, stored)
    if key not in cache:
        config = ExperimentConfig.load("config.json")
        for name, value in settings.items():
            setattr(config, name, value)
        for name in RECORDED_INPUT_SETTINGS:
            if name in stored:
                setattr(config, name, stored[name])
        dataset = build_validation_dataset(config)
        torch.manual_seed(42)
        items = [dataset[int(i)] for i in validation_indices(len(dataset))]
        cache[key] = (items, config.num_layers)
    return cache[key]


def score(path, cache):
    """Cards on A (ink-containing patches) and C (all patches), and the checkpoint."""
    model, settings, chk = load_tool_checkpoint(path, torch.device("cpu"))
    model.eval()
    items, num_layers = patches(settings, chk.get("config", {}), cache)
    probs, targets = [], []
    with torch.no_grad():
        for s in range(0, len(items), BATCH):
            x_raw, target, _fiber = default_collate(items[s : s + BATCH])
            x = x_raw[:, :, DEPTH_MARGIN : DEPTH_MARGIN + num_layers]
            probs.append(ink_probabilities(model, validate_batch(x, settings)).float())
            targets.append(target.reshape(probs[-1].shape).float())
    p, t = torch.cat(probs), torch.cat(targets)
    has_ink = t.flatten(1).sum(1) >= 1.0
    cards = {}
    for name, keep in (("A", has_ink), ("C", torch.ones_like(has_ink))):
        labels = (t[keep].numpy().ravel() > 0.5).astype(np.uint8)
        cards[name] = card(p[keep].numpy().ravel(), labels)
    return cards, chk, int(has_ink.sum())


def config_diff(candidate, incumbent):
    keys = sorted(set(candidate) | set(incumbent))
    return {k: candidate.get(k) for k in keys if candidate.get(k) != incumbent.get(k)}


def ratio(gap, values):
    spread = statistics.stdev(values)
    return {"gap": gap, "spread": spread, "ratio": gap / spread}


def copied(candidate_dir):
    """Snapshots whose copy has finished, in order: the first (copied by hand
    before the watcher started) and those the watcher has logged."""
    log = os.path.join(candidate_dir, "snapshots.log")
    logged = set()
    if os.path.exists(log):
        for line in open(log):
            parts = line.split()
            if len(parts) >= 2 and parts[1].endswith(".pt"):
                logged.add(os.path.basename(parts[1]))
    names = sorted(
        os.path.basename(p)
        for p in glob.glob(os.path.join(candidate_dir, "candidate_*.pt"))
    )
    return [
        os.path.join(candidate_dir, b)
        for b in names
        if b == FIRST or (b > FIRST and b in logged)
    ]


def main(candidate_dir, out_path, n, wait):
    torch.set_num_threads(1)  # the loop's data pipeline needs the other cores
    if not wait and len(copied(candidate_dir)) < n:
        raise SystemExit(f"fewer than {n} snapshots in {candidate_dir}")
    saved = {"A": json.load(open(SAMPLE_A)), "C": json.load(open(SAMPLE_C))}
    protocol = validation_protocol(ExperimentConfig.load("config.json").depth_band)
    cache = {}

    incumbent, inc_chk, inc_ink = score("best_model.pt", cache)
    for name in ("A", "C"):
        want = saved[name]["cards"]["loop_incumbent"]
        if abs(incumbent[name]["val_f1"] - want["val_f1"]) > 1e-5:
            raise RuntimeError(f"incumbent does not reproduce finding 88's {name}")
    if inc_ink != saved["A"]["usable_patches"]:
        raise RuntimeError("ink-containing patch count differs from finding 88")

    rows = []
    while len(rows) < n:
        pending = copied(candidate_dir)[len(rows) : n]
        if not pending:  # --wait: the loop has not finished the next cycle yet
            time.sleep(60)
            continue
        path = pending[0]
        cards, chk, _ = score(path, cache)
        stored = float(chk["val_f1"])
        if chk.get("val_protocol") != protocol:
            raise RuntimeError(f"{path}: scored under {chk.get('val_protocol')}")
        if abs(cards["A"]["val_f1"] - stored) > REPRODUCE:
            raise RuntimeError(
                f"{path}: A val_f1 {cards['A']['val_f1']:.6f} vs stored {stored:.6f}"
            )
        rows.append(
            {
                "snapshot": os.path.basename(path),
                "sha256": sha256(path),
                "stored_val_f1": stored,
                "train_sampling_seed": chk.get("train_sampling_seed"),
                "config_diff": config_diff(
                    chk.get("config", {}), inc_chk.get("config", {})
                ),
                "cards": cards,
                "margin_over_incumbent": {
                    k: cards[k]["val_f1"] - incumbent[k]["val_f1"] for k in ("A", "C")
                },
                "would_promote_under_C": bool(
                    cards["C"]["val_f1"] > incumbent["C"]["val_f1"] + TOLERANCE
                    and cards["C"]["ap_prevalence_lift"] > 1.0 + LIFT_MARGIN
                ),
            }
        )
        print(
            f"{rows[-1]['snapshot']}: A {cards['A']['val_f1']:.6f} "
            f"(stored {stored:.6f}) C {cards['C']['val_f1']:.6f}",
            flush=True,
        )

    separation = {}
    for metric in ("val_f1", "roc_auc", "ap_prevalence_lift"):
        separation[metric] = {}
        for name in ("A", "C"):
            det = saved[name]["cards"]["detector_single_window"][metric]
            separation[metric][name] = ratio(
                det - incumbent[name][metric],
                [r["cards"][name][metric] for r in rows],
            )
    ra, rc = separation["val_f1"]["A"]["ratio"], separation["val_f1"]["C"]["ratio"]
    if rc >= 2 * ra:
        reading = "C separates better; finding 88's recommendation stands"
    elif ra >= 2 * rc:
        reading = "A separates better once the tolerance is scaled; correct finding 88"
    else:
        reading = "comparable; the defect is a tolerance matched to neither spread"
    result = {
        "protocol": protocol,
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_REPO
        ).stdout.strip(),
        "best_model_sha256": sha256("best_model.pt"),
        "detector_sha256": saved["C"]["detector_sha256"],
        "candidates": len(rows),
        "incumbent": incumbent,
        "rows": rows,
        "separation": separation,
        "reading": reading,
    }
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({k: result[k] for k in ("separation", "reading")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidates", required=True, help="snapshot directory")
    parser.add_argument("--out", required=True, help="JSON path to write")
    parser.add_argument("--n", type=int, default=CANDIDATES, help=argparse.SUPPRESS)
    parser.add_argument(
        "--wait", action="store_true", help="score snapshots as the watcher logs them"
    )
    args = parser.parse_args()
    main(args.candidates, args.out, args.n, args.wait)
