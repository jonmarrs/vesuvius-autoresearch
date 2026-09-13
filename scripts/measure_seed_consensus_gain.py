"""Does averaging seeds give a more reproducible ink map, and by how much?

Implements `docs/preregistration/2026-09-13_does_averaging_seeds_help.md`.

Fits differing only by RNG seed agree on ink placement at r ~ 0.70. Two attempts
to explain that have failed; this asks the practical question instead. Leave one
arm out, and compare how well a SINGLE other arm predicts it against how well the
MEAN of the two others does.

The registration states plainly that averaging independent noise and correlating
against a third map generally wins, so the sign is near-arithmetic and the
MAGNITUDE is the result. It also names the interesting failure: a gain below +0.01
would mean the differences are not independent noise at all, because that is
precisely what averaging removes.
"""

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_ink_in_volume import corr, volume_map  # noqa: E402

WORTH_IT = 0.05
MARGINAL = 0.01


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument(
        "--arms", nargs="+", default=["curbase_s1", "curbase_s2", "curbase_s3"]
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    maps, axis = {}, None
    for tag in args.arms:
        H, axis = volume_map(f"{args.spiral_out}/outer_{tag}", axis)
        if H is None:
            print(f"{tag}: unusable, skipped")
            continue
        maps[tag] = H
    tags = list(maps)
    if len(tags) < 3:
        raise SystemExit("need three arms for leave-one-out")

    print(
        "leave-one-out: does the MEAN of two arms predict the third better than one arm does?"
    )
    print(
        f"{'held out':<16}{'single(a)':>11}{'single(b)':>11}{'consensus':>11}{'gain':>9}"
    )
    singles, gains, rows = [], [], []
    for held in tags:
        a, b = [t for t in tags if t != held]
        s_a = corr(maps[a], maps[held])
        s_b = corr(maps[b], maps[held])
        cons = corr((maps[a] + maps[b]) / 2.0, maps[held])
        gain = cons - max(
            s_a, s_b
        )  # against the BETTER single, not the mean of singles
        singles += [s_a, s_b]
        gains.append(gain)
        rows.append(
            {
                "held_out": held,
                "single_a": s_a,
                "single_b": s_b,
                "consensus": cons,
                "gain_vs_best_single": gain,
            }
        )
        print(f"{held:<16}{s_a:>11.3f}{s_b:>11.3f}{cons:>11.3f}{gain:>+9.3f}")

    mean_gain = float(np.mean(gains))
    print(
        f"\nmean single {np.mean(singles):.3f}   mean gain vs the BETTER single {mean_gain:+.3f}"
    )
    print(
        "  (compared against the better of the two singles, which is the conservative"
    )
    print(
        "   choice: a consensus that only beats the worse input is not buying anything)"
    )

    if mean_gain >= WORTH_IT:
        verdict = "WORTH IT"
        why = "averaging two seeds buys real reproducibility; the loop should keep the consensus."
    elif mean_gain >= MARGINAL:
        verdict = "MARGINAL"
        why = "real but small; not obviously worth doubling the render cost."
    else:
        verdict = "NOT WORTH IT"
        why = (
            "averaging does not stabilise the map. Since averaging is exactly what removes "
            "INDEPENDENT noise, this points at systematic per-run structure instead."
        )
    print(f"\nVERDICT: {verdict}\n  {why}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "thresholds": {"worth_it": WORTH_IT, "marginal": MARGINAL},
                    "rows": rows,
                    "mean_single": float(np.mean(singles)),
                    "mean_gain": mean_gain,
                    "verdict": verdict,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
