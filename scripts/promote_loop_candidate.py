"""Promote a kept loop candidate by hand, as the loop's own promotion does, when every gate but the F1 margin passes.

The loop promotes a cycle when train.py's promotion_decision passes: complete validation, the incumbent's protocol and
validation inputs, the prize gates when enforced, AP prevalence lift above 1 + LIFT_MARGIN, and val_f1 above the
incumbent's by F1_NOISE_TOLERANCE (0.01). A promotion then goes: train.py replaces best_model.pt with the cycle's
checkpoint and appends a row to results.tsv and to prize_readiness.tsv; the loop makes the cycle's config config.json,
adds 1 to the tweak family's weight in autoresearch_history.json, and commits config.json, best_model.pt and
autoresearch_history.json, those paths only (`git commit --only`).

This does the same for a candidate the owner promotes in place of the 0.01 margin; --reason says why. The candidate must
pass every other part of the gate and beat the incumbent, and its config must be config.json with the one tweak. With
--apply the loop must be stopped: .loop_paused present (so the watchdog leaves it), no lock holder, no training run in
the checkout, no held incumbent. Before changing anything it copies the five files it changes to
local_data/loop_promotions/<stamp>/. Without --apply it checks and changes nothing. Run it from the loop's checkout:

    cd <loop checkout> && python3 <repo>/scripts/promote_loop_candidate.py --candidate <checkpoint> \
        --tweak aug_mode=batchgeneratorsv2 --family features --reason "<why>" [--apply]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import loop_control  # noqa: E402

from scripts.training.config import ExperimentConfig  # noqa: E402
from scripts.training.promotion import (  # noqa: E402
    validation_inputs_fingerprint,
    validation_protocol,
)
from vesuvius_autoresearch.core.file_modes import replacement_mode  # noqa: E402

# train.py's, which it does not import (an import patches wandb for the process); the tests compare them.
HISTORY_COLUMNS = (
    "timestamp",
    "val_bpb",
    "avg_skel_dist",
    "avg_centerline_dice",
    "avg_cc_diff",
    "avg_crit_comp",
    "avg_mean_ap",
    "train_loss",
    "throughput_Mvps",
    "num_params_M",
    "peak_vram_mb",
    "config",
)
RESULTS_COLUMNS = tuple(c for c in HISTORY_COLUMNS if c != "avg_mean_ap")
PRIZE_READINESS_COLUMNS = (
    "timestamp",
    "submittable",
    "window_ok",
    "window_mm",
    "villa_metrics_ok",
    "patch_size",
    "val_bpb",
    "avg_skel_dist",
    "avg_centerline_dice",
    "avg_cc_diff",
    "avg_crit_comp",
    "config",
)
LIFT_MARGIN = 0.02
F1_NOISE_TOLERANCE = 1e-2
# run_autoresearch_loop.PROMOTION_FILES: what a promotion commits
PROMOTION_FILES = ("config.json", "best_model.pt", "autoresearch_history.json")
CHANGED = (*PROMOTION_FILES, "results.tsv", "prize_readiness.tsv")
INCUMBENT, HELD, PAUSED = "best_model.pt", ".best_model.pt.held", ".loop_paused"


def checkpoint(raw: bytes) -> dict:
    """A loop checkpoint read without running pickled code: tensors, plain values and the NumPy scalars it saves."""
    try:
        from numpy._core.multiarray import scalar
    except ImportError:
        from numpy.core.multiarray import scalar  # type: ignore[no-redef]  # NumPy 1.x
    allowed = [scalar, np.dtype, type(np.dtype("float64")), type(np.dtype("float32"))]
    with torch.serialization.safe_globals(allowed):
        return torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)


def checks(candidate: dict, incumbent: dict, config: dict, attr: str, value, inputs: str) -> list[tuple[str, bool, str]]:  # fmt: skip
    """promotion_decision's gates but the margin, and that the candidate is this config with the one tweak."""
    protocol = validation_protocol(config.get("depth_band"))
    diag, inc_diag = (
        candidate.get("validation_diag") or {},
        incumbent.get("validation_diag") or {},
    )
    want = {**config, attr: value}
    differ = sorted(
        k
        for k in set(want) | set(candidate["config"])
        if want.get(k) != candidate["config"].get(k)
    )
    f1, inc_f1, lift = (
        candidate.get("val_f1"),
        incumbent.get("val_f1"),
        candidate.get("ap_prevalence_lift"),
    )
    finite = all(isinstance(x, (int, float)) and math.isfinite(x) for x in (f1, inc_f1))
    gates = (
        not config.get("enforce_prize_gates", True)
        or candidate.get("submittable") is True
    )
    a, b = candidate["model_state_dict"], incumbent["model_state_dict"]
    same_model = a.keys() == b.keys() and all(a[k].shape == b[k].shape for k in a)
    return [
        ("tweak", config.get(attr) != value, f"config.json has {attr}={config.get(attr)!r}; the candidate {value!r}"),
        ("config", not differ, "config.json with the tweak" if not differ else f"differs in {differ}"),
        ("protocol", candidate.get("val_protocol") == incumbent.get("val_protocol") == protocol,
         f"{candidate.get('val_protocol')} (incumbent {incumbent.get('val_protocol')}, loop {protocol})"),
        ("validation complete", diag.get("complete") is True and diag.get("batch_errors") == 0
         and diag.get("scored_patches") == diag.get("requested_patches"),
         f"{diag.get('scored_patches')} of {diag.get('requested_patches')} patches, {diag.get('batch_errors')} batch errors"),
        ("validation inputs", diag.get("inputs_sha256") == inc_diag.get("inputs_sha256") == inputs,
         f"{str(diag.get('inputs_sha256'))[:16]} (incumbent {str(inc_diag.get('inputs_sha256'))[:16]}, now {inputs[:16]})"),
        ("prize gates", gates, f"submittable {candidate.get('submittable')}"),
        ("AP lift", isinstance(lift, (int, float)) and math.isfinite(lift) and lift > 1 + LIFT_MARGIN,
         f"{lift} (above {1 + LIFT_MARGIN})"),
        ("beats the incumbent", finite and f1 > inc_f1,
         f"{f1} against {inc_f1}: {f1 - inc_f1:+.6f}, the loop's margin {F1_NOISE_TOLERANCE}" if finite else "not finite"),
        ("architecture", same_model, f"{len(a)} tensors" + ("" if same_model else ", unlike the incumbent's")),
    ]  # fmt: skip


