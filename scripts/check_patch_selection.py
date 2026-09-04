"""Verify the patch-bootstrap arms are what the registration says they are.

Run 2026-09-04, while arms 2-6 were still fitting. Everything here is an INPUT
property -- which patches went in, and how good the reference fit said they were.
No endpoint (`total_fg_pixels`, `satisfied_area_fraction`) is read, so this can be
run at any point in a study without touching the pre-committed decision rule.

It exists because `docs/preregistration/2026-09-03_patch_bootstrap.md` makes four
factual claims about datasets built hours earlier, and "the builder printed the
right number once" is not the same as "the directory on disk is still right".
This project has already retracted a finding that lived in an inline one-liner
(see scripts/measure_strip_periodicity.py), so the check is a script.

ENFORCED invariants -- these fail the run:
  1. both arms are subsets of the reference fit's patches;
  2. no BOOTSTRAP patch sits below the selection threshold;
  3. the arms match on total AREA, which is the confound the control exists to
     remove -- a count-matched control left them 76.4% vs 70.0%.

REPORTED, not enforced:
  4. the manipulation contrast (BOOT quality vs RAND quality). Reported rather
     than gated because there is no principled threshold for "enough contrast",
     and inventing one after seeing the data is how a null becomes a finding.
  5. how close RAND sits to the FULL population. The registration flagged that
     RANDOM is a single draw and an unusual one would bias the comparison; if
     RAND's quality profile matches ALL, that draw is demonstrably not extreme
     on the selection variable. It cannot speak for any other dimension.
"""

import argparse
import json
import os
import statistics as st
import sys

# Area shares are computed from the same reference json for both arms, so they
# agree to well under a point when the build is correct; the observed gap is 0.01.
# 0.5 leaves room for a rebuild without admitting the 6.4-point count-matched miss.
AREA_TOL_PCT = 0.5


def load_reference(path):
    patches = json.load(open(path))["patches"]
    return (
        {p["id"]: p["fraction"] for p in patches},
        {p["id"]: p["total_area"] for p in patches},
    )


def arm_ids(dataset_dir):
    return set(os.listdir(os.path.join(dataset_dir, "verified_patches")))


def summarise(ids, frac, area):
    v = [frac[i] for i in ids]
    tot = sum(area[i] for i in ids)
    return {
        "n": len(v),
        "mean": st.mean(v),
        "median": st.median(v),
        "p25": st.quantiles(v, n=4)[0],
        "area_weighted_mean": sum(frac[i] * area[i] for i in ids) / tot,
        "area": tot,
    }


def check(reference, boot_dir, rand_dir, threshold):
    frac, area = load_reference(reference)
    total_area = sum(area.values())
    boot_raw, rand_raw = arm_ids(boot_dir), arm_ids(rand_dir)

    failures = []
    for name, raw in (("BOOTSTRAP", boot_raw), ("RANDOM", rand_raw)):
        unknown = raw - frac.keys()
        if unknown:
            failures.append(
                f"{name} has {len(unknown)} patch(es) absent from the reference fit, "
                f"e.g. {sorted(unknown)[:3]}; the arms must be subsets of it"
            )

    boot, rand = boot_raw & frac.keys(), rand_raw & frac.keys()
    below = [i for i in boot if frac[i] < threshold]
    if below:
        failures.append(
            f"BOOTSTRAP contains {len(below)} patch(es) below the {threshold} "
            f"threshold (min {min(frac[i] for i in below):.4f}); the selection leaked"
        )

    sb = summarise(boot, frac, area)
    sr = summarise(rand, frac, area)
    sa = summarise(set(frac), frac, area)
    pb, pr = 100 * sb["area"] / total_area, 100 * sr["area"] / total_area
    if abs(pb - pr) > AREA_TOL_PCT:
        failures.append(
            f"the arms are NOT area-matched: BOOTSTRAP {pb:.2f}% vs RANDOM {pr:.2f}% "
            f"of total area, gap {abs(pb - pr):.2f} > {AREA_TOL_PCT} points. The "
            "control cannot separate evidence quality from evidence quantity."
        )

    return failures, {
        "BOOTSTRAP": sb,
        "RANDOM": sr,
        "ALL": sa,
        "boot_area_pct": pb,
        "rand_area_pct": pr,
        "rand_below_threshold": sum(1 for i in rand if frac[i] < threshold),
        "overlap": len(boot & rand),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--reference", required=True, help="reference satisfied_fitted.json"
    )
    ap.add_argument("--bootstrap", required=True, help="BOOTSTRAP dataset dir")
    ap.add_argument("--random", required=True, dest="random_dir", help="RANDOM dir")
    ap.add_argument("--threshold", type=float, default=0.90)
    args = ap.parse_args()

    failures, s = check(args.reference, args.bootstrap, args.random_dir, args.threshold)

    print(f"{'set':<12}{'n':>9}{'mean':>9}{'median':>9}{'p25':>9}{'area-wtd':>10}")
    for k in ("BOOTSTRAP", "RANDOM", "ALL"):
        r = s[k]
        print(
            f"{k:<12}{r['n']:>9,}{r['mean']:>9.4f}{r['median']:>9.4f}"
            f"{r['p25']:>9.4f}{r['area_weighted_mean']:>10.4f}"
        )

    print(
        f"\narea share: BOOTSTRAP {s['boot_area_pct']:.2f}%  "
        f"RANDOM {s['rand_area_pct']:.2f}%  "
        f"(gap {abs(s['boot_area_pct'] - s['rand_area_pct']):.2f} pts, "
        f"tolerance {AREA_TOL_PCT})"
    )
    print(f"overlap BOOTSTRAP & RANDOM: {s['overlap']:,} patches")
    print(
        f"RANDOM patches below threshold: {s['rand_below_threshold']:,} "
        "-- this is the contrast the study depends on"
    )

    d_all = abs(s["RANDOM"]["mean"] - s["ALL"]["mean"])
    print(
        f"\nmanipulation contrast: BOOTSTRAP mean {s['BOOTSTRAP']['mean']:.4f} vs "
        f"RANDOM {s['RANDOM']['mean']:.4f}"
    )
    print(
        f"RANDOM vs FULL population: {s['RANDOM']['mean']:.4f} vs "
        f"{s['ALL']['mean']:.4f} (|diff| {d_all:.4f}). A single draw that tracks the "
        "population is not an extreme draw ON THIS VARIABLE; it says nothing about "
        "any other dimension."
    )

    if failures:
        print("\nSELECTION CHECK FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nselection check: PASS (subset, threshold, area-match all hold)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
