"""The finding-126 report states the numbers in its record, numbers only, and registers no verdict of its own."""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0358_studio_band.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0358_studio_band.json").read_text())
F125 = json.loads((ROOT / "reports/first_letters_0826_studio_band.json").read_text())
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()
FLAT_STRATEGY = " ".join(STRATEGY.split())
REG = " ".join((ROOT / RECORD["registration"]).read_text().split())
PST = timezone(timedelta(hours=-8))


def _spread(s: dict) -> str:
    return f"median {s['median']} ({s['min']} to {s['max']})"


def _hms(seconds: int) -> str:
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    if h:
        return f"{h} h {m} min {s} s"
    return f"{m} min {s} s" if m else f"{s} s"


def _read_seconds(rec: dict) -> int:
    s = rec["steps"]
    return sum(s[k]["seconds"] for k in ("snap", "orient", "summarise")) + sum(
        s[k]["seconds_total"] for k in ("flatten", "render", "studio")
    )


def test_every_step_of_the_chain_and_the_read_exited_zero():
    assert RECORD["finding"] == 126 and RECORD["registration_commit"] == "3c97310a"
    assert RECORD["arm"] == "fulldense" and RECORD["quality_arm"] == "full"
    assert all(g["exit"] == 0 for g in RECORD["chain"]["steps"].values())
    assert len(RECORD["chain"]["steps"]) == 10
    steps = RECORD["steps"]
    assert all(steps[s]["exit"] == 0 for s in ("snap", "orient", "summarise"))
    for name in ("flatten", "render", "studio"):
        assert steps[name]["attempted"] == steps[name]["exited_zero"] == 111
        assert steps[name]["failed"] == []
    assert RECORD["windings"] == RECORD["read"] == 111
    assert RECORD["windings_with_no_tile_scored"] == []
    assert "111 of 111 (none failed)" in REPORT


def test_no_verdict_is_claimed_and_no_image_is_shipped():
    assert "verdict" not in RECORD and "The read has no automatic verdict" in REG
    assert "**The read has no automatic verdict.**" in REPORT
    assert "I have not looked at them" in FLAT
    assert not re.search(r"!\[|\.png\)", REPORT)  # links no image
    assert "/home/" not in json.dumps(RECORD)  # numbers and winding names only


def test_the_fit_is_finding_112s_table_and_the_selection_its_positive_windings():
    fit = RECORD["fit"]
    assert fit["verdict"] == "ON_SHEETS" and fit["p1"] and fit["p2"]
    full, smoke = fit["full"], fit["smoke"]
    assert full["windings_scored"] == smoke["windings_scored"] == 120
    assert (
        f"| {full['excess_median']} (p10 {full['excess_p10']}, p90 {full['excess_p90']}) |"
        in REPORT
    )
    assert f"| {full['share_of_windings_with_positive_excess']} |" in REPORT
    assert (
        f"| median excess of the 300-step fit (the floor; at most 0.03) | {smoke['excess_median']} |"
        in REPORT
    )
    assert "**`ON_SHEETS`**" in REPORT and "`PARTLY_ON_SHEETS` or better" in REG
    for part in fit["full_by_index"]:
        assert (
            f"| w{part['first']:03d} to w{part['last']:03d} | {part['excess_median']} | {part['positive']} "
            f"| {part['on_sheet_median']} |"
        ) in REPORT
    assert max(fit["full_by_index"], key=lambda p: p["excess_median"])["first"] == 90
    by = RECORD["by_winding"]
    assert all(row["excess"] > 0 for row in by.values())
    dropped = sorted({f"w{i:03d}" for i in range(10, 130)} - set(by))
    assert len(dropped) == 120 - 111
    assert ", ".join(dropped[:-1]) + " and " + dropped[-1] in FLAT
    assert f"all among the inner {int(dropped[-1][1:]) - 10 + 1}" in FLAT
    # the selection lost 9 windings, as the positive shares of the three parts say
    assert sum(
        round(p["windings"] * (1 - p["positive"])) for p in fit["full_by_index"]
    ) == len(dropped)


