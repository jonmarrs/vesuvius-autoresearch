"""The frozen sheet-switch detector, and nothing else.

FROZEN 2026-08-29 in `docs/preregistration/2026-08-29_sheet_switch_detector.md`.
A patch is flagged when, over the quads the satisfaction metric ACCEPTS:

    minority_fraction = 1 - (quads on the patch's most common winding) / (satisfied quads)
    flagged  <=>  minority_fraction >= 0.10  AND  minority region >= 16 quads

No boundary-length term, no shape term, no per-patch tuning. The thresholds are
constants below and must not be swept in this file; sweeping them is how a
detector gets fitted to its own test set.

TWO THINGS THE PRE-REGISTRATION REQUIRES BE SAID WHEREVER THIS IS QUOTED:

  * the statistic was chosen AFTER seeing baseline distributions
    (`reports/sheet_switch_baseline_signal.md`). That is development, not
    validation, but it is not blind.
  * at 0.10 the baseline flag rate is 5.12%, which FAILS the pre-registered 5%
    conservativeness bar. A 0.20 threshold gives 3.74% and passes; it is not
    used, because passing would be the only reason to prefer it.

WHAT A FLAG IS NOT. It is not an established sheet switch. The baseline work
showed these regions are localized rather than full-height bands, which rules
out the theta=0 branch cut as the explanation but does not identify what they
are. Only the injection study can speak to recall.

Run:
    uv run python scripts/detect_sheet_switches.py --cache <cache.pkl> [--json-out f.json]
"""

import argparse
import json
import pickle

import numpy as np

MIN_MINORITY_FRACTION = 0.10  # frozen
MIN_MINORITY_QUADS = 16  # frozen


def flag_patches(cache):
    """Frozen rule. Returns (flagged_ids, per_patch_records)."""
    satisfied = dict(cache["satisfied"])
    flagged, records = [], []
    for pid, a in cache["patches"]:
        if a is None or a.size == 0:
            continue
        m = satisfied.get(pid)
        if m is None or m.shape != a.shape:
            continue
        ok = (a >= 0) & m
        v = a[ok]
        if v.size < MIN_MINORITY_QUADS:
            continue
        _, counts = np.unique(v, return_counts=True)
        minority = int(v.size - counts.max())
        frac = minority / v.size
        hit = frac >= MIN_MINORITY_FRACTION and minority >= MIN_MINORITY_QUADS
        records.append(
            {
                "patch": pid,
                "satisfied_quads": int(v.size),
                "minority_quads": minority,
                "minority_fraction": float(frac),
                "flagged": bool(hit),
            }
        )
        if hit:
            flagged.append(pid)
    return flagged, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    with open(args.cache, "rb") as fh:
        cache = pickle.load(fh)
    flagged, records = flag_patches(cache)
    n = len(records)
    print(f"run            {cache.get('run', '?')}")
    print(f"dr             {cache.get('dr', float('nan')):.3f}")
    print(f"patches scored {n}")
    print(f"flagged        {len(flagged)}  ({len(flagged) / max(n, 1):.2%})")
    print(
        f"thresholds     minority_fraction >= {MIN_MINORITY_FRACTION}, "
        f"minority quads >= {MIN_MINORITY_QUADS}  (FROZEN)"
    )
    print()
    print(
        "A flag is a candidate, not an established sheet switch. The 5% conservativeness"
    )
    print("bar in the pre-registration is FAILED at this threshold, by design, and the")
    print("threshold that would pass was declined because passing was its only merit.")
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(
                {
                    "run": cache.get("run"),
                    "flagged": flagged,
                    "thresholds": {
                        "minority_fraction": MIN_MINORITY_FRACTION,
                        "minority_quads": MIN_MINORITY_QUADS,
                    },
                    "records": records,
                },
                fh,
            )
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
