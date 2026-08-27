"""The track metric has the same blindness, and here it is measured.

CONTEXT. On villa issue #1621, @Bullo27 reproduced the patch-satisfaction
blindness through villa's native `unwrap_targets`, sharpened the acceptance edge
to the tolerance itself by bisection, and then found something that was not in
our write-up: `get_track_satisfied_counts` builds its target the same
self-referential way. They flagged that half explicitly as a code-and-algebra
claim rather than a measurement, saying it would need a fit context to execute.

It does not. This runs it.

WHAT IS RUN. villa's own unmodified `tracks.get_track_satisfied_counts`, and the
chunked wrapper `get_track_satisfied_counts_in_chunks` that `satisfaction_metrics`
actually imports, on a synthetic track lying on winding 40 at dr = 12.81,
displaced by whole and half windings. No reimplementation of the snap.

THE CONTROL IS THE POINT. Half-winding displacements must drive the satisfied
count to zero. If they did not, the harness would be inert and the zeros on whole
windings would mean nothing. This is the same discipline as the patch probe, and
the reason its zeros are informative.

WHAT THIS ADDS BEYOND THE ALGEBRA. Two things the source reading alone does not
show:

  * `get_track_satisfied_counts` already returns `mode_winding_per_track`, and it
    tracks the displacement exactly: 40, 41, 42, 63 for displacements of 0, 1, 2
    and 23 windings. The metric therefore *computes and hands back* the number
    that would expose the displacement, and simply never compares it to
    anything.
  * `get_track_satisfied_counts_in_chunks` -- the entry point
    `satisfaction_metrics.py` imports -- discards it: it unpacks five values and
    returns two, keeping the counts and dropping the winding. So the quantity a
    conservative failure check needs exists one call below the boundary and is
    thrown away at it.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_track_satisfaction_winding.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402
import torch  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
sys.path.insert(
    0, os.path.join(_REPO, "villa", "volume-cartographer", "scripts", "spiral")
)

from probe_spiral_satisfaction_winding import IdentityTransform  # noqa: E402
from tracks import (  # noqa: E402  # type: ignore[import-not-found]
    get_track_satisfied_counts,
    get_track_satisfied_counts_in_chunks,
)

DR = 12.81
WINDING = 40
N_POINTS = 24
THETA0, THETA1 = 0.30, 1.30
DISPLACEMENTS = [0.0, 0.5, 1.0, 2.0, 5.5, 23.0]
REPORTING = {
    "satisfaction_radius_tolerance": 0.45,
    "satisfaction_distance_tolerance": 6.0,
    "satisfied_patch_quad_fraction": 0.95,
    "boundary_satisfied_patch_quad_fraction": 0.90,
}
SPLICING = {
    "satisfaction_radius_tolerance": 0.495,
    "satisfaction_distance_tolerance": 12.0,
    "satisfied_patch_quad_fraction": 0.90,
}
OUT = os.path.join(_REPO, "reports", "track_satisfaction_winding.txt")


def track_on(winding, n=N_POINTS):
    """A track lying exactly on `winding`, in the same construction as the patch probe."""
    th = np.linspace(THETA0, THETA1, n)
    r = winding * DR + th / (2 * np.pi) * DR
    return np.stack(
        [np.full_like(th, 1000.0), np.sin(th) * r, np.cos(th) * r], axis=-1
    ).astype(np.float32)


def score(displacement, cfg):
    idx, sat, lens, per_point, mode = get_track_satisfied_counts(
        IdentityTransform(), torch.tensor(DR), [track_on(WINDING + displacement)], cfg
    )
    return int(sat[0]), int(lens[0]), int(mode[0])


def score_chunked(displacement, cfg):
    sat, tot = get_track_satisfied_counts_in_chunks(
        IdentityTransform(), torch.tensor(DR), [track_on(WINDING + displacement)], cfg
    )
    return int(sat[0]), int(tot[0])


def main():
    lines = [
        "The track metric has the same blindness, measured rather than argued",
        "",
        "@Bullo27 found this by reading tracks.py and flagged it as algebra, not a",
        "measurement, saying it would need a fit context. It does not: villa's own",
        "get_track_satisfied_counts runs on a synthetic track directly.",
        "",
        f"  track on winding {WINDING}, dr = {DR}, {N_POINTS} points,"
        f" theta {THETA0} to {THETA1}",
        "  villa's unmodified tracks.py; no reimplementation of the snap",
        "",
    ]
    for name, cfg in (("reporting", REPORTING), ("splicing", SPLICING)):
        lines.append(f"=== {name} config ===")
        lines.append("   displacement   satisfied   mode_winding   note")
        lines.append("  " + "-" * 62)
        for d in DISPLACEMENTS:
            sat, tot, mode = score(d, cfg)
            note = "<- CONTROL, rejects" if abs(d - round(d)) > 1e-9 else ""
            lines.append(
                f"   {d:9.1f}      {sat:3d}/{tot:<3d}      {mode:6d}       {note}"
            )
        lines.append("")

    lines += [
        "The controls are what make the zeros mean something: half-winding displacements",
        "drive the satisfied count to zero under both configs, so the harness can produce",
        "a rejection. Whole and double windings, and 23 windings, leave it untouched.",
        "",
        "=== Through the entry point satisfaction_metrics.py actually imports ===",
    ]
    for d in DISPLACEMENTS:
        sat, tot = score_chunked(d, REPORTING)
        lines.append(
            f"   get_track_satisfied_counts_in_chunks, {d:5.1f} -> {sat}/{tot}"
        )
    lines += [
        "",
        "Two things the source reading alone does not show.",
        "",
        "  The mode_winding column tracks the displacement exactly: 40, 41, 42, 63 for 0,",
        "  1, 2 and 23 windings. The metric COMPUTES AND RETURNS the number that would",
        "  expose the displacement. It simply never compares it to anything.",
        "",
        "  And get_track_satisfied_counts_in_chunks discards it. It unpacks five values",
        "  and returns two, keeping the counts and dropping the winding. So the quantity a",
        "  conservative failure check needs already exists one call below the boundary and",
        "  is thrown away at it. For tracks the proposed fix is cheaper than for patches:",
        "  the caller does not need to derive anything, only to stop discarding it.",
        "",
        "Limits. Synthetic flat track, one geometry, displacement varied and shape not.",
        "No fit was run. This measures what the metric does with a track placed on a",
        "winding; it says nothing about how often a real fit misplaces one.",
    ]
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
