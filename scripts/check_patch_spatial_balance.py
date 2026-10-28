"""Describe patch area by radial proxy using complete, validated input geometry.

The area-weighted centre and band cuts come from BOOTSTRAP | RANDOM. Optional
ALL uses the scored reference population on those same axes. Area is spread
across each bbox's radial extent, not assigned to a centroid. The proxy assumes
uniform area in radius and does not establish winding calibration.

This reports diagnostics without a spatial-balance acceptance threshold.
Input errors fail the command; successful diagnostics do not certify study
validity, payload integrity or scientific improvement. --json emits one report.
"""

import argparse
import json
import math
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
from scripts.patch_dataset_artifacts import (
    fingerprint,
    geometry,
    number,
    reference_patches,
    verify_geometry,
)

N_BANDS = 10


def load_boxes(dataset_dir, ids):
    """Read every requested bbox; missing/invalid geometry fails explicitly."""
    return geometry(Path(dataset_dir), ids)[0]


def radial_extent(box, cx, cy):
    """(r_min, r_max) of an axis-aligned XY footprint about (cx, cy).

    r_min is 0 when the centre lies inside the footprint; otherwise it is the
    distance to the nearest edge or corner. r_max is always a corner.
    """
    (x0, y0, _), (x1, y1, _) = box
    dx = max(x0 - cx, 0.0, cx - x1)
    dy = max(y0 - cy, 0.0, cy - y1)
    r_min = (dx * dx + dy * dy) ** 0.5
    r_max = max(
        ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x in (x0, x1) for y in (y0, y1)
    )
    return r_min, r_max


