"""Finding 111, after the verdict: descriptions that are not part of the registered table.

Per-model AUC at the chosen depth and side, a block-bootstrap spread of the ensemble's AUC, the AUC with the
map moved by a few cells, and a figure of
each held-out segment's ensemble map beside the team's labels. Nothing here can change the verdict.

usage: describe.py OUT.json FIGURE_DIR --choice sweep.json --segment NAME MESH MAPS RENDER LABELS [...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import surface_control as sc  # noqa: E402
from surface_control import analysis, transfer_maps  # noqa: E402

BLOCK_CELLS = 64  # 256 render pixels a side: the unit resampled by the bootstrap
DRAWS = 500
SHIFT_MAX, SHIFT_STEP = 6, 2  # lattice cells; one cell is 4 render pixels


def block_bootstrap(
    score: np.ndarray, scored: np.ndarray, ink: np.ndarray, rng: np.random.Generator
) -> dict:
    """2.5th and 97.5th percentile of the AUC when whole blocks of the lattice are resampled with replacement."""
    rows, cols = np.nonzero(scored)
    block = (rows // BLOCK_CELLS) * 100000 + cols // BLOCK_CELLS
    order = np.argsort(block, kind="stable")
    ids, starts = np.unique(block[order], return_index=True)
    groups = np.split(order, starts[1:])
    values, labels = score[scored], ink[scored]
    draws = []
    for _ in range(DRAWS):
        take = np.concatenate([groups[i] for i in rng.integers(0, len(ids), len(ids))])
        value = sc.auc(values[take], labels[take])
        if value is not None:
            draws.append(value)
    low, high = np.percentile(draws, [2.5, 97.5])
    return {
        "blocks": int(len(ids)),
        "draws": len(draws),
        "low": round(float(low), 4),
        "high": round(float(high), 4),
    }


def shift_scan(segment: sc.Segment, score: np.ndarray) -> dict:
    """AUC with the map moved by up to SHIFT_MAX cells each way: is the map where the labels are?"""
    best = (-1.0, 0, 0)
    for dr in range(-SHIFT_MAX, SHIFT_MAX + 1, SHIFT_STEP):
        for dc in range(-SHIFT_MAX, SHIFT_MAX + 1, SHIFT_STEP):
            moved = np.roll(score, (dr, dc), axis=(0, 1))
            both = np.roll(segment.render_ok, (dr, dc), axis=(0, 1)) & segment.scored
            value = sc.auc(moved[both], segment.ink[both])
            if value is not None and value > best[0]:
                best = (value, dr, dc)
    return {"best_auc": round(best[0], 4), "rows": best[1], "cols": best[2]}


def per_model(segment: sc.Segment, depth: int, reading: bool) -> dict:
    name = segment.render.name.removesuffix(".zarr")
    out = {}
    for model in analysis.MODELS:
        one = transfer_maps.read_map(
            transfer_maps.map_file(segment.maps, name, model, reading, depth),
            model,
            segment.canvas,
        )
        score = analysis.highpass(one.astype(np.float64), segment.render_ok)
        out[model] = round(
            sc.auc(score[segment.scored], segment.ink[segment.scored]), 4
        )
    return out


def figure(segment: sc.Segment, score: np.ndarray, path: Path) -> list[int]:
    """The ensemble beside the labels over the bounding box of the scored cells. Returns that box."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows, cols = np.nonzero(segment.scored)
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    crop = (slice(r0, r1), slice(c0, c1))
    shown = np.where(segment.render_ok[crop], score[crop], np.nan)
    low, high = np.nanpercentile(shown, [2, 98])
    label = np.full(shown.shape, 0.5)
    label[segment.scored[crop] & segment.ink[crop]] = 0.0
    label[segment.scored[crop] & ~segment.ink[crop]] = 1.0
    fig, axes = plt.subplots(
        1, 2, figsize=(14, 14 * shown.shape[0] / shown.shape[1] / 2 + 0.6)
    )
    axes[0].imshow(-shown, cmap="gray", vmin=-high, vmax=-low, interpolation="nearest")
    axes[0].set_title("four-model ensemble (dark = ink-like)")
    axes[1].imshow(label, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    axes[1].set_title("team labels: black ink, white bare, grey not scored")
    for ax in axes:
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return [int(r0), int(r1), int(c0), int(c1)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("figures")
    ap.add_argument("--choice", required=True)
    ap.add_argument("--segment", nargs=5, action="append", required=True)
    args = ap.parse_args(argv)
    chosen = json.loads(Path(args.choice).read_text())["chosen"]
    depth, reading = chosen["depth"], chosen["side"] == "reverse"
    rng = np.random.default_rng(0)
    result: dict = {"chosen": chosen, "block_cells": BLOCK_CELLS, "segments": {}}
    Path(args.figures).mkdir(parents=True, exist_ok=True)
    for values in args.segment:
        segment = sc._segment(values)
        score = segment.score_map(depth, reading)
        short = "s" + segment.name.split("-")[0]
        result["segments"][segment.name] = {
            "auc": round(sc.auc(score[segment.scored], segment.ink[segment.scored]), 4),
            "block_bootstrap": block_bootstrap(score, segment.scored, segment.ink, rng),
            "per_model": per_model(segment, depth, reading),
            "shift_scan": shift_scan(segment, score),
            "figure_box_cells": figure(
                segment, score, Path(args.figures) / f"first_letters_0841_{short}.png"
            ),
        }
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
