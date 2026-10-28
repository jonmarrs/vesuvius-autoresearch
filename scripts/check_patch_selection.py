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
import statistics as st
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.patch_check_inputs import (
    INPUT_ERRORS,
    arm_provenance,
    read_arm,
    verify_arm,
)
from scripts.patch_dataset_artifacts import number, reference_patches

AREA_TOL_PCT = 0.5


def load_reference(path):
    _, rows = reference_patches(path)
    return (
        {pid: row[0] for pid, row in rows.items()},
        {pid: row[1] for pid, row in rows.items()},
    )


def arm_ids(dataset_dir):
    return set(read_arm(dataset_dir)["targets"])


def summarise(ids, frac, area):
    ids = sorted(ids)
    values = [frac[pid] for pid in ids]
    total = number(sum(area[pid] for pid in ids), "selection total area")
    return {
        "n": len(values),
        "mean": st.mean(values) if values else None,
        "median": st.median(values) if values else None,
        "p25": st.quantiles(values, n=4)[0] if len(values) > 1 else None,
        "area_weighted_mean": sum(frac[pid] * area[pid] for pid in ids) / total
        if total
        else None,
        "area": total,
    }


def build_report(reference, boot_dir, rand_dir, threshold=0.9):
    report = {
        "schema": "patch-selection-check-v1",
        "status": "FAIL",
        "scope": "patch_selection_input_checks",
        "scientific_validity_verified": False,
        "payload_contents_hashed": False,
        "failures": [],
        "statistics": {},
    }
    failures = report["failures"]
    try:
        number(threshold, "threshold", upper=1)
        source, rows = reference_patches(reference)
        report["reference_source"] = source.provenance()
        frac = {pid: value[0] for pid, value in rows.items()}
        area = {pid: value[1] for pid, value in rows.items()}
        captures = {"BOOTSTRAP": read_arm(boot_dir), "RANDOM": read_arm(rand_dir)}
        report["arms"] = {
            name: arm_provenance(value) for name, value in captures.items()
        }
        known = {}
        for name, captured in captures.items():
            raw = set(captured["targets"])
            unknown = raw - rows.keys()
            if unknown:
                failures.append(
                    f"{name} has {len(unknown)} patch(es) absent from the reference fit, e.g. {sorted(unknown)[:3]}; the arms must be subsets of it"
                )
            known[name] = raw & rows.keys()
            if not known[name]:
                failures.append(f"{name} must contain scored patches")
        boot, rand = known["BOOTSTRAP"], known["RANDOM"]
        below = [pid for pid in sorted(boot) if frac[pid] < threshold]
        if below:
            failures.append(
                f"BOOTSTRAP contains {len(below)} patch(es) below the {threshold} threshold (min {min(frac[pid] for pid in below):.4f}); the selection leaked"
            )
        stats = {name: summarise(ids, frac, area) for name, ids in known.items()}
        stats["ALL"] = summarise(rows, frac, area)
        for name in ("BOOTSTRAP", "RANDOM"):
            if stats[name]["area"] <= 0:
                failures.append(f"{name} must have positive total area")
        total_area = stats["ALL"]["area"]
        pb, pr = (
            100 * (stats[name]["area"] / total_area) for name in ("BOOTSTRAP", "RANDOM")
        )
        if abs(pb - pr) > AREA_TOL_PCT:
            failures.append(
                f"the arms are NOT area-matched: BOOTSTRAP {pb:.2f}% vs RANDOM {pr:.2f}% of total area, gap {abs(pb - pr):.2f} > {AREA_TOL_PCT} points. The control cannot separate evidence quality from evidence quantity."
            )
        stats.update(
            {
                "boot_area_pct": pb,
                "rand_area_pct": pr,
                "rand_below_threshold": sum(frac[pid] < threshold for pid in rand),
                "overlap": len(boot & rand),
            }
        )
        report["statistics"] = stats
        report["threshold"] = threshold
        report["area_tolerance_percentage_points"] = AREA_TOL_PCT
        source.verify()
        for captured in captures.values():
            verify_arm(captured)
    except INPUT_ERRORS as exc:
        failures.append(f"input validation failed: {exc}")
    report["status"] = "FAIL" if failures else "PASS"
    return report


def check(reference, boot_dir, rand_dir, threshold):
    report = build_report(reference, boot_dir, rand_dir, threshold)
    return report["failures"], report["statistics"]


def format_number(value, digits=4):
    return "n/a" if value is None else f"{value:.{digits}f}"


def render(report):
    stats = report["statistics"]
    if stats:
        print(f"{'set':<12}{'n':>9}{'mean':>9}{'median':>9}{'p25':>9}{'area-wtd':>10}")
        for name in ("BOOTSTRAP", "RANDOM", "ALL"):
            row = stats[name]
            print(
                f"{name:<12}{row['n']:>9,}{format_number(row['mean']):>9}{format_number(row['median']):>9}{format_number(row['p25']):>9}{format_number(row['area_weighted_mean']):>10}"
            )
        pb, pr = stats["boot_area_pct"], stats["rand_area_pct"]
        print(
            f"\narea share: BOOTSTRAP {pb:.2f}%  RANDOM {pr:.2f}% (gap {abs(pb - pr):.2f} pts, tolerance {AREA_TOL_PCT})"
        )
        print(f"overlap BOOTSTRAP & RANDOM: {stats['overlap']:,} patches")
        print(f"RANDOM patches below threshold: {stats['rand_below_threshold']:,}")
        print(
            f"mean satisfaction: BOOTSTRAP {format_number(stats['BOOTSTRAP']['mean'])}; RANDOM {format_number(stats['RANDOM']['mean'])}; ALL {format_number(stats['ALL']['mean'])}"
        )
    if report["failures"]:
        print("\nSELECTION CHECK FAILED:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    else:
        print(
            "\nselection check: PASS (subset, threshold, area-match and directory checks hold)"
        )
    print(
        "Scope: mechanical input checks; payload integrity and scientific validity are unverified."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--bootstrap", required=True)
    parser.add_argument("--random", required=True, dest="random_dir")
    parser.add_argument("--threshold", type=float, default=0.90)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one finite JSON report instead of text",
    )
    args = parser.parse_args(argv)
    report = build_report(
        args.reference, args.bootstrap, args.random_dir, args.threshold
    )
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        render(report)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
