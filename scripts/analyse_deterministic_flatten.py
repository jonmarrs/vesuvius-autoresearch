"""Decide the deterministic-flatten bands. Committed before either surface existed.

Implements `docs/preregistration/2026-09-21_deterministic_flatten.md` and
nothing else. The two arms are flattens of one mesh set under
FLATTEN_DETERMINISTIC=1; the comparison is nearest-neighbour surface distance,
the instrument that produced the stock-mode 7.15 vx figure.

The band boundaries are the registration's. The one worth stating in code: a
result >= 1 vx WITH NO WARNINGS means the mechanism attribution in
reports/the_flatten_has_no_seed_to_set.md is wrong or incomplete, and this
script says so rather than softening it.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_flatten_divergence import nn_distance  # noqa: E402

STOCK_NN = 7.151  # reports/the_flatten_lands_on_different_surfaces.md, outer pair
STOCK_ITS = 155.0  # median stock stage0 it/s across rad0/rad0b at matched steps
WARN_RX = re.compile(r"does not have a deterministic", re.I)
ITS_RX = re.compile(r"stage0 +(\d+)/4500 +\S+ +(\S+) ")


def warnings_in(log: Path) -> list[str]:
    seen = []
    for line in log.read_text(errors="ignore").splitlines():
        if WARN_RX.search(line):
            op = line.strip()[:120]
            if op not in seen:
                seen.append(op)
    return seen


def median_its(log: Path) -> float | None:
    vals = []
    for line in log.read_text(errors="ignore").replace("\r", "\n").splitlines():
        m = ITS_RX.search(line)
        if m and int(m.group(1)) >= 900:
            try:
                vals.append(float(m.group(2)))
            except ValueError:
                pass
    if not vals:
        return None
    vals.sort()
    return vals[len(vals) // 2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="flat dir of DET-A")
    ap.add_argument("--b", required=True, help="flat dir of DET-B")
    ap.add_argument("--log", required=True, help="det_chain.log")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    d = nn_distance(args.a, args.b)
    mean = float(d.mean())
    warns = warnings_in(Path(args.log))
    its = median_its(Path(args.log))

    print("DETERMINISTIC FLATTEN: two runs of one mesh set under deterministic mode\n")
    import numpy as np

    print(
        f"  mean NN distance   {mean:.4f} vx   (p50 {float(np.percentile(d, 50)):.4f}, "
        f"p90 {float(np.percentile(d, 90)):.4f})"
    )
    print(f"  stock-mode pair    {STOCK_NN:.3f} vx")
    print(f"  ratio              {STOCK_NN / max(mean, 1e-9):,.0f}x tighter")
    print(f"  escaped-op warnings: {len(warns)}")
    for w in warns[:6]:
        print(f"     {w}")
    if its:
        print(
            f"  stage0 it/s        {its:.1f}  vs stock ~{STOCK_ITS:.0f}  -> {STOCK_ITS / its:.1f}x slower"
        )

    if mean < 0.01:
        band, read = (
            "WHOLE CAUSE",
            (
                "Reduction order is the whole cause. The flatten is reproducible when asked; "
                "the 3.04% floor becomes optional for every study, including fit comparisons, "
                "at the speed cost above."
            ),
        )
    elif mean < 1.0:
        band, read = (
            "MOSTLY",
            (
                "Determinism mode removes most of it; a residual source exists"
                + (
                    " -- the escaped ops above."
                    if warns
                    else " -- plausibly the fused Triton kernel, outside torch's determinism scope."
                )
            ),
        )
    elif warns:
        band, read = (
            "RESIDUAL NAMED",
            "The escaped ops named in the warnings are the residual source.",
        )
    else:
        band, read = (
            "ATTRIBUTION WRONG",
            (
                "Determinism mode did not act on the sources that matter, and nothing escaped. "
                "The mechanism attribution in the_flatten_has_no_seed_to_set.md is wrong or "
                "incomplete. Reported as such."
            ),
        )
    print(f"\nBAND: {band}\n  {read}")
    print(
        f"\nregistered prediction: MOSTLY (0.01-1 vx)  -> "
        f"{'MET' if band == 'MOSTLY' else 'MISS, recorded as a miss'}"
    )

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "mean_nn": mean,
                    "stock_nn": STOCK_NN,
                    "warnings": warns,
                    "its": its,
                    "band": band,
                    "prediction_met": band == "MOSTLY",
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