def test_the_registered_numbers_are_the_records():
    ro = RECORD["render_orientation"]
    assert ro["flip"] == 111 and ro["keep"] == []
    assert "| 111; kept: none |" in REPORT
    assert f"| {_spread(ro['share_of_normals_pointing_inward'])} |" in REPORT
    assert RECORD["reading_orientation"]["mirrored only"] == 111
    assert f"| {_spread(RECORD['ink_share'])} |" in REPORT
    assert f"| {_spread(RECORD['largest_tile_ink_share'])} |" in REPORT
    assert f"| {RECORD['tiles_scored']:,} |" in REPORT
    assert f"| {RECORD['rendered_pixels']:,} |" in REPORT
    assert ", ".join(RECORD["inspection_order_first_ten"]) in FLAT
    assert (
        f"(median {F125['ink_share']['median']} and {F125['largest_tile_ink_share']['median']})"
        in FLAT
    )


def test_every_render_follows_the_axis_rule():
    g = RECORD["geometry"]
    assert g["rendered_against_the_axis_rule"] == []
    for w, row in RECORD["by_winding"].items():
        assert (
            row["render"] == "flip" and row["geometry"]["inward_against_axis"] > 0.5
        ), w
    assert f"points inward on {g['inward_against_axis']['min']} of its nodes" in FLAT
    assert f"gives a median {g['inward_against_band_centre_median']} here" in FLAT


def test_the_stacked_pairs_are_the_records_and_all_inner():
    st = RECORD["stacked"]
    assert st["line"] == 0.3
    assert all((v > st["line"]) == (k in st["stacked"]) for k, v in st["pairs"].items())
    names = st["stacked"]
    assert (
        f"Of the {len(st['pairs'])} pairs of neighbouring windings (both read, indices one apart), "
        f"{len(names)} have more than 30%" in FLAT
    )
    assert ", ".join(names[:-1]) + " and " + names[-1] in FLAT
    assert max(int(p.split("-")[1][1:]) for p in names) == 37
    f125 = F125["stacked"]
    assert (
        f"On PHerc. 0826, {len(f125['stacked'])} of {len(f125['pairs'])} pairs were stacked"
        in FLAT
    )


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
    assert f"it holds from {t[0]} to {t[2]}" in FLAT
    t125 = F125["geometry"]["final_within_2_by_radius_tercile_median"]
    assert f"fell from {t125[0]} at the inner third to {t125[2]} at the outer" in FLAT
    w125 = F125["geometry"]["predicted_sheet_within_2_median"]
    assert (
        f"({w2['snapped']} to {w2['final']}, against {w125['snapped']} to {w125['final']})"
        in FLAT
    )
    assert (
        f"| final nodes within 2 voxels of the snapped triangles | {g['on_snapped_triangles_median']} |"
        in REPORT
    )
    by = RECORD["by_winding"]
    trusted = [r["geometry"]["trusted"] for r in by.values()]
    assert g["trusted_median"] == round(float(np.median(trusted)), 4)
    assert f"Median {g['trusted_median']} ({min(trusted)} to {max(trusted)})" in FLAT
    low = sorted(w for w, r in by.items() if r["geometry"]["trusted"] < 0.4)
    assert low == ["w012", "w013"]
    for w in low:
        assert f"{w} ({by[w]['geometry']['trusted']})" in FLAT
        assert any(w in pair for pair in RECORD["stacked"]["stacked"])
    assert f"layers inward is a median {g['other_side_median']}" in FLAT


