"""The before/after picture for docs/VILLA_DRAFT_volume_seed_heading.md: which hand-traced fiber a cube's tracing covers
with villa's 35° seed skip (finding 97's run) and without it (finding 100's `keep` arm).

A ground-truth point counts as covered as ScrollGT's fiber scorer (scoring version 3) counts it: the fiber is resampled
every 0.5 voxels and a sample is covered when a traced fiber's label, grown by the tolerance (2 voxels), reaches it.
The covered share it prints must equal the scorer's coverage in reports/neural_tracer_steep_heading.json.

    nice -n 19 .venv/bin/python scripts/villa_seed_heading_figure.py [--cube s5_16997_03997_04497_256] [--out PNG]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_ct_context as cc  # noqa: E402

T = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer")
RUNS = {
    "before": T / "ct_context_run/neural",
    "after": T / "steep_heading_run/keep",
}
TOL = 2.0


def samples(skel, grown: dict) -> tuple[np.ndarray, dict]:
    """In-cube samples of every scored fiber (zyx), their lengths, and for each run whether it covers them."""
    from scrollgt.fibers.eval_trace import _resample_fiber

    shape = next(iter(grown.values())).shape
    pts, lens = [], []
    for fiber in skel.fibers:
        for p, dl in _resample_fiber(fiber.coords, fiber.edges, step=0.5):
            if p is None:
                continue
            idx = tuple(int(round(v)) for v in p)
            if all(0 <= idx[a] < shape[a] for a in range(3)):
                pts.append(idx)
                lens.append(dl)
    pts_a, lens_a = np.array(pts), np.array(lens)
    cov = {k: g[tuple(pts_a.T)] > 0 for k, g in grown.items()}
    return np.column_stack([pts_a, lens_a]), cov


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cube", default="s5_16997_03997_04497_256")
    ap.add_argument(
        "--out", default="reports/figures/villa_volume_seed_heading_s5_16997.png"
    )
    a = ap.parse_args(argv)
    sys.path.insert(0, str(f91.SG / "src"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scrollgt.fibers.eval_trace import _dilate_labels, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    size = int(a.cube.rsplit("_", 1)[1])
    skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{a.cube}")
    labels = {
        k: cc.labels_in_cube(d / a.cube / "fibers.afv", cc.MARGIN, size)
        for k, d in RUNS.items()
    }
    grown = {k: _dilate_labels(v, TOL) for k, v in labels.items()}
    pts, cov = samples(skel, grown)
    w = pts[:, 3]
    share = {k: float(w[c].sum() / w.sum()) for k, c in cov.items()}
    scored = {
        k: score_tracing(skel, v, tolerance=TOL).as_row()["coverage"]
        for k, v in labels.items()
    }
    d = json.loads(Path("reports/neural_tracer_steep_heading.json").read_text())
    want = {
        "before": d["baseline_rows_tol2"][a.cube]["coverage"],
        "after": d["rows_tol2"]["keep"][a.cube]["coverage"],
    }
    b, f = cov["before"], cov["after"]
    kinds = {
        "covered with and without the skip": (b & f, "#4c72b0", 1.2),
        "covered only without the skip": (~b & f, "#f28e2b", 2.0),
        "covered only with the skip": (b & ~f, "#c44e52", 2.0),
        "covered by neither": (~b & ~f, "#d0d0d0", 0.8),
    }
    record = {
        "cube": a.cube,
        "tolerance": TOL,
        "covered_share": share,
        "scorer_coverage": scored,
        "json_coverage": want,
        "length_share": {
            k: float(w[m].sum() / w.sum()) for k, (m, _, _) in kinds.items()
        },
    }
    print(json.dumps(record, indent=1))
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.8), sharex=True, sharey=True)
    panels = (
        (
            f"with the 35° skip (villa main): coverage {want['before']:.3f}",
            ("covered with and without the skip", "covered only with the skip"),
        ),  # fmt: skip
        (
            f"without it (this PR): coverage {want['after']:.3f}",
            ("covered with and without the skip", "covered only without the skip"),
        ),  # fmt: skip
    )
    for ax, (title, shown) in zip(axes, panels, strict=True):
        missed = ~np.any([kinds[k][0] for k in shown], axis=0)
        ax.scatter(
            pts[missed, 2],
            pts[missed, 1],
            s=0.8,
            c="#d0d0d0",
            linewidths=0,
            label="not covered",
        )
        for k in shown:
            m, colour, s = kinds[k]
            ax.scatter(pts[m, 2], pts[m, 1], s=s, c=colour, linewidths=0, label=k)
        ax.set_title(title, fontsize=11)
        ax.set_aspect("equal")
        ax.set_xlim(0, size)
        ax.set_ylim(size, 0)
        ax.set_xlabel("x (voxels)")
        ax.legend(loc="lower left", fontsize=8, markerscale=4, frameon=True)
    axes[0].set_ylabel("y (voxels)")
    fig.suptitle(
        f"{a.cube}: hand-traced fibers (ScrollGT), projected along z; a point is covered when a traced fiber "
        f"passes within {TOL:g} voxels",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110, bbox_inches="tight")
    Path(a.out).with_suffix(".json").write_text(json.dumps(record, indent=1) + "\n")
    ok = all(abs(scored[k] - want[k]) < 5e-5 for k in want)
    print("scorer matches the JSON" if ok else "SCORER DIFFERS FROM THE JSON")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
