"""Does the loop's own model read ink better from deep windows? (finding 90)

Finding 89: the TimeSformer detector reads ink mostly from zarr slices 20-26.
The loop's validation reads each patch's 24 slices from a start z0 drawn in 0-7
(depth_band [1, 27], a 4-slice margin), and its model sees the middle 16, zarr
z0+4 to z0+19: none of slices 20-26 at z0 = 0, all seven at z0 = 7. Forcing
z0 = 7 is what depth_band [11, 27] would read. Whether the loop's model, not
the detector, depends on the window's position was not measured.

Read-only, CPU only, one thread. The loop's 400-patch validation draw (seed 42,
moved in the plane as the loop reads it), every patch kept (the sample of
protocol v3, PR #66), scored with the read start forced to each z0:

- the incumbent, best_model.pt, at z0 = 0-7, and at each patch's own z0, which
  must reproduce finding 88 C's incumbent card;
- finding 88 D's 10 loop candidates, at z0 = 0 and z0 = 7.

The loader draws a patch's plane position before its depth, and draws no depth
when the range holds one start, so every z0 scores the same pixels against the
same targets: each comparison is paired.

Pre-registered reading (committed before the first run). The primary number is
delta = pooled ROC AUC at z0 = 7 minus at z0 = 0, over all 400 patches.
  delta(incumbent) >= +0.02 and delta > 0 for at least 8 of the 10 candidates:
      the loop's model reads ink better from deep windows, and pinning the band
      deep (depth_band [11, 27]) is a candidate lever;
  delta(incumbent) <= -0.02 and delta < 0 for at least 8 of the 10: it reads
      ink better from shallow windows;
  |delta(incumbent)| < 0.01 and |mean candidate delta| < 0.01: its reading does
      not depend on the window's position, unlike the detector's;
  otherwise: mixed, reported as such.
Reported beside it: AUC on the 97 ink-containing patches, val_f1 and AP lift
pooled over all 400, and the incumbent at every z0.

    CUDA_VISIBLE_DEVICES= UV_NO_SYNC=1 uv run python scripts/loop_model_depth_offset.py \
        --out reports/loop_model_depth_offset.json
"""

import argparse
import json
import os
import statistics
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # before torch: never touch the loop's GPU

import torch  # noqa: E402
from torch.utils.data import default_collate  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "scripts", "training"))

from train import DEPTH_MARGIN, ExperimentConfig, build_validation_dataset  # noqa: E402

from scripts.detector_on_loop_sample import card, sha256  # noqa: E402
from scripts.loop_candidate_spread import FIRST, copied, input_key  # noqa: E402
from scripts.reevaluate_best_model import RECORDED_INPUT_SETTINGS  # noqa: E402
from scripts.training.promotion import validation_indices  # noqa: E402
from vesuvius_autoresearch.core.checkpoint_tools import (  # noqa: E402
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
)

CANDIDATES = 10
SHALLOW, DEEP = 0, 7
BATCH = 4
REPRODUCE = 1e-4  # this script's incumbent card vs finding 88 C's, both on CPU
SAMPLE_C = "reports/detector_on_full_v2_sample.json"
SAMPLE_D = "reports/loop_candidate_spread.json"


def force_start(dataset, z0):
    """Make every read start at zarr slice z0 (None: the dataset's own draw).

    VesuviusLabeledDataset draws z0 from depth_range only when that range holds
    more than one start, after the plane jitter, so the patches stay put."""
    if not hasattr(dataset, "natural_range"):
        dataset.natural_range = dataset.depth_range
    if z0 is None:
        dataset.depth_range = dataset.natural_range
        return
    start, end = dataset.natural_range
    if not start <= z0 <= end - dataset.num_layers:
        raise ValueError(f"z0 {z0} is outside the dataset's reads {start}-{end}")
    dataset.depth_range = (z0, z0 + dataset.num_layers)


def datasets_for(settings, stored, cache):
    """The validation dataset under a checkpoint's input settings (cached)."""
    key = input_key(settings, stored)
    if key not in cache:
        config = ExperimentConfig.load("config.json")
        for name, value in settings.items():
            setattr(config, name, value)
        for name in RECORDED_INPUT_SETTINGS:
            if name in stored:
                setattr(config, name, stored[name])
        cache[key] = (build_validation_dataset(config), config.num_layers)
    return cache[key]


def probabilities(model, settings, num_layers, items):
    out = []
    with torch.no_grad():
        for s in range(0, len(items), BATCH):
            x_raw, _target, _fiber = default_collate(items[s : s + BATCH])
            x = x_raw[:, :, DEPTH_MARGIN : DEPTH_MARGIN + num_layers]
            out.append(ink_probabilities(model, validate_batch(x, settings)).float())
    return torch.cat(out)


def cards(probs, targets):
    """Cards over all 400 patches and over the ink-containing ones."""
    has_ink = targets.flatten(1).sum(1) >= 1.0
    labels = (targets > 0.5).to(torch.uint8)
    return {
        "all": card(probs.numpy().ravel(), labels.numpy().ravel()),
        "ink": card(probs[has_ink].numpy().ravel(), labels[has_ink].numpy().ravel()),
    }, int(has_ink.sum())


