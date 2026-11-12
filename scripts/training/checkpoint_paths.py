"""Read-only path checks for experiment checkpoints and learning-curve artifacts."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from scripts.training.data_split import local_volume_path
from scripts.training.input_paths import VALIDATION_LABEL_FILES
from vesuvius_autoresearch.core.prediction_artifacts import (
    validate_output_file,
    validate_plan_paths,
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


def validate_checkpoint_writes(paths, *, inputs=(), base_dir=None):
    """Protect loop state and supplied inputs before creating or replacing files.

    Ordinary existing checkpoint files may be replaced; links/special files may
    not. Checks are snapshots. Callers serialize writers and recheck before saves.
    """
    base = Path.cwd() if base_dir is None else Path(base_dir)
    writes = []
    for path in paths:
        raw = os.fspath(path)
        if not raw.strip() or urlsplit(raw).scheme:
            raise ValueError(
                "checkpoint outputs must be nonempty local filesystem paths"
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

    Protect named local CT trees, labels (including pseudo-labels), masks,
    catalogues, foundation weights and the active config. Remote inputs are not
    opened. Default loop promotion paths remain managed by the promotion code.
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
            inputs.append(local)
            inputs.extend(
                local.parent / name
                for name in (*VALIDATION_LABEL_FILES, "mask.png", "patches.json")
            )
        if getattr(config, "pseudo_label_dir", None):
            segment = os.path.basename(os.path.dirname(uri.rstrip("/")))
            inputs.append(Path(config.pseudo_label_dir) / f"{segment}_pseudo.png")
    if getattr(config, "foundation_model_path", None):
        inputs.append(config.foundation_model_path)
    validate_checkpoint_writes(paths, inputs=inputs, base_dir=base)