def test_the_costs_are_the_records():
    chain = RECORD["chain"]["steps"]
    for name, label in (
        ("fetch_volumes", "fetch the volumes"),
        ("fetch_tracks", "fetch the tracks"),
        ("make_dataset", "make the dataset"),
        ("sdt", "distance field"),
        ("fit_smoke", "fit, 300 steps"),
        ("fit_full", "fit, 30,000 steps"),
        ("quality", "quality"),
        ("select", "select"),
        ("densify", "densify"),
        ("read", "read, 111 windings"),
    ):
        assert f"| {label} | {_hms(chain[name]['seconds'])} |" in REPORT, name
    total = RECORD["chain"]["seconds"]
    assert total == sum(g["seconds"] for g in chain.values())
    h, m = divmod(round(total / 60), 60)
    assert f"| **all** | **{h} h {m} min** |" in REPORT
    assert f"by a factor of {round(total / (8 * 3600), 1)}" in FLAT
    assert (
        f"{round(chain['read']['seconds'] / (111 * 3.5 * 60), 1)} times its registered rate"
        in FLAT
    )
    steps = RECORD["steps"]
    assert f"| snap | {steps['snap']['seconds']} s |" in REPORT
    assert f"| orient | {steps['orient']['seconds']} s |" in REPORT
    assert f"| summarise | {_hms(steps['summarise']['seconds'])} |" in REPORT
    for name in ("flatten", "render", "studio"):
        s = steps[name]
        assert (
            f"{_hms(s['seconds_total'])} (median {s['seconds_median']} s, at most {s['seconds_max']} s)"
            in REPORT
        ), name
    assert _read_seconds(RECORD) <= chain["read"]["seconds"]
    per = round(chain["read"]["seconds"] / 111 / 60, 1)
    assert f"the read took {per} minutes" in FLAT
    assert f"finding 125's measured {round(_read_seconds(F125) / 70 / 60, 1)}" in FLAT
    assert (
        steps["flatten"]["seconds_median"] < F125["steps"]["flatten"]["seconds_median"]
    )
    assert f"below finding 125's {F125['steps']['flatten']['seconds_median']} s" in FLAT
    c = RECORD["render_canvas_megapixels"]
    assert f"median {c['median']} million pixels ({c['min']} to {c['max']})" in FLAT
    disk = RECORD["bytes_on_disk"] | RECORD["chain"]["bytes_on_disk"]
    assert (
        f"the inputs take {disk['inputs'] / 1e9:.1f} GB and the tracks {disk['tracks'] / 1e9:.1f} GB"
        in FLAT
    )
    assert f"The renders take {disk['renders'] / 1e9:.1f} GB" in FLAT
    assert f"Studio's maps {disk['studio_maps'] / 1e9:.1f} GB" in FLAT
    assert f"this read's renders alone take {disk['renders'] / 1e9:.1f} GB" in FLAT


def test_the_gpu_peaks_and_the_late_sampler_are_stated():
    fit = RECORD["fit"]["steps"]
    assert (
        f"the fit peaked at {fit['full/fit']['gpu_peak_mib_all_processes']:,} MiB"
        in FLAT
    )
    assert (
        f"(the 300-step fit at {fit['smoke/fit']['gpu_peak_mib_all_processes']:,})"
        in FLAT
    )
    assert f"Studio's peak, {RECORD['gpu_peak_mib_all_processes']:,} MiB" in FLAT
    g = RECORD["gpu_samples"]
    start = datetime.fromtimestamp(g["first_epoch"], tz=PST)
    assert (
        f"the sampler ran from {start:%H:%M} to the end of the read, {g['count']} samples"
        in FLAT
    )
    assert "the last 22 windings' reads (w108 to w129)" in FLAT
    assert sorted(RECORD["by_winding"])[-22:][0] == "w108"


def test_the_outer_sheet_check_is_quoted_from_its_numbers():
    outer = json.loads(
        (ROOT / "reports/first_letters_0358_outer_sheets.json").read_text()
    )
    assert outer["finding"] == 126 and "/home/" not in json.dumps(outer)
    assert (ROOT / outer["script"]).exists()
    w129, w110 = outer["windings"]["w129"], outer["windings"]["w110"]
    assert f"at the band's middle slice (z {outer['z_working']:.0f})" in FLAT
    gap = w129["outermost_sheet_minus_winding_radius_working_median"]
    assert f"lies a median {gap} voxels from it" in FLAT
    runs = w129["sheet_runs_beyond_median"]
    assert (
        f"A median of {runs:.0f} sheet runs lie beyond it (90th percentile {w129['sheet_runs_beyond_p10_p90'][1]:.0f})"
        in FLAT
    )
    assert f"beyond w110 there are {w110['sheet_runs_beyond_median']:.0f}" in FLAT


def test_the_strategy_carries_the_finding():
    assert "reports/first_letters_0358_studio_band.md" in STRATEGY
    assert "finding 126" in FLAT_STRATEGY
    t = RECORD["geometry"]["final_within_2_by_radius_tercile_median"]
    assert (
        f"holds from {round(t[0], 2)} at the inner third of radii to {round(t[2], 2)} at the outer"
        in FLAT_STRATEGY
    )
    f = RECORD["fit"]["full"]
    assert (
        f"(median excess {f['excess_median']}, {f['share_of_windings_with_positive_excess']} of windings positive)"
        in FLAT_STRATEGY
    )
    st = RECORD["stacked"]
    assert (
        f"{len(st['stacked'])} of {len(st['pairs'])} neighbouring pairs are stacked"
        in FLAT_STRATEGY
    )
