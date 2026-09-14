"""Calibrated consensus re-test: does a 3-seed consensus reproduce at 0.877?

Implements `docs/preregistration/2026-09-14_consensus_retest_calibrated.md`,
written while `curbase_s7` is mid-fit and neither new comparison exists.

The previous attempt returned VOID because its ink gate was calibrated from three
arms (CV 0.0124) and applied to six (CV 0.0740), rejecting an arm with no
independent sign of being wrong. Two things are different here:

* **The gate is a 95% prediction interval for a new draw from the six existing
  arms**, so it contains every arm the process has actually produced, `s6`
  included. A gate that rejects a real arm is a broken gate.
* **The A-vs-B comparison is RETIRED.** It was computed and seen at 0.876. This
  module refuses to compute it -- not by convention but structurally -- because
  re-reporting a number already seen, under a gate widened afterwards, would be
  choosing a threshold to admit the answer.

Two forward comparisons remain, A-vs-C and B-vs-C. Both are reported. If they
disagree the verdict is INCONSISTENT and neither is claimed; they exist to make
that visible, not to let the better one be picked.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_ink_in_volume import corr, volume_map  # noqa: E402

TRIPLETS = {
    "A": ("curbase_s1", "curbase_s2", "curbase_s3"),
    "B": ("curbase_s4", "curbase_s5", "curbase_s6"),
    "C": ("curbase_s7", "curbase_s8", "curbase_s9"),
}
# Computed and seen at 0.876 before this registration existed. Never re-reported.
RETIRED = frozenset({frozenset({"A", "B"})})
COMPARISONS = (("A", "C"), ("B", "C"))

PREDICTED = 0.877
CONFIRM = (0.85, 0.91)
PARTIAL = (0.79, 0.85)
REFUTE_BELOW = 0.79

# 95% prediction interval for a new draw from s1-s6 (mean 3,019,001, sd 223,329,
# n=6, t=2.571). Contains all six existing arms including s6.
#
# THE QUANTITY MATTERS. These constants were computed from `total_fg_pixels` in
# `<arm>/ink_metric/metrics.json`, whose s1-s6 mean is 3,019,001 exactly. An
# earlier version of this module gated `H.sum()` from the volume map instead,
# which runs ~0.2% lower on every arm because the histogram's validity mask drops
# non-finite and non-positive coordinates. Immaterial against a +/-20% gate, and
# no arm's verdict changed -- but calibrating on one quantity and gating another
# is the exact class of error that voided the previous run, so it is fixed here
# rather than tolerated. The gate is applied to the quantity it was calibrated
# on; H.sum() is still reported as a diagnostic.
GATE_INK = (2_398_918.0, 3_639_084.0)
GATE_SOURCE = "ink_metric/metrics.json:summary.total_fg_pixels"
GATE_NONBLANK = (0.40, 0.55)


def verdict_one(r: float) -> str:
    if r > CONFIRM[1]:
        return "BETTER THAN PREDICTED"
    if CONFIRM[0] <= r <= CONFIRM[1]:
        return "CONFIRMED"
    if PARTIAL[0] <= r < CONFIRM[0]:
        return "PARTIAL"
    return "REFUTED"


def combine(verdicts: list[str]) -> tuple[str, str]:
    """Both comparisons must agree. Disagreement is reported, not resolved."""
    good = {"CONFIRMED", "BETTER THAN PREDICTED"}
    if all(v in good for v in verdicts):
        return "CONFIRMED", (
            "both forward comparisons land in the predicted band; the "
            "independent-noise model predicts k-seed consensus reproducibility."
        )
    if all(v == "REFUTED" for v in verdicts):
        return "REFUTED", (
            "both comparisons fall below the floor averaging should reach. The "
            "k-seed projection is WITHDRAWN, not qualified."
        )
    if len(set(verdicts)) == 1:
        return verdicts[0], "both comparisons agree on this outcome."
    return "INCONSISTENT", (
        f"the two forward comparisons disagree ({', '.join(verdicts)}). Neither is "
        "claimed. Two comparisons exist to make this visible, not to let one be picked."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    needed = [a for t in TRIPLETS.values() for a in t]
    maps, ink, fg, axis, missing, no_metrics = {}, {}, {}, None, [], []
    for tag in needed:
        H, axis = volume_map(f"{args.spiral_out}/outer_{tag}", axis)
        if H is None:
            missing.append(tag)
            continue
        maps[tag], ink[tag] = H, float(H.sum())
        mp = Path(f"{args.spiral_out}/outer_{tag}/ink_metric/metrics.json")
        if not mp.exists():
            no_metrics.append(tag)
            continue
        fg[tag] = float(json.loads(mp.read_text())["summary"]["total_fg_pixels"])
    if missing:
        raise SystemExit(
            f"not scored yet: {', '.join(missing)}. A partial sample is refused, "
            "not reported."
        )
    if no_metrics:
        raise SystemExit(
            f"rendered but no {GATE_SOURCE} for: {', '.join(no_metrics)}. The gate "
            "is calibrated on that quantity and will not fall back to another."
        )

    print(f"{'arm':<16}{'total_fg_pixels':>18}{'H.sum() (diag)':>18}")
    for t in needed:
        print(f"{t:<16}{fg[t]:>18,.0f}{ink[t]:>18,.0f}")

    # ---- validity gate, calibrated before any comparison -----------------
    gate = [t for t, v in fg.items() if not (GATE_INK[0] <= v <= GATE_INK[1])]
    print(
        f"\nvalidity gate: {GATE_SOURCE} within "
        f"{GATE_INK[0]:,.0f}-{GATE_INK[1]:,.0f} (95% PI from s1-s6)"
    )
    print(f"  {'all arms inside' if not gate else 'OUTSIDE: ' + ', '.join(gate)}")

    # ---- the two forward comparisons -------------------------------------
    cons = {k: np.mean([maps[t] for t in v], axis=0) for k, v in TRIPLETS.items()}
    rows, verdicts = [], []
    print(f"\n{'comparison':<18}{'r':>8}{'predicted':>11}{'verdict':>24}")
    for a, b in COMPARISONS:
        assert frozenset({a, b}) not in RETIRED, f"{a}-vs-{b} is retired"
        r = corr(cons[a], cons[b])
        v = verdict_one(r)
        verdicts.append(v)
        rows.append({"pair": f"{a}-{b}", "r": r, "verdict": v})
        print(f"{a + ' vs ' + b:<18}{r:>8.3f}{PREDICTED:>11.3f}{v:>24}")

    if gate:
        tag, why = (
            "VOID",
            (
                f"ink outside the calibrated interval: {', '.join(gate)}. This is NOT "
                "a null result."
            ),
        )
    else:
        tag, why = combine(verdicts)
    print(f"\nVERDICT: {tag}\n  {why}")
    print(
        f"\nregistered prediction {PREDICTED:.3f}: "
        f"{'MET' if tag in ('CONFIRMED', 'BETTER THAN PREDICTED') else 'not met'}"
    )
    print("A-vs-B is retired at 0.876 and is not part of this test.")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "predicted": PREDICTED,
                    "confirm": CONFIRM,
                    "gate_ink": GATE_INK,
                    "comparisons": rows,
                    "total_fg_pixels": fg,
                    "h_sum_diagnostic": ink,
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
