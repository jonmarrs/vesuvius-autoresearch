#!/usr/bin/env python3
"""Launcher for villa's neural_tracing trace_service.

trace_service.py is the canonical neural_tracing entry point: a long-running
Unix-domain-socket daemon that answers heatmap-next-points, dense-displacement,
and displacement-copy queries against an OME-Zarr volume. VC3D and Crackle
Viewer can connect to it during reviewer evaluation of a candidate, turning a
raw Scroll 2/3 prediction window into an inspectable sheet-tracing view.

This launcher resolves the volume zarr from a candidate row (or the Scroll 2/3
worklist), finds a usable checkpoint if one exists locally, and prints the
exact command to start the service. It does not start the daemon by default
because trace_service is a foreground process intended to be paired with an
interactive review tool.

Status of the trace-service checkpoint: there is no trained neural_tracing
heatmap checkpoint in this repo yet (only LeJEPA self-sup checkpoints). Since
2026-06-05 the launcher falls back to villa's HuggingFace sentinel
``extrap_displacement_latest`` rather than treating that as a blocker, so a
missing local checkpoint no longer stops a launch; to train a local one see
``villa/vesuvius/.../neural_tracing/trainers/train_rowcol_cond.py``. It emits
a marker so the evidence chain can
report the gap.
"""

from __future__ import annotations

import argparse
import ast
import glob
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRACE_SERVICE = (
    PROJECT_ROOT
    / "villa"
    / "vesuvius"
    / "src"
    / "vesuvius"
    / "neural_tracing"
    / "trace_service.py"
)
TRACE_TRAINER = (
    PROJECT_ROOT
    / "villa"
    / "vesuvius"
    / "src"
    / "vesuvius"
    / "neural_tracing"
    / "trainers"
    / "train_rowcol_cond.py"
)


def _find_volume_for_candidate(
    scroll_id: str | None, division: str | None
) -> Path | None:
    """Best-effort mapping from a candidate row to a local OME-zarr."""
    local_data = PROJECT_ROOT / "local_data"
    if scroll_id and division:
        for stem in (f"{scroll_id}_Divisions", f"PHerc{scroll_id}_Divisions"):
            cand = local_data / stem / division / "0"
            if cand.is_dir():
                return cand
    if scroll_id:
        # First Scroll-level zarr we can find
        candidates = [
            local_data / f"{scroll_id}_Large" / "0",
            local_data / f"PHerc{scroll_id}_Large" / "0",
        ]
        for c in candidates:
            if c.is_dir():
                return c
    return None


def _find_neural_tracing_checkpoint() -> Path | None:
    """The newest locally-trained rowcol_cond / heatmap_single_point checkpoint.

    From the first base that holds one, its newest .pth, else its newest .pt. By
    modification time, as launch_finetune_lejepa finds its checkpoint: a name such
    as ckpt_000009 orders the iterations of one run, not the runs of a base.
    """
    search = [
        PROJECT_ROOT / "checkpoints" / "neural_tracing",
        PROJECT_ROOT / "checkpoints" / "rowcol_cond",
    ]
    for base in search:
        if not base.is_dir():
            continue
        for pattern in ("*.pth", "*.pt"):
            found = [
                Path(path)
                for path in glob.glob(str(base / "**" / pattern), recursive=True)
                if Path(path).is_file()
            ]
            if found:
                return max(found, key=lambda path: (path.stat().st_mtime_ns, str(path)))
    return None


def _checkpoint_sentinels() -> frozenset[str]:
    """The bare names villa resolves from HuggingFace, or none if unreadable.

    The keys of _CHECKPOINT_SENTINELS in the model module trace_service loads,
    neural_tracing/nets/models.py. Read from its source: importing it needs torch.
    """
    models = TRACE_SERVICE.parent / "nets" / "models.py"
    try:
        tree = ast.parse(models.read_text())
    except (OSError, SyntaxError, ValueError):
        return frozenset()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_CHECKPOINT_SENTINELS"
            for target in node.targets
        ):
            try:
                return frozenset(ast.literal_eval(node.value))
            except (TypeError, ValueError):
                return frozenset()
    return frozenset()