def _band_count(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1000:
        raise ValueError("band count must be an integer in 1..1000")
    return value


def _population(ids, extent, area):
    ids = sorted(ids)
    if not ids:
        raise ValueError("radial population must be nonempty")
    for pid in ids:
        if pid not in extent or pid not in area:
            raise ValueError(f"missing radial extent or area for {pid}")
        lo, hi = extent[pid]
        number(lo, "radial minimum")
        number(hi, "radial maximum", lower=lo)
        number(area[pid], "patch area")
    total = number(sum(area[pid] for pid in ids), "radial population area")
    if total <= 0:
        raise ValueError("radial population area must be positive")
    return ids, total


def radial_bands(extent, area, n_bands=N_BANDS):
    """Return n-1 weighted midpoint cuts, repeating cuts for coarse populations."""
    n_bands = _band_count(n_bands)
    ids, total = _population(extent, extent, area)
    midpoint = {pid: extent[pid][0] / 2 + extent[pid][1] / 2 for pid in ids}
    order = sorted(ids, key=lambda pid: (midpoint[pid], pid))
    edges, accumulated = [], 0.0
    step = total / n_bands
    if not math.isfinite(step) or step <= 0:
        raise ValueError("population cannot define positive finite band weights")
    for pid in order:
        accumulated += area[pid]
        while len(edges) < n_bands - 1 and accumulated >= step * (len(edges) + 1):
            edges.append(midpoint[pid])
    if len(edges) != n_bands - 1:
        raise ValueError("population did not define all requested radial cuts")
    return edges


def area_share_by_band(ids, extent, edges, area, n_bands=N_BANDS):
    """Spread areas across fixed cuts; point extents on a cut use its lower band."""
    n_bands = _band_count(n_bands)
    ids, total = _population(ids, extent, area)
    if len(edges) != n_bands - 1:
        raise ValueError("radial cuts must match the requested band count")
    previous = 0.0
    for edge in edges:
        number(edge, "radial cut", lower=previous)
        previous = edge
    bounds = [0.0, *edges, float("inf")]
    per = [0.0] * n_bands
    for pid in ids:
        lo, hi = extent[pid]
        span = hi - lo
        if span == 0:
            per[min(sum(lo > edge for edge in edges), n_bands - 1)] += area[pid]
        else:
            for band in range(n_bands):
                overlap = min(hi, bounds[band + 1]) - max(lo, bounds[band])
                if overlap > 0:
                    per[band] += area[pid] * (overlap / span)
    return [value / total for value in per], total


def build_report(reference, boot_dir, rand_dir, full=None):
    report = {
        "schema": "patch-spatial-diagnostic-v1",
        "status": "FAIL",
        "scope": "radial_proxy_input_diagnostic",
        "balance_verdict": "not_assessed",
        "winding_calibration_verified": False,
        "scientific_validity_verified": False,
        "payload_contents_hashed": False,
        "failures": [],
        "warnings": [],
    }
    try:
        source, rows = reference_patches(reference)
        area = {pid: value[1] for pid, value in rows.items()}
        captures = {"BOOTSTRAP": read_arm(boot_dir), "RANDOM": read_arm(rand_dir)}
        ids = {name: set(value["targets"]) for name, value in captures.items()}
        for name, values in ids.items():
            if not values or values - rows.keys():
                raise ValueError(f"{name} must be nonempty and contain only scored IDs")
        boxes, geometry_sources = {}, []
        for name, captured in captures.items():
            current, records = geometry(Path(captured["path"]), ids[name])
            for pid, box in current.items():
                if pid in boxes and boxes[pid] != box:
                    raise ValueError(f"conflicting geometry for shared patch {pid}")
                boxes[pid] = box
            geometry_sources.extend(records)
        union = sorted(boxes)
        total_union = number(sum(area[pid] for pid in union), "union area")
        if total_union <= 0:
            raise ValueError("union area must be positive")
        center = [
            sum(
                (boxes[pid][0][axis] / 2 + boxes[pid][1][axis] / 2)
                * (area[pid] / total_union)
                for pid in union
            )
            for axis in (0, 1)
        ]
        for value in center:
            number(value, "radial centre", lower=None)
        extent = {pid: radial_extent(boxes[pid], *center) for pid in union}
        edges = radial_bands(extent, area)
        shares, totals = {}, {}
        for name, values in ids.items():
            shares[name], totals[name] = area_share_by_band(values, extent, edges, area)
        if full is not None:
            captured = read_arm(full)
            if rows.keys() - captured["targets"].keys():
                raise ValueError("FULL dataset is missing scored patches")
            full_boxes, records = geometry(Path(captured["path"]), rows)
            for pid, box in boxes.items():
                if full_boxes[pid] != box:
                    raise ValueError(f"FULL geometry conflicts with arm patch {pid}")
            geometry_sources.extend(records)
            full_extent = {
                pid: radial_extent(box, *center) for pid, box in full_boxes.items()
            }
            shares["ALL"], totals["ALL"] = area_share_by_band(
                rows, full_extent, edges, area
            )
            captures["ALL"] = captured
        bands = []
        for index in range(N_BANDS):
            row = {
                "index": index,
                "radius_lower": 0.0 if index == 0 else edges[index - 1],
                "radius_upper": edges[index] if index < len(edges) else None,
                "bootstrap_share": shares["BOOTSTRAP"][index],
                "random_share": shares["RANDOM"][index],
                "bootstrap_minus_random_pp": 100
                * (shares["BOOTSTRAP"][index] - shares["RANDOM"][index]),
            }
            if "ALL" in shares:
                row["reference_population_share"] = shares["ALL"][index]
                row["random_minus_reference_pp"] = 100 * (
                    shares["RANDOM"][index] - shares["ALL"][index]
                )
            bands.append(row)
        if len(set(edges)) != len(edges):
            report["warnings"].append(
                "Repeated radial cuts: weighted population does not support ten distinct intervals."
            )
        source.verify()
        verify_geometry(geometry_sources)
        for captured in captures.values():
            verify_arm(captured)
        report.update(
            {
                "status": "MEASURED",
                "reference_source": source.provenance(),
                "arms": {
                    name: arm_provenance(value) for name, value in captures.items()
                },
                "source_population": "scored_reference_population",
                "center_xy": center,
                "n_bands": N_BANDS,
                "edges": edges,
                "bands": bands,
                "geometry_sources_sha256": fingerprint(geometry_sources),
                "global_area_gap_pp": 100
                * (abs(totals["BOOTSTRAP"] - totals["RANDOM"]) / sum(area.values())),
                "median_patch_radial_width": st.median(
                    hi - lo for lo, hi in extent.values()
                ),
                "median_internal_band_width": st.median(
                    b - a for a, b in zip(edges, edges[1:], strict=False)
                )
                if len(edges) > 1
                else None,
                "largest_band_gap_pp": max(
                    abs(row["bootstrap_minus_random_pp"]) for row in bands
                ),
                "mean_midpoint_radius": {
                    name: st.mean(
                        extent[pid][0] / 2 + extent[pid][1] / 2
                        for pid in sorted(values)
                    )
                    for name, values in ids.items()
                },
            }
        )
    except INPUT_ERRORS as exc:
        report["failures"].append(f"input validation failed: {exc}")
    return report


def render(report):
    if report["status"] == "FAIL":
        print("SPATIAL INPUT CHECK FAILED:")
        for failure in report["failures"]:
            print(f"  - {failure}")
        return
    cx, cy = report["center_xy"]
    print(f"radial centre (area-weighted union, XY): ({cx:,.0f}, {cy:,.0f})")
    print(
        f"{'band':<6}{'radius <=':>12}{'BOOT area%':>12}{'RAND area%':>12}{'gap pts':>10}"
    )
    for row in report["bands"]:
        upper = row["radius_upper"]
        limit = "outermost" if upper is None else f"{upper:,.0f}"
        print(
            f"{row['index']:<6}{limit:>12}{100 * row['bootstrap_share']:>12.2f}{100 * row['random_share']:>12.2f}{row['bootstrap_minus_random_pp']:>+10.2f}"
        )
        if "reference_population_share" in row:
            print(
                f"      ALL area%: {100 * row['reference_population_share']:.2f}; RAND-ALL: {row['random_minus_reference_pp']:+.2f} pts"
            )
    print(
        f"\nlargest per-band gap: {report['largest_band_gap_pp']:.2f} points (global area gap for the same build: {report['global_area_gap_pp']:.2f} points)"
    )
    outer = report["bands"][-1]
    print(
        f"outermost radial proxy band: BOOT {100 * outer['bootstrap_share']:.2f}% vs RAND {100 * outer['random_share']:.2f}% of own area"
    )
    print(
        "REPORTED, NOT GATED: no spatial balance criterion is applied. Winding calibration is unverified."
    )
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--bootstrap", required=True)
    parser.add_argument("--random", required=True, dest="random_dir")
    parser.add_argument(
        "--full",
        help="Include the scored reference population on the union-derived axes",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one finite JSON report instead of text",
    )
    args = parser.parse_args(argv)
    report = build_report(args.reference, args.bootstrap, args.random_dir, args.full)
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        render(report)
    return 0 if report["status"] == "MEASURED" else 1


if __name__ == "__main__":
    sys.exit(main())
