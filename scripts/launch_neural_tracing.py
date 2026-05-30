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
heatmap checkpoint in this repo yet (only LeJEPA self-sup checkpoints). The
launcher therefore degrades gracefully: with no checkpoint, it surfaces the
plan and explains what to train (see ``villa/vesuvius/.../neural_tracing/
trainers/train_rowcol_cond.py``), and emits a marker so the evidence chain can
report the gap.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
    """Look for any locally-trained rowcol_cond / heatmap_single_point checkpoint."""
    search = [
        PROJECT_ROOT / "checkpoints" / "neural_tracing",
        PROJECT_ROOT / "checkpoints" / "rowcol_cond",
    ]
    for base in search:
        if not base.is_dir():
            continue
        for path in sorted(
            glob.glob(str(base / "**" / "*.pth"), recursive=True), reverse=True
        ):
            return Path(path)
        for path in sorted(
            glob.glob(str(base / "**" / "*.pt"), recursive=True), reverse=True
        ):
            return Path(path)
    return None


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

    checkpoint = (
        Path(args.checkpoint) if args.checkpoint else _find_neural_tracing_checkpoint()
    )

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
    ]
    if checkpoint is not None:
        cmd_parts.extend(["--checkpoint_path", str(checkpoint)])

    blockers: list[str] = []
    if volume_zarr is None or not volume_zarr.is_dir():
        blockers.append(
            "missing OME-zarr volume; pass --volume-zarr or --scroll-id/--division"
        )
    if checkpoint is None:
        blockers.append(
            f"no neural_tracing heatmap checkpoint found; train one via {TRACE_TRAINER}"
        )

    marker_path = Path(args.marker_out)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "trace_service_path": str(TRACE_SERVICE),
        "volume_zarr": str(volume_zarr) if volume_zarr else None,
        "volume_scale": args.volume_scale,
        "socket_path": str(socket_path),
        "checkpoint": str(checkpoint) if checkpoint else None,
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