def _resolve_checkpoint(checkpoint: str) -> tuple[str, str | None]:
    """What the command passes for a checkpoint, and why it could not load.

    As villa's resolve_checkpoint_path (neural_tracing/nets/models.py): the text
    is stripped, and one of villa's sentinel names is passed as it is. Anything
    else is a path: an existing file, or a directory holding ckpt_*.pth (villa
    does not look in its subdirectories). The path is made absolute, so the
    command does not depend on the directory it is run from. trace_service loads
    the model lazily, so a checkpoint that resolves to nothing would fail only at
    the first request that needs the model.
    """
    text = checkpoint.strip()
    if not text:
        return checkpoint, "checkpoint is empty"
    sentinels = _checkpoint_sentinels()
    if text in sentinels:
        return text, None
    path = Path(text).absolute()
    if path.is_dir():
        if any(path.glob("ckpt_*.pth")):
            return str(path), None
        return str(path), f"checkpoint directory holds no ckpt_*.pth: {path}"
    if path.exists():
        return str(path), None
    names = ", ".join(sorted(sentinels)) or "none could be read"
    return str(path), f"checkpoint not found: {text} (villa's sentinel names: {names})"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch villa's neural_tracing trace_service for a candidate."
    )
    parser.add_argument(
        "--volume-zarr",
        type=str,
        default=None,
        help="Explicit OME-zarr path. Overrides --scroll-id/--division resolution.",
    )
    parser.add_argument("--scroll-id", type=str, default=None, help="e.g. 0125, 0332.")
    parser.add_argument("--division", type=str, default=None, help="e.g. div_90.")
    parser.add_argument(
        "--volume-scale", type=int, default=0, help="OME-Zarr scale to use."
    )
    parser.add_argument(
        "--socket-path",
        type=str,
        default=str(PROJECT_ROOT / "reports" / "neural_tracing.sock"),
        help="Unix domain socket path the service will listen on.",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=None,
        help="Optional heatmap checkpoint. If unset, the launcher will auto-discover.",
    )
    parser.add_argument(
        "--marker-out",
        type=str,
        default=str(PROJECT_ROOT / "reports" / "neural_tracing_service.json"),
    )
    args = parser.parse_args()

    if not TRACE_SERVICE.exists():
        print(f"ERROR: trace_service.py not found at {TRACE_SERVICE}", file=sys.stderr)
        return 1

    if args.volume_zarr:
        volume_zarr = Path(args.volume_zarr)
    else:
        volume_zarr = _find_volume_for_candidate(args.scroll_id, args.division)

    checkpoint_str = args.checkpoint
    if not checkpoint_str:
        local_ckpt = _find_neural_tracing_checkpoint()
        if local_ckpt:
            checkpoint_str = str(local_ckpt)
        else:
            # Fallback to Villa's built-in tracing module HuggingFace sentinel
            checkpoint_str = "extrap_displacement_latest"
    checkpoint_str, checkpoint_blocker = _resolve_checkpoint(checkpoint_str)

    socket_path = Path(args.socket_path)
    socket_path.parent.mkdir(parents=True, exist_ok=True)

    cmd_parts: list[str] = [
        sys.executable,
        str(TRACE_SERVICE),
        "--volume_zarr",
        str(volume_zarr) if volume_zarr else "<MISSING_VOLUME_ZARR>",
        "--volume_scale",
        str(args.volume_scale),
        "--socket_path",
        str(socket_path),
        "--checkpoint_path",
        checkpoint_str,
    ]

    blockers: list[str] = []
    if volume_zarr is None or not volume_zarr.is_dir():
        blockers.append(
            "missing OME-zarr volume; pass --volume-zarr or --scroll-id/--division"
        )
    if checkpoint_blocker:
        blockers.append(checkpoint_blocker)

    marker_path = Path(args.marker_out)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "trace_service_path": str(TRACE_SERVICE),
        "volume_zarr": str(volume_zarr) if volume_zarr else None,
        "volume_scale": args.volume_scale,
        "socket_path": str(socket_path),
        "checkpoint": checkpoint_str,
        "scroll_id": args.scroll_id,
        "division": args.division,
        "command": cmd_parts,
        "ready": not blockers,
        "blockers": blockers,
        "trainer_hint": str(TRACE_TRAINER),
    }
    with open(marker_path, "w") as f:
        json.dump(marker, f, indent=2)

    print(f"Marker: {marker_path}")
    if blockers:
        print("Not ready to launch trace_service:")
        for b in blockers:
            print(f"  - {b}")
    else:
        print("Ready. Start the service with:")
        print(" ", " ".join(cmd_parts))
        print(f"Then point VC3D / Crackle Viewer at the socket at {socket_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