def reading(delta_incumbent, delta_candidates):
    """The pre-registered reading of the AUC deltas (z0 = 7 minus z0 = 0)."""
    up = sum(d > 0 for d in delta_candidates)
    down = sum(d < 0 for d in delta_candidates)
    if delta_incumbent >= 0.02 and up >= 8:
        return "deep windows read better; pinning the band deep is a candidate lever"
    if delta_incumbent <= -0.02 and down >= 8:
        return "shallow windows read better"
    if abs(delta_incumbent) < 0.01 and abs(statistics.mean(delta_candidates)) < 0.01:
        return "no dependence on the window's position"
    return "mixed"


def main(candidate_dir, out_path):
    torch.set_num_threads(1)
    saved_c = json.load(open(SAMPLE_C))
    saved_d = json.load(open(SAMPLE_D))
    if sha256("best_model.pt") != saved_c["best_model_sha256"]:
        raise RuntimeError("best_model.pt is not the incumbent finding 88 measured")
    paths = copied(candidate_dir)[:CANDIDATES]
    if not paths or os.path.basename(paths[0]) != FIRST or len(paths) != CANDIDATES:
        raise RuntimeError(f"expected {CANDIDATES} candidates from {FIRST}")
    for path, row in zip(paths, saved_d["rows"], strict=True):
        if (os.path.basename(path), sha256(path)) != (row["snapshot"], row["sha256"]):
            raise RuntimeError(f"{path} is not finding 88 D's candidate")

    models = {}
    for name, path in [("incumbent", "best_model.pt")] + [
        (os.path.basename(p), p) for p in paths
    ]:
        model, settings, chk = load_tool_checkpoint(path, torch.device("cpu"))
        models[name] = (model.eval(), settings, chk.get("config", {}))

    cache, results, targets_seen = {}, {name: {} for name in models}, None
    plan = [(z0, ["incumbent"]) for z0 in range(SHALLOW, DEEP + 1)]
    plan[SHALLOW] = (SHALLOW, list(models))
    plan[DEEP] = (DEEP, list(models))
    plan.append((None, ["incumbent"]))
    for z0, names in plan:
        by_key = {}
        for name in names:
            _model, settings, stored = models[name]
            by_key.setdefault(input_key(settings, stored), []).append(name)
        for group in by_key.values():
            _model, settings, stored = models[group[0]]
            dataset, num_layers = datasets_for(settings, stored, cache)
            force_start(dataset, z0)
            torch.manual_seed(42)
            items = [dataset[int(i)] for i in validation_indices(len(dataset))]
            force_start(dataset, None)
            targets = torch.stack([t.reshape(1, *t.shape[-2:]) for _, t, _ in items])
            if targets_seen is None:
                targets_seen = targets
            elif not torch.equal(targets, targets_seen):
                raise RuntimeError(f"z0 {z0} moved the patches: not a paired sample")
            for name in group:
                model, settings, _stored = models[name]
                probs = probabilities(model, settings, num_layers, items)
                card_set, n_ink = cards(probs.reshape(targets.shape), targets)
                results[name]["natural" if z0 is None else str(z0)] = card_set
                print(
                    f"z0={z0} {name}: AUC {card_set['all']['roc_auc']:.4f}", flush=True
                )
            del items

    natural = results["incumbent"]["natural"]["all"]
    want = saved_c["cards"]["loop_incumbent"]
    for key in ("val_f1", "roc_auc", "ap_prevalence_lift"):
        if abs(natural[key] - want[key]) > REPRODUCE:
            raise RuntimeError(
                f"incumbent {key} {natural[key]} vs finding 88 C {want[key]}"
            )
    if n_ink != saved_c["patches_with_ink"]:
        raise RuntimeError("ink-containing patch count differs from finding 88")

    def delta(name, part="all"):
        r = results[name]
        return r[str(DEEP)][part]["roc_auc"] - r[str(SHALLOW)][part]["roc_auc"]

    candidates = [name for name in models if name != "incumbent"]
    deltas = {name: delta(name) for name in models}
    result = {
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_REPO
        ).stdout.strip(),
        "best_model_sha256": saved_c["best_model_sha256"],
        "candidates": candidates,
        "patches": int(targets_seen.shape[0]),
        "patches_with_ink": n_ink,
        "z0_range": [SHALLOW, DEEP],
        "cards": results,
        "auc_delta_deep_minus_shallow": deltas,
        "auc_delta_ink_patches": {name: delta(name, "ink") for name in models},
        "reading": reading(deltas["incumbent"], [deltas[c] for c in candidates]),
    }
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(
        json.dumps(
            {k: result[k] for k in ("auc_delta_deep_minus_shallow", "reading")},
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidates", default="local_data/loop_candidates")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    main(args.candidates, args.out)
