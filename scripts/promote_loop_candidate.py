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
the checkout, no held incumbent. It holds the checkout lock while applying and refuses if the checked incumbent or
config changed. It installs the captured checkpoint bytes that passed validation. Before changing anything it
validates both log headers and the history weights, then copies the five files it changes to
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
from scripts import loop_control  # noqa: E402
from scripts.training.config import ExperimentConfig  # noqa: E402
from scripts.training.promotion import (  # noqa: E402
    F1_NOISE_TOLERANCE,
    HISTORY_COLUMNS,
    LIFT_MARGIN,
    PRIZE_READINESS_COLUMNS,
    RESULTS_COLUMNS,
    VALIDATION_SAMPLE_PATCHES,
    validation_inputs_fingerprint,
    validation_protocol,
)
from vesuvius_autoresearch.core.file_modes import replacement_mode  # noqa: E402

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


def comparison_checks(candidate: dict, incumbent: dict, config: dict, inputs: str) -> list[tuple[str, bool, str]]:  # fmt: skip
    """Shared recorded-score gates for manual and replicate-rule promotion, without the F1 margin."""
    protocol = validation_protocol(config.get("depth_band"))
    diag, inc_diag = (
        candidate.get("validation_diag") or {},
        incumbent.get("validation_diag") or {},
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
    requested, scored = diag.get("requested_patches"), diag.get("scored_patches")
    complete = (
        diag.get("complete") is True
        and diag.get("batch_errors") == 0
        and isinstance(requested, int)
        and not isinstance(requested, bool)
        and 0 < requested <= VALIDATION_SAMPLE_PATCHES
        and isinstance(scored, int)
        and not isinstance(scored, bool)
        and scored == requested == inc_diag.get("requested_patches")
    )
    return [
        (
            "protocol",
            candidate.get("val_protocol") == incumbent.get("val_protocol") == protocol
            and diag.get("protocol") == inc_diag.get("protocol") == protocol,
            f"{candidate.get('val_protocol')} (incumbent {incumbent.get('val_protocol')}, loop {protocol})",
        ),
        (
            "validation complete",
            complete,
            f"{diag.get('scored_patches')} of {diag.get('requested_patches')} patches, {diag.get('batch_errors')} batch errors",
        ),
        (
            "validation inputs",
            diag.get("inputs_sha256") == inc_diag.get("inputs_sha256") == inputs,
            f"{str(diag.get('inputs_sha256'))[:16]} (incumbent {str(inc_diag.get('inputs_sha256'))[:16]}, now {inputs[:16]})",
        ),
        ("prize gates", gates, f"submittable {candidate.get('submittable')}"),
        (
            "AP lift",
            isinstance(lift, (int, float))
            and math.isfinite(lift)
            and lift > 1 + LIFT_MARGIN,
            f"{lift} (above {1 + LIFT_MARGIN})",
        ),
        (
            "beats the incumbent",
            finite and f1 > inc_f1,
            f"{f1} against {inc_f1}: {f1 - inc_f1:+.6f}, the loop's margin {F1_NOISE_TOLERANCE}"
            if finite
            else "not finite",
        ),
    ]


def checks(candidate: dict, incumbent: dict, config: dict, attr: str, value, inputs: str) -> list[tuple[str, bool, str]]:  # fmt: skip
    """Shared comparison gates, plus the manual command's one-tweak and architecture requirements."""
    want = {**config, attr: value}
    differ = sorted(
        k
        for k in set(want) | set(candidate["config"])
        if want.get(k) != candidate["config"].get(k)
    )
    a, b = candidate["model_state_dict"], incumbent["model_state_dict"]
    same_model = a.keys() == b.keys() and all(a[k].shape == b[k].shape for k in a)
    return [
        ("tweak", config.get(attr) != value, f"config.json has {attr}={config.get(attr)!r}; the candidate {value!r}"),
        ("config", not differ, "config.json with the tweak" if not differ else f"differs in {differ}"),
        *comparison_checks(candidate, incumbent, config, inputs),
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


def stopped(loop: Path, *, check_lock: bool = True) -> None:
    if not (loop / PAUSED).exists():
        raise SystemExit(f"{PAUSED} is missing, so the watchdog would restart the loop: stop it with scripts/loop_control.py stop")  # fmt: skip
    pid = loop_control.running_pid(loop) if check_lock else None
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


def _check_header(path: Path, columns: tuple, missing_ok: bool = False) -> None:
    if missing_ok and not path.exists():
        return
    lines = path.read_text().splitlines()
    if not lines or tuple(lines[0].split("\t")) != columns:
        raise SystemExit(f"{path.name}'s header is not train.py's")


def _append(path: Path, columns: tuple, values: list, missing_ok: bool = False) -> None:
    _check_header(path, columns, missing_ok)
    with open(path, "a") as f:
        if f.tell() == 0:
            f.write("\t".join(columns) + "\n")
        f.write("\t".join(str(v) for v in values) + "\n")
        f.flush()
        os.fsync(f.fileno())


def promote_files(loop: Path, candidate_raw: bytes, new_rows: dict, stamp: str, missing_ok: bool = False) -> Path:  # fmt: skip
    """Install the checked bytes and append their rows, keeping backups and restoring files on write failure.
    The caller holds the checkout lock. With missing_ok, missing logs start with their schema; malformed logs are refused.
    """
    _check_header(loop / "results.tsv", RESULTS_COLUMNS, missing_ok)
    _check_header(loop / "prize_readiness.tsv", PRIZE_READINESS_COLUMNS, missing_ok)
    kept = (
        loop / "local_data/loop_promotions" / stamp.replace(" ", "_").replace(":", "-")
    )
    kept.mkdir(parents=True)
    present = [name for name in CHANGED if (loop / name).exists()]
    for name in present:
        shutil.copy2(loop / name, kept / name)
    try:
        _replace(loop / INCUMBENT, lambda tmp: tmp.write_bytes(candidate_raw))
        _append(
            loop / "results.tsv", RESULTS_COLUMNS, new_rows["results.tsv"], missing_ok
        )
        _append(
            loop / "prize_readiness.tsv",
            PRIZE_READINESS_COLUMNS,
            new_rows["prize_readiness.tsv"],
            missing_ok,
        )
    except BaseException:
        _restore(loop, kept)
        raise
    return kept


def _restore(loop: Path, kept: Path) -> None:
    """Put back the files promote_files kept, and remove the ones it created."""
    for name in CHANGED:
        if (kept / name).exists():
            _replace(loop / name, lambda tmp, n=name: shutil.copyfile(kept / n, tmp))
        elif (loop / name).exists():
            (loop / name).unlink()


def apply(loop: Path, candidate_raw: bytes, cfg: ExperimentConfig, family: str, new_rows: dict, stamp: str, message: str) -> Path:  # fmt: skip
    _check_header(loop / "results.tsv", RESULTS_COLUMNS)
    _check_header(loop / "prize_readiness.tsv", PRIZE_READINESS_COLUMNS)
    counts = json.loads((loop / "autoresearch_history.json").read_text())
    counts[family] = counts.get(family, 1) + 1
    if not isinstance(counts[family], (int, float)) or not math.isfinite(
        counts[family]
    ):
        raise SystemExit(f"history weight for {family!r} must be finite")
    kept = promote_files(loop, candidate_raw, new_rows, stamp)
    try:
        _replace(loop / "config.json", cfg.save)
        _replace(loop / "autoresearch_history.json", lambda tmp: tmp.write_text(json.dumps(counts, indent=4)))  # fmt: skip
    except BaseException:
        _restore(loop, kept)  # not the new checkpoint beside the old config
        raise
    git = ["git", "-C", str(loop)]
    done = subprocess.run([*git, "add", "--", *PROMOTION_FILES])
    if done.returncode == 0:
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
    config_raw = (loop / "config.json").read_bytes()
    config = json.loads(config_raw)
    if not sep or attr not in config:
        raise SystemExit(f"--tweak names no config.json field: {args.tweak}")
    try:
        value = json.loads(raw_value)
    except ValueError:
        value = raw_value
    raw = args.candidate.read_bytes()
    incumbent_raw = (loop / INCUMBENT).read_bytes()
    candidate, incumbent = checkpoint(raw), checkpoint(incumbent_raw)
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
    try:
        lock = loop_control.acquire_lock(loop / "autoresearch.lock")
    except BlockingIOError:
        raise SystemExit(
            "the checkout lock was acquired by another process; retry after stopping it"
        ) from None
    with lock:
        # Opening/closing the lock file via running_pid here would release this
        # process's POSIX lock, so only repeat the other stopped-state checks.
        stopped(loop, check_lock=False)
        for name, expected in (("config.json", config_raw), (INCUMBENT, incumbent_raw)):
            if (loop / name).read_bytes() != expected:
                raise SystemExit(f"{name} changed after validation; retry the checks")
        if (
            validation_inputs_fingerprint(config["val_uri"], config.get("depth_band"))
            != inputs
        ):
            raise SystemExit(
                "validation inputs changed after validation; retry the checks"
            )
        kept = apply(loop, raw, cfg, args.family, new_rows, stamp, message)
    print(f"promoted; the old files are in {kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
