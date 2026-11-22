"""The finding-125 report states the numbers in its record, numbers only, and registers no verdict of its own."""

import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0826_studio_band.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0826_studio_band.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()
FLAT_STRATEGY = " ".join(STRATEGY.split())
REG = (ROOT / RECORD["registration"]).read_text()


def _spread(s: dict) -> str:
    return f"median {s['median']} ({s['min']} to {s['max']})"


def _hms(seconds: int) -> str:
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h} h {m} min {s} s" if h else f"{m} min {s} s"


def test_every_winding_went_through_every_step():
    steps = RECORD["steps"]
    assert all(steps[s]["exit"] == 0 for s in ("snap", "orient", "summarise"))
    for name in ("flatten", "render", "studio"):
        assert steps[name]["attempted"] == steps[name]["exited_zero"] == 70
        assert steps[name]["failed"] == []
    assert RECORD["windings"] == RECORD["read"] == 70
    assert RECORD["windings_with_no_tile_scored"] == []
    assert "70 of 70 (none failed)" in REPORT


def test_no_verdict_is_claimed_and_no_image_is_shipped():
    assert "verdict" not in RECORD and "This read has no automatic verdict" in REG
    assert "**No automatic verdict was registered.**" in REPORT
    assert "I have not looked at them" in FLAT
    assert not re.search(r"!\[|\.png\)", REPORT)  # links no image
    # the record is numbers and winding names only: no path into the run directory
    assert "/home/" not in json.dumps(RECORD)


def test_the_registered_numbers_are_the_records():
    ro = RECORD["render_orientation"]
    assert ro["flip"] == 68 and ro["keep"] == ["w010", "w011"]
    assert f"| {ro['flip']}; kept: {', '.join(ro['keep'])} |" in REPORT
    assert f"| {_spread(ro['share_of_normals_pointing_inward'])} |" in REPORT
    assert RECORD["reading_orientation"]["mirrored only"] == 70
    assert f"| {_spread(RECORD['ink_share'])} |" in REPORT
    assert f"| {_spread(RECORD['largest_tile_ink_share'])} |" in REPORT
    assert f"| {RECORD['tiles_scored']:,} |" in REPORT
    assert f"| {RECORD['rendered_pixels']:,} |" in REPORT
    assert ", ".join(RECORD["inspection_order_first_ten"]) in FLAT


def test_the_kept_windings_follow_the_registered_rule_and_break_the_axis_rule():
    by = RECORD["by_winding"]
    for w, row in by.items():
        assert (row["render"] == "flip") == (
            row["share_of_normals_pointing_inward"] > 0.5
        ), w
        assert row["geometry"]["inward_against_axis"] > 0.5, w
    g = RECORD["geometry"]
    assert g["rendered_against_the_axis_rule"] == RECORD["render_orientation"]["keep"]
    a = g["inward_against_axis"]
    assert (
        f"median {a['median']} ({a['min']} to {a['max']}) after the flatten, {g['snapped_inward_against_axis_median']} after the snap"
        in FLAT
    )
    assert (
        f"({by['w010']['share_of_normals_pointing_inward']} and {by['w011']['share_of_normals_pointing_inward']})"
        in FLAT
    )


def test_the_stacked_pairs_are_the_records_and_all_inner():
    st = RECORD["stacked"]
    assert st["line"] == 0.3 and len(st["pairs"]) == 69
    assert all((v > st["line"]) == (k in st["stacked"]) for k, v in st["pairs"].items())
    names = st["stacked"]
    assert (
        f"Of the 69 pairs of neighbouring windings, {len(names)} have more than 30%"
        in FLAT
    )
    assert ", ".join(names[:-1]) + " and " + names[-1] in FLAT
    assert max(int(p.split("-")[1][1:]) for p in names) == 26


def test_the_geometry_tables_are_the_records():
    g = RECORD["geometry"]
    w2, on = g["predicted_sheet_within_2_median"], g["predicted_sheet_on_sheet_median"]
    assert (
        f"| nodes within 2 voxels of the predicted sheet | {w2['snapped']} | {w2['final']} |"
        in REPORT
    )
    assert (
        f"| nodes inside the predicted sheet | {on['snapped']} | {on['final']} |"
        in REPORT
    )
    t = g["final_within_2_by_radius_tercile_median"]
    for label, value in zip(
        ("inner third of radii", "middle third", "outer third"), t, strict=True
    ):
        assert f"| {label} | {value} |" in REPORT
    assert (
        f"| final nodes within 2 voxels of the snapped triangles | {g['on_snapped_triangles_median']} |"
        in REPORT
    )
    by = RECORD["by_winding"]
    trusted = [r["geometry"]["trusted"] for r in by.values()]
    assert g["trusted_median"] == round(float(np.median(trusted)), 4)
    assert f"Median {g['trusted_median']} ({min(trusted)} to {max(trusted)})" in FLAT
    low = sorted(w for w, r in by.items() if r["geometry"]["trusted"] < 0.4)
    assert low == ["w010", "w011", "w077", "w078", "w079"]
    for w in low:
        assert f"{w} ({by[w]['geometry']['trusted']})" in FLAT


def test_the_costs_are_the_records():
    steps = RECORD["steps"]
    assert f"| snap | {steps['snap']['seconds']} s |" in REPORT
    assert f"| orient | {steps['orient']['seconds']} s |" in REPORT
    assert f"| summarise | {_hms(steps['summarise']['seconds'])} |" in REPORT
    for name, label in (
        ("flatten", "flatten"),
        ("render", "render"),
        ("studio", "Studio"),
    ):
        s = steps[name]
        assert (
            f"{_hms(s['seconds_total'])} (median {s['seconds_median']} s, at most {s['seconds_max']} s)"
            in REPORT
        ), label
    total = sum(steps[k]["seconds"] for k in ("snap", "orient", "summarise")) + sum(
        steps[k]["seconds_total"] for k in ("flatten", "render", "studio")
    )
    h, m = divmod(round(total / 60), 60)
    assert f"| **all** | **{h} h {m} min** |" in REPORT
    assert f"by a factor of {round(total / (4 * 3600), 1)}" in FLAT
    c = RECORD["render_canvas_megapixels"]
    assert f"median {c['median']} million pixels ({c['min']} to {c['max']})" in FLAT
    disk = RECORD["bytes_on_disk"]
    assert f"the renders take {disk['renders'] / 1e9:.1f} GB" in FLAT
    assert f"Studio's maps {disk['studio_maps'] / 1e9:.1f} GB" in FLAT
    assert f"at most {RECORD['gpu_peak_mib_all_processes']:,} MiB" in FLAT


def test_the_strategy_carries_the_finding():
    assert "reports/first_letters_0826_studio_band.md" in STRATEGY
    assert "finding 125" in FLAT_STRATEGY
    g = RECORD["geometry"]["final_within_2_by_radius_tercile_median"]
    assert (
        f"from {round(g[0], 2)} at the inner third of radii to {round(g[2], 2)} at the outer"
        in FLAT_STRATEGY
    )
