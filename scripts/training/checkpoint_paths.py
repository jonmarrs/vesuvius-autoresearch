"""Read-only path checks for experiment checkpoints and learning-curve artifacts."""

import os
import re
from pathlib import Path

from scripts.training.data_split import local_volume_path
from scripts.training.input_paths import (
    VALIDATION_LABEL_FILES,
    training_pseudo_label_path,
)
from vesuvius_autoresearch.core.prediction_artifacts import (
    validate_output_file,
    validate_plan_paths,
)
from vesuvius_autoresearch.core.volume_paths import select_local_zarr_array

# A colon starts a URL as "://", "scheme:/", or a known scheme with no slash
# (s3:bucket/x.pt). urlsplit treats the text before any colon as a scheme, so a
# local name such as run-08:00.pt would otherwise be refused. A single letter
# is a Windows drive, never a known scheme, so C:\x.pt is a local name; C:/x.pt
# is local only where Path sees a drive.
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
_URL_SCHEMES = frozenset(
    {"s3", "s3a", "s3n", "gs", "gcs", "az", "abfs", "abfss", "hf", "http", "https"}
    | {"ftp", "sftp", "file", "data"}
)

LOOP_STATE = (
    "best_model.pt",
    "last_model.pt",
    "config.json",
    "run_result.json",
    "results.tsv",
    "history.tsv",
    "prize_readiness.tsv",
    "autoresearch_history.json",
    "recent_configs.json",
    "autoresearch.lock",
    ".loop_paused",
    "cycles.jsonl",
    "config_temp.json",
    ".current_day_shift_log",
    ".best_model.pt.held",
    "autoresearch.out",
    "run.log",
    "run.log.old",
    "watchdog.log",
    "sprint_logs",
)


def _is_url(raw):
    """True for ``s3://...``, ``file:/...`` and ``s3:bucket``, not ``run-08:00.pt``."""
    raw = raw.lstrip()
    scheme = _SCHEME.match(raw)
    return "://" in raw or bool(
        scheme
        and (
            scheme[1].lower() in _URL_SCHEMES
            or (raw[scheme.end() :].startswith("/") and not Path(raw).drive)
        )
    )


def validate_checkpoint_writes(paths, *, inputs=(), base_dir=None):
    """Protect loop state and supplied inputs before creating or replacing files.

    Ordinary existing checkpoint files may be replaced; links/special files may
    not. Checks are snapshots. Callers serialize writers and recheck before saves.
    """
    base = Path.cwd() if base_dir is None else Path(base_dir)
    writes = []
    for path in paths:
        raw = os.fspath(path)
        if not raw.strip() or _is_url(raw):
            raise ValueError(
                "checkpoint outputs must be nonempty local filesystem paths, not URLs"
            )
        destination = base / raw
        try:
            info = destination.lstat()
        except FileNotFoundError:
            info = None
        if info is not None:
            validate_output_file(destination, info, label="training checkpoint")
        writes.append((destination, "training checkpoint/curve"))
    protected = [(base / name, "loop state") for name in LOOP_STATE]
    protected.extend((base / path, "training input") for path in inputs)
    validate_plan_paths(writes, protected)


def validate_training_checkpoint_writes(
    config, *, config_path=None, step=None, base_dir=None
):
    """Check configured experiment output, curve CSV and an optional step snapshot.

    Protect named local CT trees and their selected arrays, labels (including
    pseudo-labels), masks, catalogues, foundation weights and the active config.
    Remote inputs are not opened. Default loop promotion paths remain managed
    by the promotion code.
    """
    prefix = getattr(config, "checkpoint_out", None)
    paths = [prefix] if prefix else []
    if step is not None or getattr(config, "eval_every_steps", 0) > 0:
        prefix = prefix or "long_model.pt"
        paths.append(f"{prefix}.curve.csv")
        if step is not None:
            paths.append(f"{prefix}.step{step}.pt")
    if not paths:
        return
    base = Path.cwd() if base_dir is None else Path(base_dir).absolute()
    inputs = [config_path] if config_path is not None else []
    uris = list(getattr(config, "uris", None) or []) + [config.val_uri]
    if getattr(config, "use_uamt", False):
        uris += list(config.unlabeled_uris or [])
    for uri in uris:
        local = local_volume_path(uri, base_dir=base, resolve=False)
        if local is not None:
            inputs.extend((local, select_local_zarr_array(local)))
            inputs.extend(
                local.parent / name
                for name in (*VALIDATION_LABEL_FILES, "mask.png", "patches.json")
            )
        if getattr(config, "pseudo_label_dir", None):
            inputs.append(
                training_pseudo_label_path(uri, config.pseudo_label_dir, base_dir=base)
            )
    if getattr(config, "foundation_model_path", None):
        inputs.append(config.foundation_model_path)
    validate_checkpoint_writes(paths, inputs=inputs, base_dir=base)
