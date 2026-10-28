#!/usr/bin/env python3
"""Inspect local setup and process state without starting or changing research work.

This is a filesystem check, not training preflight: it never loads checkpoints,
volume arrays, labels, study journals, GPU libraries or network resources.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

# Direct execution works before installing the project and creates no pyc files.
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts import loop_control
from scripts.training.config import ExperimentConfig
from scripts.training.input_paths import training_label_path, validation_label_path


def inspect_workspace(repo: Path, config_path: Path = Path("config.json")) -> dict:
    """Return observations only; an idle process state is not a GPU reservation."""
    repo = repo.resolve()
    checks: list[dict] = []
    report = {
        "contract": 1,
        "repository": str(repo),
        "setup_status": "unknown",
        "training_readiness": "not_checked",
        "checks": checks,
        "limitations": [
            "Checkpoint contents, warm start and validation compatibility are not checked.",
            "Data contents, dependencies, GPU availability and memory are not checked.",
            "Process state is a snapshot; this command does not reserve the GPU.",
        ],
    }

    def add(name, status, message, path=None):
        item = {"name": name, "status": status, "message": message}
        if path is not None:
            item["path"] = str(path)
        checks.append(item)

    def finish():
        states = {item["status"] for item in checks}
        report["setup_status"] = (
            "blocked"
            if "blocked" in states
            else "unknown"
            if "unknown" in states
            else "ok"
        )
        return report

    def local_path(value, name):
        if not isinstance(value, str) or not value:
            add(name, "blocked", "Expected a nonempty local path string.")
            return None
        try:
            scheme = urlsplit(value).scheme
        except ValueError as exc:
            add(name, "blocked", f"Invalid path or URI: {exc}")
            return None
        if scheme:
            add(
                name,
                "unknown",
                "URI is not inspected; only local filesystem paths are checked.",
                value,
            )
            return None
        return repo / value

    def present(path, name, *, file=False):
        try:
            found = path.is_file() if file else path.exists()
        except OSError as exc:
            add(name, "unknown", f"Cannot inspect path: {exc}", path)
            return False
        add(
            name,
            "ok" if found else "blocked",
            "Present; contents not checked." if found else "Missing required path.",
            path,
        )
        return found

    if not repo.is_dir():
        add("repository", "blocked", "Repository directory is missing.", repo)
        return finish()
    add("repository", "ok", "Directory is present.", repo)
    try:
        paused = (repo / ".loop_paused").exists()
        if not Path("/proc/self/cwd").exists():
            raise RuntimeError("Linux /proc is unavailable")
        pid = loop_control.running_pid(repo)
        runs = loop_control.unsupervised_runs(repo, supervisor=pid)
        report["process"] = {
            "state": "running" if pid is not None else "idle",
            "pid": pid,
            "watchdog_paused": paused,
            "unsupervised_runs": [
                {"pid": p, "age_seconds": age, "supervisor_started": started}
                for p, age, started in runs
            ],
        }
        add(
            "process",
            "info",
            f"Work is running (PID {pid})."
            if pid is not None
            else "No registered work is running.",
        )
        add(
            "watchdog",
            "info",
            "Paused by .loop_paused."
            if paused
            else "Pause flag is absent; an installed watchdog may restart work.",
        )
        if runs:
            add(
                "unsupervised_runs",
                "blocked",
                "Training runs remain in this checkout: "
                + "; ".join(loop_control.describe_run(*run) for run in runs)
                + ". Inspect them before starting work.",
            )
    except (OSError, RuntimeError, ValueError) as exc:
        add("process", "unknown", f"Cannot determine process state: {exc}")

    checkpoint = repo / "best_model.pt"
    try:
        if checkpoint.is_file():
            add(
                "checkpoint",
                "info",
                "Present; contents and compatibility are unvalidated.",
                checkpoint,
            )
        elif checkpoint.exists() or checkpoint.is_symlink():
            add(
                "checkpoint",
                "blocked",
                "Checkpoint path is not an available regular file.",
                checkpoint,
            )
        else:
            add(
                "checkpoint",
                "info",
                "No incumbent file; the loop may bootstrap a first model.",
                checkpoint,
            )
    except OSError as exc:
        add(
            "checkpoint",
            "unknown",
            f"Cannot inspect checkpoint path: {exc}",
            checkpoint,
        )

    path = repo / config_path
    try:
        raw = path.read_text()
        if not isinstance(json.loads(raw), dict):
            raise ValueError("configuration must be a JSON object")
        notice = io.StringIO()
        with contextlib.redirect_stdout(notice):
            config = ExperimentConfig.from_json(raw)
        add(
            "config",
            "ok",
            "Parsed with ExperimentConfig; this does not validate all training settings.",
            path,
        )
        if notice.getvalue().strip():
            add("config_normalization", "info", notice.getvalue().strip())
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        add("config", "blocked", f"Cannot load configuration: {exc}", path)
        return finish()

    pseudo = config.pseudo_label_dir
    if pseudo:
        pseudo_path = local_path(pseudo, "pseudo_label_dir")
        if pseudo_path is None:
            return finish()
        # Keep URI spelling/basename semantics; resolving symlinks changes the
        # segment name used to choose a pseudo-label.
        config.pseudo_label_dir = str(pseudo_path)

    def volume(uri, name, *, training=False, labels=True):
        data = local_path(uri, name)
        if data is None:
            return
        present(data, name)
        if not labels:
            return
        try:
            label = (
                training_label_path(str(data), config)
                if training
                else validation_label_path(str(data))
            )
            present(Path(label), f"{name}.labels", file=True)
        except (OSError, ValueError, TypeError) as exc:
            add(f"{name}.labels", "blocked", str(exc))

    if not isinstance(config.uris, list) or not config.uris:
        add(
            "training", "blocked", "uris must be a nonempty list of local volume paths."
        )
    else:
        for index, uri in enumerate(config.uris):
            volume(uri, f"training[{index}]", training=True)
    volume(config.val_uri, "validation")
    if config.use_uamt:
        if config.unlabeled_uris and not isinstance(config.unlabeled_uris, list):
            add(
                "unlabeled",
                "blocked",
                "unlabeled_uris must be a list of local volume paths.",
            )
        elif not config.unlabeled_uris:
            add(
                "unlabeled",
                "info",
                "No unlabeled volumes after validation overlap filtering; no consistency batches will be drawn.",
            )
        else:
            for index, uri in enumerate(config.unlabeled_uris):
                volume(uri, f"unlabeled[{index}]", labels=False)
    return finish()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Configuration path, relative to --repo unless absolute.",
    )
    parser.add_argument("--json", action="store_true", help="Print one JSON report.")
    args = parser.parse_args(argv)
    report = inspect_workspace(args.repo, args.config)
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        print(f"Local setup: {report['setup_status']} ({report['repository']})")
        for item in report["checks"]:
            location = f" [{item['path']}]" if "path" in item else ""
            print(
                f"{item['status'].upper()} {item['name']}: {item['message']}{location}"
            )
        print("Training readiness: not checked.")
        for limitation in report["limitations"]:
            print(limitation)
    return {"ok": 0, "blocked": 1, "unknown": 2}[report["setup_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