def history_row(loop: Path, candidate: dict) -> list[str]:
    """The candidate run's history.tsv row (train.py logs every run there in results.tsv's format)."""
    lines = (loop / "history.tsv").read_text().splitlines()
    if tuple(lines[0].split("\t")) != HISTORY_COLUMNS:
        raise SystemExit("history.tsv's header is not train.py's")
    want = [
        f"{candidate[k]:.6f}"
        for k in ("val_bpb", "avg_skel_dist", "avg_centerline_dice")
    ]
    want.append(f"{candidate['avg_cc_diff']:.3f}")
    cfg = json.dumps(candidate["config"])
    found = [r for r in (ln.split("\t") for ln in lines[1:]) if len(r) == len(HISTORY_COLUMNS) and r[-1] == cfg and r[1:5] == want]  # fmt: skip
    if len(found) != 1:
        raise SystemExit(
            f"history.tsv has {len(found)} rows for the candidate's run, not 1"
        )
    return found[0]


def rows(row: list[str], candidate: dict, stamp: str) -> dict[str, list]:
    return {
        "results.tsv": [stamp, *row[1:6], *row[7:]],
        "prize_readiness.tsv": [
            stamp, candidate["submittable"], candidate["window_ok"], f"{candidate['window_mm']:.4f}",
            candidate["villa_metrics_ok"], candidate["config"]["patch_size"], *row[1:6], row[11],
        ],
    }  # fmt: skip


def stopped(loop: Path) -> None:
    if not (loop / PAUSED).exists():
        raise SystemExit(f"{PAUSED} is missing, so the watchdog would restart the loop: stop it with scripts/loop_control.py stop")  # fmt: skip
    pid = loop_control.running_pid(loop)
    if pid:
        raise SystemExit(f"the loop's lock is held by PID {pid}: stop it first")
    runs = loop_control.unsupervised_runs(loop)
    if runs:
        raise SystemExit(f"training runs are going in this checkout: {runs}")
    if (loop / HELD).exists():
        raise SystemExit(
            f"{HELD} exists: a run's held incumbent needs the operator's call first"
        )


