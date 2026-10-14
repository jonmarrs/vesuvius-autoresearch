"""Plan or execute isolated identical-config repeatability runs.

Dry run is the default. Execution requires --execute and a new output directory.
This records descriptive F1 spread; it never calibrates the promotion tolerance.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import shutil
import signal
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.artifact_hashes import sha256_file
from scripts.loop_control import acquire_lock
from scripts.process_supervisor import ProcessSupervisor
from scripts.training.config import ExperimentConfig
from scripts.training.promotion import (
    VALIDATION_PROTOCOL,
    VALIDATION_SAMPLE_PATCHES,
    validation_protocol,
)

RUNNER = REPO / "scripts/training/run_noise_probe.py"
TRAINER = REPO / "scripts/training/train.py"
VILLA = REPO / "villa"
METRICS = (
    "val_f1",
    "val_f1_threshold",
    "ap_prevalence_lift",
    "roc_auc",
    "val_positive_rate",
)


@dataclass(frozen=True)
class ProbePlan:
    config: dict
    checkpoint: Path
    output: Path
    runs: int
    timeout: float
    input_hashes: dict[str, str]
    protocol: str


def _integer(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def _path(value, base):
    if not isinstance(value, str) or not value:
        raise ValueError("input paths must be nonempty strings")
    if urlsplit(value).scheme:
        return value
    return str((base / Path(value).expanduser()).resolve())


def make_plan(config_path, checkpoint, output, *, runs=4, timeout=None):
    from scripts.labeling.label_artifacts import new_output

    config_path, checkpoint = Path(config_path).resolve(), Path(checkpoint).resolve()
    if (
        not config_path.is_file()
        or not checkpoint.is_file()
        or checkpoint.stat().st_size == 0
    ):
        raise ValueError("config and starting checkpoint must be existing files")
    runs = _integer(runs, "runs", 2, 16)
    config_bytes = config_path.read_bytes()
    config_hash = hashlib.sha256(config_bytes).hexdigest()
    with contextlib.redirect_stdout(sys.stderr):
        cfg = ExperimentConfig.from_json(config_bytes)
        for key in ("uri", "val_uri", "foundation_model_path", "pseudo_label_dir"):
            value = getattr(cfg, key)
            if value is not None:
                setattr(cfg, key, _path(value, config_path.parent))
        for key in ("uris", "unlabeled_uris"):
            values = getattr(cfg, key)
            if values is None and key == "unlabeled_uris":
                values = []
            if not isinstance(values, list):
                raise ValueError(f"{key} must be a list of input paths")
            setattr(cfg, key, [_path(value, config_path.parent) for value in values])
        cfg.__post_init__()
    budget = _integer(cfg.time_budget, "time_budget", 1, 86400)
    if timeout is None:
        timeout = budget + 900
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be positive and finite")
    config = asdict(cfg)
    # The legacy, unused skeleton gate defaults to +inf. Omit that exact default
    # so JSON stays strict; ExperimentConfig restores it when loading each trial.
    if config["max_prize_skel_dist"] == math.inf:
        config.pop("max_prize_skel_dist")
    json.dumps(config, allow_nan=False)
    sources = [config_path, checkpoint, RUNNER, TRAINER]
    sources.extend((REPO / "scripts", REPO / "src", VILLA))
    for key in ("uris", "unlabeled_uris"):
        sources.extend(
            Path(value).parent for value in config[key] if not urlsplit(value).scheme
        )
    if not urlsplit(config["val_uri"]).scheme:
        sources.append(Path(config["val_uri"]).parent)
    for key in ("foundation_model_path", "pseudo_label_dir"):
        if config[key] and not urlsplit(config[key]).scheme:
            sources.append(Path(config[key]))
    output = new_output(output, *sources)
    hashes = {str(path): sha256_file(path) for path in (checkpoint, RUNNER, TRAINER)}
    hashes[str(config_path)] = config_hash
    planned = ProbePlan(
        config,
        checkpoint,
        output,
        runs,
        float(timeout),
        hashes,
        validation_protocol(cfg.depth_band),
    )
    _unchanged(planned)
    return planned


def _unchanged(plan):
    for path, expected in plan.input_hashes.items():
        if sha256_file(path) != expected:
            raise ValueError(f"input changed during probe: {path}")


def read_result(path, protocol):
    """Accept complete protocol evidence, independently of promotion success.

    The trainer's raw JSON has reported-only NaNs. Extract only validated fields;
    those raw legacy diagnostics never enter this probe's strict JSON summary.
    """
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024**2:
        raise ValueError("missing, linked or oversized run_result.json")
    result = json.loads(path.read_text())
    if not isinstance(result, dict) or result.get("val_protocol") != protocol:
        raise ValueError("result has no current validation protocol")
    diag = result.get("validation_diag")
    if (
        not isinstance(diag, dict)
        or diag.get("complete") is not True
        or diag.get("protocol") != protocol
    ):
        raise ValueError("validation sample is incomplete or has another protocol")
    requested = _integer(
        diag.get("requested_patches"), "requested_patches", 1, VALIDATION_SAMPLE_PATCHES
    )
    usable = _integer(diag.get("usable_patches"), "usable_patches", 1, requested)
    empty = _integer(
        diag.get("empty_target_patches"), "empty_target_patches", 0, requested
    )
    _integer(diag.get("batch_errors"), "batch_errors", 0, 0)
    if usable + empty != requested:
        raise ValueError("validation patch counts do not account for the whole sample")
    # What the sample was drawn from (promotion.validation_inputs_fingerprint).
    # Every trial runs the current trainer, which records it; without it, equal
    # counts from other label files would pass as one sample.
    inputs = diag.get("inputs_sha256")
    if not isinstance(inputs, str) or not inputs:
        raise ValueError("result records no validation inputs fingerprint")
    seed = _integer(
        result.get("train_sampling_seed"), "train_sampling_seed", 0, 2**31 - 1
    )
    metrics = {}
    for key in METRICS:
        value = result.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{key} must be a finite number")
        if key == "ap_prevalence_lift":
            if value < 0:
                raise ValueError("AP lift cannot be negative")
        elif not 0 <= value <= 1:
            raise ValueError(f"{key} must be in [0, 1]")
        metrics[key] = float(value)
    prevalence = metrics["val_positive_rate"]
    if not 0 < prevalence < 1 or metrics["ap_prevalence_lift"] * prevalence > 1 + 1e-9:
        raise ValueError("result has invalid prevalence or AP lift")
    return {
        "metrics": metrics,
        "validation_diag": {
            "protocol": protocol,
            "complete": True,
            "requested_patches": requested,
            "usable_patches": usable,
            "empty_target_patches": empty,
            "batch_errors": 0,
            "inputs_sha256": inputs,
        },
        "train_sampling_seed": seed,
    }


def execute(plan):
    from scripts.labeling.label_artifacts import publish_new

    supervisor = ProcessSupervisor()
    try:
        lock = acquire_lock(str(REPO / "autoresearch.lock"))
    except BlockingIOError as exc:
        raise ValueError(
            "another research process owns autoresearch.lock; stop it before executing the probe"
        ) from exc
    records = []
    interrupted = False
    try:
        _unchanged(plan)
        with publish_new(plan.output) as staging:
            for index in range(1, plan.runs + 1):
                workspace = staging / f"run_{index:02d}"
                workspace.mkdir()
                record = {
                    "run": index,
                    "directory": workspace.name,
                    "status": "FAILED",
                    "returncode": None,
                }
                started = time.monotonic()
                try:
                    _unchanged(plan)
                    copy = workspace / "best_model.pt"
                    shutil.copyfile(plan.checkpoint, copy)
                    checkpoint_hash = plan.input_hashes[str(plan.checkpoint)]
                    if sha256_file(copy) != checkpoint_hash:
                        raise ValueError("starting checkpoint changed while copying")
                    config = dict(plan.config)
                    config.update(
                        checkpoint_out=str(workspace / "candidate.pt"),
                        cache_dir=str(workspace / "cache"),
                        use_wandb=False,
                    )
                    (workspace / "config.json").write_text(
                        json.dumps(config, indent=2, allow_nan=False) + "\n"
                    )
                    (workspace / "villa").symlink_to(VILLA, target_is_directory=True)
                    (workspace / "tmp").mkdir()
                    env = dict(os.environ)
                    env.update(
                        PYTHONPATH=str(REPO),
                        PYTHONUNBUFFERED="1",
                        PYTHONDONTWRITEBYTECODE="1",
                        WANDB_MODE="disabled",
                        TMPDIR=str(workspace / "tmp"),
                        MPLCONFIGDIR=str(workspace / "matplotlib"),
                        TORCH_EXTENSIONS_DIR=str(workspace / "native_build"),
                        CUPY_CACHE_DIR=str(workspace / "cupy_cache"),
                    )
                    command = [
                        sys.executable,
                        str(RUNNER),
                        "--config",
                        str(workspace / "config.json"),
                    ]
                    record["command"] = command
                    with (workspace / "training.log").open("w") as log:
                        record["execution_attempted"] = True
                        completed = supervisor.run(
                            command,
                            timeout=plan.timeout,
                            cwd=workspace,
                            env=env,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                        )
                    record["returncode"] = completed.returncode
                    if completed.returncode != 0:
                        raise ValueError(
                            f"trainer exited {completed.returncode}; emitted scores are ineligible"
                        )
                    evidence = read_result(workspace / "run_result.json", plan.protocol)
                    candidate = workspace / "candidate.pt"
                    if (
                        candidate.is_symlink()
                        or not candidate.is_file()
                        or candidate.stat().st_size == 0
                    ):
                        raise ValueError(
                            "trainer did not produce a nonempty candidate checkpoint"
                        )
                    if sha256_file(copy) != checkpoint_hash:
                        raise ValueError("trainer modified its starting checkpoint")
                    _unchanged(plan)
                    record.update(
                        evidence,
                        status="COMPLETE",
                        checkpoint_sha256=sha256_file(candidate),
                    )
                except KeyboardInterrupt:
                    interrupted = True
                    record.update(status="INTERRUPTED", error="probe interrupted")
                except Exception as exc:
                    record["error"] = f"{type(exc).__name__}: {exc}"
                record["seconds"] = time.monotonic() - started
                records.append(record)
                if record["status"] != "COMPLETE":
                    break
            input_error = None
            try:
                _unchanged(plan)
            except Exception as exc:
                input_error = str(exc)
            complete = (
                len(records) == plan.runs
                and all(row["status"] == "COMPLETE" for row in records)
                and input_error is None
            )
            if complete:

                def sample(row):
                    return row["validation_diag"], row["metrics"]["val_positive_rate"]

                if any(sample(row) != sample(records[0]) for row in records[1:]):
                    complete = False
                    input_error = (
                        "validation inputs, sample counts or prevalence changed "
                        "between trials"
                    )
            values = [row["metrics"]["val_f1"] for row in records] if complete else []
            summary = {
                "contract": 1,
                "scope": "identical_config_repeatability",
                "status": "COMPLETE"
                if complete
                else "INTERRUPTED"
                if interrupted
                else "FAILED",
                "protocol": plan.protocol,
                "requested_runs": plan.runs,
                "execution_attempted": any(
                    row.get("execution_attempted", False) for row in records
                ),
                "tolerance_calibrated": False,
                "input_hashes": plan.input_hashes,
                "input_error": input_error,
                "config": plan.config,
                "runs": records,
                "f1_spread": {
                    "n": len(values),
                    "mean": statistics.mean(values),
                    "sample_std": statistics.stdev(values),
                    "range": max(values) - min(values),
                }
                if complete
                else None,
            }
            (staging / "probe.json").write_text(
                json.dumps(summary, indent=2, allow_nan=False) + "\n"
            )
        return summary
    finally:
        try:
            supervisor.stop()
        finally:
            lock.close()


def _interrupt(*args):
    raise KeyboardInterrupt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument(
        "--out", required=True, type=Path, help="new, source-disjoint report directory"
    )
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument(
        "--timeout", type=float, help="per-run seconds; default training budget + 900"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute training; default is a read-only plan",
    )
    args = parser.parse_args(argv)
    try:
        plan = make_plan(
            args.config, args.checkpoint, args.out, runs=args.runs, timeout=args.timeout
        )
        if args.execute:
            previous = signal.signal(signal.SIGTERM, _interrupt)
            previous_cwd = Path.cwd()
            try:
                # loop_control verifies the registered owner's checkout as well
                # as its script, so stop.sh can stop a running probe safely.
                os.chdir(REPO)
                summary = execute(plan)
            finally:
                os.chdir(previous_cwd)
                signal.signal(signal.SIGTERM, previous)
        else:
            summary = {
                "status": "DRY_RUN",
                "training_executed": False,
                "requested_runs": plan.runs,
                "timeout_seconds": plan.timeout,
                "protocol": plan.protocol,
                "output": str(plan.output),
                "input_hashes": plan.input_hashes,
                "config": plan.config,
                "note": "File identities and configuration only; checkpoint compatibility, data and GPU readiness are checked during execution.",
            }
        print(json.dumps(summary, indent=2, allow_nan=False))
        return (
            0
            if summary["status"] in {"COMPLETE", "DRY_RUN"}
            else 130
            if summary["status"] == "INTERRUPTED"
            else 1
        )
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
