"""Forward test: does a 3-seed consensus reproduce at the predicted 0.884?

Implements `docs/preregistration/2026-09-13_consensus_forward_prediction.md`,
and is committed while `curbase_s4` is still fitting -- before any of the three
new arms exists.

The independent-noise model, replicated on three triplets, predicts that a k-seed
consensus reproduces against an independent k-seed consensus at
r = 1 / (1 + 0.393/k). For k = 3 that is 0.884, against 0.718 measured for
singles. Allowing the ~12% excess seen at k = 2, the supported band is
0.884-0.904.

Two things decide the outcome and they are kept separate on purpose:

* the **validity gate** -- does this comparison mean anything at all;
* the **decision rule** -- given that it does, what does the number say.

The gate exists because `reports/the_sanity_check_caught_a_false_positive.md`
records a decision rule reporting a significant artefact three times over. A gate
failure yields VOID, which is not a null and must never be reported as one.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_ink_in_volume import corr, volume_map  # noqa: E402

TRIPLET_A = ("curbase_s1", "curbase_s2", "curbase_s3")
TRIPLET_B = ("curbase_s4", "curbase_s5", "curbase_s6")

PREDICTED = 0.884
BAND = (0.884, 0.904)
CONFIRM = (0.86, 0.92)
PARTIAL = (0.80, 0.86)
REFUTE_BELOW = 0.80

GATE_SINGLE = (0.65, 0.78)  # cross-triplet single-vs-single must land here
GATE_INK = (2.70e6, 3.05e6)  # current-tier spread of total_fg_pixels


def verdict(r: float) -> tuple[str, str]:
    """The registered rule. Gate is applied separately and can override to VOID."""
    if r > CONFIRM[1]:
        return "BETTER THAN PREDICTED", (
            "the noise is more averageable than the model says; the ~12% excess is "
            "larger at k=3 than at k=2."
        )
    if CONFIRM[0] <= r <= CONFIRM[1]:
        return "CONFIRMED", (
            "seed differences are independent noise and averaging is the right "
            "response to them."
        )
    if PARTIAL[0] <= r < CONFIRM[0]:
        return "PARTIAL", (
            "averaging helps but less than independence predicts, implying some "
            "shared per-run structure."
        )
    return "REFUTED", (
        "a floor this high at k=3 means a systematic component averaging cannot "
        "remove. The k-seed projection must be WITHDRAWN, not qualified."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    maps, ink, axis = {}, {}, None
    missing = []
    for tag in TRIPLET_A + TRIPLET_B:
        H, axis = volume_map(f"{args.spiral_out}/outer_{tag}", axis)
        if H is None:
            missing.append(tag)
            continue
        maps[tag] = H
        ink[tag] = float(H.sum())

    if missing:
        raise SystemExit(
            f"not scored yet: {', '.join(missing)}. A partial sample is refused, "
            "not reported."
        )

    print(f"{'arm':<16}{'ink in map':>14}")
    for t in TRIPLET_A + TRIPLET_B:
        print(f"{t:<16}{ink[t]:>14,.0f}")

    # ---- validity gate -------------------------------------------------
    cross = [corr(maps[a], maps[b]) for a in TRIPLET_A for b in TRIPLET_B]
    mean_cross = float(np.mean(cross))
    gate = []
    if not (GATE_SINGLE[0] <= mean_cross <= GATE_SINGLE[1]):
        gate.append(
            f"cross-triplet single-vs-single {mean_cross:.3f} outside {GATE_SINGLE}"
        )
    out_of_spread = [t for t, v in ink.items() if not (GATE_INK[0] <= v <= GATE_INK[1])]
    if out_of_spread:
        gate.append(f"ink outside the current-tier spread: {', '.join(out_of_spread)}")

    print("\nvalidity gate")
    print(
        f"  cross-triplet single-vs-single: {mean_cross:.3f}  "
        f"(must be in {GATE_SINGLE})"
    )
    print(
        f"  ink within current-tier spread: "
        f"{'all arms' if not out_of_spread else 'FAILED: ' + ', '.join(out_of_spread)}"
    )

    # ---- the forward comparison ----------------------------------------
    cons_a = np.mean([maps[t] for t in TRIPLET_A], axis=0)
    cons_b = np.mean([maps[t] for t in TRIPLET_B], axis=0)
    r = corr(cons_a, cons_b)

    print(f"\n{'quantity':<44}{'value':>9}")
    print(f"{'single vs single (cross-triplet, mean of 9)':<44}{mean_cross:>9.3f}")
    print(f"{'CONSENSUS vs CONSENSUS (3 seeds each)':<44}{r:>9.3f}")
    print(f"{'predicted by the independent-noise model':<44}{PREDICTED:>9.3f}")
    print(f"{'registered supported band':<44}{f'{BAND[0]:.3f}-{BAND[1]:.3f}':>9}")

    if gate:
        tag, why = "VOID", "; ".join(gate)
        print(f"\nVERDICT: VOID -- {why}")
        print("  This is NOT a null result. The comparison does not mean anything.")
    else:
        tag, why = verdict(r)
        print(f"\nVERDICT: {tag}\n  {why}")
        print(
            f"\nregistered prediction {PREDICTED:.3f}: "
            f"{'MET' if tag in ('CONFIRMED', 'BETTER THAN PREDICTED') else 'MISS, recorded as a miss'}"
        )

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "predicted": PREDICTED,
                    "band": BAND,
                    "r_consensus": r,
                    "mean_cross_single": mean_cross,
                    "ink": ink,
                    "gate_failures": gate,
                    "verdict": tag,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