def _replace(path: Path, write) -> None:
    """write(temporary path), then rename it over path with path's mode."""
    tmp = path.with_name(f".{path.name}.promote.tmp")
    write(tmp)
    os.chmod(tmp, replacement_mode(path))
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _append(path: Path, columns: tuple, values: list) -> None:
    if path.read_text().splitlines()[0].split("\t") != list(columns):
        raise SystemExit(f"{path.name}'s header is not train.py's")
    with open(path, "a") as f:
        f.write("\t".join(str(v) for v in values) + "\n")
        f.flush()
        os.fsync(f.fileno())


def apply(loop: Path, candidate_path: Path, cfg: ExperimentConfig, family: str, new_rows: dict, stamp: str, message: str) -> Path:  # fmt: skip
    kept = (
        loop / "local_data/loop_promotions" / stamp.replace(" ", "_").replace(":", "-")
    )
    kept.mkdir(parents=True)
    for name in CHANGED:
        shutil.copy2(loop / name, kept / name)
    _replace(loop / INCUMBENT, lambda tmp: shutil.copyfile(candidate_path, tmp))
    _replace(loop / "config.json", cfg.save)
    counts = json.loads((loop / "autoresearch_history.json").read_text())
    counts[family] = counts.get(family, 1) + 1
    _replace(loop / "autoresearch_history.json", lambda tmp: tmp.write_text(json.dumps(counts, indent=4)))  # fmt: skip
    _append(loop / "results.tsv", RESULTS_COLUMNS, new_rows["results.tsv"])
    _append(loop / "prize_readiness.tsv", PRIZE_READINESS_COLUMNS, new_rows["prize_readiness.tsv"])  # fmt: skip
    git = ["git", "-C", str(loop)]
    subprocess.run([*git, "add", "--", *PROMOTION_FILES], check=True)
    done = subprocess.run(
        [*git, "commit", "--only", "-m", message, "--", *PROMOTION_FILES]
    )
    if done.returncode != 0:
        subprocess.run([*git, "reset", "-q", "--", *PROMOTION_FILES])
        raise SystemExit(
            f"promoted on disk but not committed; the old files are in {kept}"
        )
    return kept


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument(
        "--tweak",
        required=True,
        help="attr=value, the candidate's one change to config.json",
    )
    ap.add_argument(
        "--family", required=True, help="the tweak's family in the loop's templates"
    )
    ap.add_argument(
        "--reason",
        required=True,
        help="why it is promoted in place of the loop's margin",
    )
    ap.add_argument(
        "--trailer",
        action="append",
        default=[],
        help="a line to end the commit message with",
    )
    ap.add_argument("--stamp", default=None, help="the rows' timestamp (default now)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    loop = Path.cwd()
    attr, sep, raw_value = args.tweak.partition("=")
    config = json.loads((loop / "config.json").read_text())
    if not sep or attr not in config:
        raise SystemExit(f"--tweak names no config.json field: {args.tweak}")
    try:
        value = json.loads(raw_value)
    except ValueError:
        value = raw_value
    raw = args.candidate.read_bytes()
    candidate, incumbent = checkpoint(raw), checkpoint((loop / INCUMBENT).read_bytes())
    inputs = validation_inputs_fingerprint(config["val_uri"], config.get("depth_band"))
    results = checks(candidate, incumbent, config, attr, value, inputs)
    for name, ok, detail in results:
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {detail}")
    failed = [name for name, ok, _ in results if not ok]
    if failed:
        raise SystemExit(f"refused: {', '.join(failed)}")
    cfg = ExperimentConfig.load(str(loop / "config.json"))
    setattr(cfg, attr, value)
    if asdict(cfg) != candidate["config"]:
        raise SystemExit(
            "config.json, loaded and tweaked as the loop does, is not the candidate's config"
        )
    stamp = args.stamp or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_rows = rows(history_row(loop, candidate), candidate, stamp)
    sha = hashlib.sha256(raw).hexdigest()
    message = (
        f"MANUAL PROMOTION: {attr}_{raw_value} improved model to val_f1 {candidate['val_f1']}\n\n"
        f"{args.reason}\n\nCandidate: {args.candidate} (sha256 {sha})."
        + ("\n\n" + "\n".join(args.trailer) if args.trailer else "")
    )
    print("all checks pass")
    print(f"would append to results.tsv: {new_rows['results.tsv'][:6]} ...")
    print(f"would commit {', '.join(PROMOTION_FILES)}:\n{message}")
    if not args.apply:
        print("dry run: nothing changed")
        return 0
    stopped(loop)
    kept = apply(loop, args.candidate, cfg, args.family, new_rows, stamp, message)
    print(f"promoted; the old files are in {kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
