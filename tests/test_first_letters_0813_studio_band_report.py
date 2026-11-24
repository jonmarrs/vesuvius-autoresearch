"""The finding-129 report states the numbers in its record, numbers only, and registers no verdict of its own."""

import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0813_studio_band.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0813_studio_band.json").read_text())
OUTER = json.loads((ROOT / "reports/first_letters_0813_outer_sheets.json").read_text())
F126 = json.loads((ROOT / "reports/first_letters_0358_studio_band.json").read_text())
F126_OUTER = json.loads(
    (ROOT / "reports/first_letters_0358_outer_sheets.json").read_text()
)
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()
FLAT_STRATEGY = " ".join(STRATEGY.split())
REG = " ".join((ROOT / RECORD["registration"]).read_text().split())
N = 110


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


def _index(w: str) -> int:
    return int(w[1:])


def test_every_step_of_the_chain_and_the_read_exited_zero():
    assert RECORD["finding"] == 129 and RECORD["registration_commit"] == "53e2b8d9"
    assert RECORD["arm"] == "fulldense" and RECORD["quality_arm"] == "full"
    assert all(g["exit"] == 0 for g in RECORD["chain"]["steps"].values())
    assert len(RECORD["chain"]["steps"]) == 10
    steps = RECORD["steps"]
    assert all(steps[s]["exit"] == 0 for s in ("snap", "orient", "summarise"))
    for name in ("flatten", "render", "studio"):
        assert steps[name]["attempted"] == steps[name]["exited_zero"] == N
        assert steps[name]["failed"] == []
    assert RECORD["windings"] == RECORD["read"] == N
    assert RECORD["windings_with_no_tile_scored"] == []
    assert f"{N} of {N} (none failed)" in REPORT
    assert "amendment 1 at `011b737d`" in REPORT
    assert "## Amendment 1" in (ROOT / RECORD["registration"]).read_text()


def test_no_verdict_is_claimed_and_no_image_is_shipped():
    assert "verdict" not in RECORD and "and the read has no automatic verdict" in REG
    assert "**The read has no automatic verdict.**" in REPORT
    assert "I have not looked at them" in FLAT
    assert not re.search(r"!\[|\.png\)", REPORT)  # links no image
    for record in (RECORD, OUTER):
        assert "/home/" not in json.dumps(record)  # numbers and winding names only


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
    parts = fit["full_by_index"]
    for part in parts:
        assert (
            f"| w{part['first']:03d} to w{part['last']:03d} | {part['excess_median']} | {part['positive']} "
            f"| {part['on_sheet_median']} |"
        ) in REPORT
    assert max(parts, key=lambda p: p["excess_median"])["first"] == 50
    outer = parts[2]
    assert outer["positive"] == 1.0
    assert outer["excess_median"] == min(p["excess_median"] for p in parts)
    assert outer["on_sheet_median"] == min(p["on_sheet_median"] for p in parts)
    by = RECORD["by_winding"]
    assert all(row["excess"] > 0 for row in by.values())
    dropped = sorted({f"w{i:03d}" for i in range(10, 130)} - set(by))
    assert len(dropped) == 120 - N
    assert ", ".join(dropped[:-1]) + " and " + dropped[-1] in FLAT
    assert f"all among the inner {_index(dropped[-1]) - 10 + 1}" in FLAT
    assert sum(round(p["windings"] * (1 - p["positive"])) for p in parts) == len(
        dropped
    )


def test_the_registered_numbers_are_the_records():
    ro = RECORD["render_orientation"]
    assert ro["flip"] == 0 and len(ro["keep"]) == N
    assert f"| none; kept: {N} |" in REPORT
    assert f"| {_spread(ro['share_of_normals_pointing_inward'])} |" in REPORT
    assert RECORD["reading_orientation"]["both"] == N
    assert f"both (mirrored and upside down): {N} |" in REPORT
    assert "With these flags it is the recipe's own rule, unchanged" in REG
    assert f"| {_spread(RECORD['ink_share'])} |" in REPORT
    assert f"| {_spread(RECORD['largest_tile_ink_share'])} |" in REPORT
    assert f"| {RECORD['tiles_scored']:,} |" in REPORT
    assert f"| {RECORD['rendered_pixels']:,} |" in REPORT
    first = RECORD["inspection_order_first_ten"]
    assert ", ".join(first) in FLAT
    assert max(_index(w) for w in first) < 111  # none of the outermost windings
    assert (
        f"(median {F126['ink_share']['median']} and {F126['largest_tile_ink_share']['median']})"
        in FLAT
    )


def test_every_render_follows_the_axis_rule():
    g = RECORD["geometry"]
    assert g["rendered_against_the_axis_rule"] == []
    for w, row in RECORD["by_winding"].items():
        assert (
            row["render"] == "keep" and row["geometry"]["inward_against_axis"] < 0.5
        ), w
    most = g["inward_against_axis"]["max"]
    assert f"points inward on {most} of its nodes" in FLAT
    assert f"still points outward on {round(1 - most, 4)} of its nodes" in FLAT
    assert (
        f"gives a median {g['inward_against_band_centre_median']} inward here" in FLAT
    )
    assert g["inward_against_band_centre_median"] < 0.5
    assert "rendered unflipped" in REG


def test_the_stacked_pairs_are_the_records():
    st = RECORD["stacked"]
    assert st["line"] == 0.3
    assert all((v > st["line"]) == (k in st["stacked"]) for k, v in st["pairs"].items())
    names = st["stacked"]
    assert (
        f"Of the {len(st['pairs'])} pairs of neighbouring windings (both read, indices one apart), "
        f"{len(names)} have more than 30%" in FLAT
    )
    assert ", ".join(names[:-1]) + " and " + names[-1] in FLAT
    f126 = F126["stacked"]
    assert (
        f"On PHerc. 0358, {len(f126['stacked'])} of {len(f126['pairs'])} pairs were stacked"
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
    assert t[2] == min(t)
    assert (
        f"| final nodes within 2 voxels of the snapped triangles | {g['on_snapped_triangles_median']} |"
        in REPORT
    )
    assert f"({g['on_snapped_triangles_median']} of all final nodes" in FLAT
    assert (
        "nearly a third of the rendered nodes" in FLAT
        and 0.28 < 1 - w2["final"] < 1 / 3
    )


def test_the_trusted_shares_are_the_records():
    g, by = RECORD["geometry"], RECORD["by_winding"]
    trusted = {w: r["geometry"]["trusted"] for w, r in by.items()}
    assert g["trusted_median"] == round(float(statistics.median(trusted.values())), 4)
    assert (
        f"Median {g['trusted_median']} ({min(trusted.values())} to {max(trusted.values())})"
        in FLAT
    )
    low = sorted(w for w, v in trusted.items() if v < 0.4)
    outermost = [f"w{i:03d}" for i in range(111, 130)]
    assert low == ["w012", "w013", "w014", "w016", *outermost]
    assert f"{len(low)} windings are under 0.4" in FLAT
    assert f"and all {len(outermost)} of w111 to w129" in FLAT
    assert f"layers inward is a median {g['other_side_median']}" in FLAT


def test_the_outermost_windings_geometry_is_quoted_from_its_numbers():
    inner, outer = OUTER["read_windings_geometry"]["parts"]
    assert (inner["first"], inner["last"], outer["first"], outer["last"]) == (
        "w010", "w110", "w111", "w129",
    )  # fmt: skip
    by = RECORD["by_winding"]
    assert inner["windings_read"] + outer["windings_read"] == len(by) == N
    assert outer["windings_read"] == sum(1 for w in by if _index(w) >= 111) == 19
    # the parts' medians agree with the record where the record carries the same number
    for part in (inner, outer):
        rows = [r for w, r in by.items() if part["first"] <= w <= part["last"]]
        final = statistics.median(r["geometry"]["final_within_2"] for r in rows)
        trusted = statistics.median(r["geometry"]["trusted"] for r in rows)
        assert abs(final - part["final_within_2_median"]) < 1e-4
        assert abs(trusted - part["trusted_median"]) < 1e-4
    assert (
        f"a median {outer['snapped_within_2_median']} of the snapped nodes and "
        f"{outer['final_within_2_median']} of the final nodes lie within 2 voxels"
        in FLAT
    )
    assert (
        f"against {inner['snapped_within_2_median']} and {inner['final_within_2_median']} for the 91 windings"
        in FLAT
    )
    assert inner["snapped_outside_field_median"] == 0.0
    assert (
        f"A median {outer['snapped_outside_field_median']} of their snapped nodes lie outside"
        in FLAT
    )
    assert f"whose median is {outer['trusted_median']}" in FLAT
    assert f"(w010 to w110: {inner['trusted_median']})" in FLAT


def test_the_outer_sheet_check_is_quoted_from_its_numbers():
    assert OUTER["finding"] == 129 and (ROOT / OUTER["script"]).exists()
    assert OUTER["z_working"] == (9996 + 11496) / 2
    assert f"at z {OUTER['z_working']:.0f}" in FLAT
    for w, row in OUTER["windings"].items():
        lo, hi = row["sheet_runs_beyond_p10_p90"]
        gap = row["outermost_sheet_minus_winding_radius_working_median"]
        cell = f"{row['sheet_runs_beyond_median']:g} ({lo:g} to {round(hi, 1):g})"
        assert f"| {w} | {cell} | {gap} |" in REPORT, w
    gaps = {
        w: r["outermost_sheet_minus_winding_radius_working_median"]
        for w, r in OUTER["windings"].items()
    }
    assert gaps["w110"] > 0 and all(gaps[w] < 0 for w in gaps if _index(w) >= 115)
    assert all(
        OUTER["windings"][w]["sheet_runs_beyond_median"] == 0
        for w in gaps
        if _index(w) >= 115
    )
    f126 = F126_OUTER["windings"]["w129"][
        "outermost_sheet_minus_winding_radius_working_median"
    ]
    assert f"(a median {f126} voxels from it)" in FLAT


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
        ("read", f"read, {N} windings"),
    ):
        assert f"| {label} | {_hms(chain[name]['seconds'])} |" in REPORT, name
    total = RECORD["chain"]["seconds"]
    assert total == sum(g["seconds"] for g in chain.values())
    h, m = divmod(round(total / 60), 60)
    assert f"| **all** | **{h} h {m} min** |" in REPORT
    assert f"in {h} h {m} min" in FLAT_STRATEGY
    assert (
        "about a day and a half" in REG
        and "4 h of flatten, 4 h of renders and 7 h of Studio" in REG
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
    assert (
        f"the read took {round(chain['read']['seconds'] / N / 60, 1)} minutes" in FLAT
    )
    assert f"close to finding 126's {round(_read_seconds(F126) / 111 / 60, 1)}" in FLAT
    hours = 3600
    assert (
        f"The flatten took {round(steps['flatten']['seconds_total'] / (4 * hours), 2):g} of its registered time "
        f"and the renders {round(steps['render']['seconds_total'] / (4 * hours), 2):g}"
    ) in FLAT
    assert (
        f"Studio took {round(steps['studio']['seconds_total'] / (7 * hours), 2)} times its registered time"
        in FLAT
    )
    assert "a median 37 million pixels" in REG and "a median 37 million pixels" in FLAT
    c = RECORD["render_canvas_megapixels"]
    assert f"median {c['median']} million pixels ({c['min']} to {c['max']})" in FLAT
    disk = RECORD["bytes_on_disk"] | RECORD["chain"]["bytes_on_disk"]
    assert (
        f"the inputs take {disk['inputs'] / 1e9:.1f} GB and the tracks {disk['tracks'] / 1e9:.1f} GB"
        in FLAT
    )
    assert f"The renders take {disk['renders'] / 1e9:.1f} GB" in FLAT
    assert f"Studio's maps {disk['studio_maps'] / 1e9:.1f} GB" in FLAT
    assert "8.2 GB" in REG and "(the tracks' listing was 8.2 GB)" in FLAT


def test_the_thin_renders_take_amendment_1s_share_of_the_disk():
    per = (RECORD["bytes_on_disk"]["renders"] / N) / (
        F126["bytes_on_disk"]["renders"] / 111
    )
    assert f"took {round(per, 3)} of PHerc. 0358's 66-layer renders per winding" in FLAT
    assert "They take 0.28 of the disk" in REG and abs(per - 0.28) < 0.01
    assert (
        f"Their median time, {RECORD['steps']['render']['seconds_median']} s, is under PHerc. 0358's "
        f"{F126['steps']['render']['seconds_median']} s"
    ) in FLAT
    assert "Time is not claimed" in REG


def test_the_gpu_peaks_are_stated_and_studio_was_not_sampled():
    fit = RECORD["fit"]["steps"]
    assert (
        f"the fit peaked at {fit['full/fit']['gpu_peak_mib_all_processes']:,} MiB"
        in FLAT
    )
    assert (
        f"(the 300-step fit at {fit['smoke/fit']['gpu_peak_mib_all_processes']:,})"
        in FLAT
    )
    assert fit["full/fit"]["gpu_peak_mib_all_processes"] < 15 * 1024
    assert "GPU memory up to about 15 GB" in REG
    assert (
        RECORD["gpu_peak_mib_all_processes"] is None and RECORD["gpu_samples"] is None
    )
    assert "Studio's use was not sampled in this read" in FLAT


def test_the_strategy_carries_the_finding():
    assert "reports/first_letters_0813_studio_band.md" in STRATEGY
    assert "finding 129" in FLAT_STRATEGY
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
    inner, outer = OUTER["read_windings_geometry"]["parts"]
    assert (
        f"is {inner['final_within_2_median']} over w010 to w110 but {outer['final_within_2_median']} over w111 to w129"
        in FLAT_STRATEGY
    )
    # finding 129's paragraph comes after finding 126's and before the kill criterion
    at = FLAT_STRATEGY.index("first_letters_0813_studio_band.md")
    assert FLAT_STRATEGY.index("first_letters_0358_studio_band.md") < at
    assert at < FLAT_STRATEGY.index("**Kill criterion.**")


# --- every place the report restates a count, a winding or a registered estimate, not only the first ---------------


def test_the_counts_the_report_repeats_are_the_records():
    parts = RECORD["fit"]["full_by_index"]
    first, last = parts[0]["first"], parts[-1]["last"]
    assert RECORD["fit"]["full"]["windings_scored"] == last - first + 1
    assert (
        f"villa's fit writes w000 to w{last:03d}; the score starts at w{first:03d}) | "
        f"{RECORD['fit']['full']['windings_scored']} |" in FLAT
    )
    assert f"Villa's fit writes {last + 1} windings whatever the scroll" in FLAT
    steps = RECORD["fit"]["steps"]
    assert f"excess, {steps['full/fit']['steps']:,}-step fit |" in FLAT
    assert (
        f"The {steps['smoke/fit']['steps']}-step fit was scored after the read" in FLAT
    )
    for phrase in (
        f"Studio read all {N} selected windings",
        f"every step of the read exited 0 on all {N} windings",
        f"all {N} at one eighth",
        f"**Selected for the read:** the {N} windings with positive excess",
        f"| median over the {N} windings |",
        f"| read, {N} windings |",
        f"| flatten, {N} windings |",
        f"| render, {N} windings |",
        f"| Studio, {N} windings (planes and map) |",
    ):
        assert phrase in FLAT, phrase


def test_the_windings_the_report_names_are_the_records():
    by = RECORD["by_winding"]
    trusted = {w: r["geometry"]["trusted"] for w, r in by.items()}
    inner_low = sorted(w for w, v in trusted.items() if v < 0.4 and _index(w) < 111)
    assert (
        f"{', '.join(inner_low[:-1])} and {inner_low[-1]} among the inner ones" in FLAT
    )
    outer = sorted(w for w in by if _index(w) >= 111)
    inner = sorted(w for w in by if _index(w) < 111)
    span = f"{outer[0]} to {outer[-1]}"
    assert (
        f"the {len(outer)} outermost windings, {span}, lie mostly off the predicted sheet"
        in FLAT
    )
    assert f"Of the {len(outer)} read windings {span}" in FLAT
    assert f"where the {len(inner)} have none" in FLAT
    part = OUTER["read_windings_geometry"]["parts"][
        0
    ]  # the index range w010 to w110, of which w012 on are read
    assert f"for the {len(inner)} windings {part['first']} to {part['last']}" in FLAT


def test_the_papyrus_edge_is_named_where_the_outer_sheet_gap_changes_sign():
    gaps = {
        w: r["outermost_sheet_minus_winding_radius_working_median"]
        for w, r in OUTER["windings"].items()
    }
    inside = max((w for w, g in gaps.items() if g > 0), key=_index)
    past = min((w for w, g in gaps.items() if g < 0), key=_index)
    assert (inside, past) == ("w110", "w115")
    assert f"those from {past} outward lie past its outermost sheet" in FLAT
    assert (
        f"the predicted papyrus ends near {inside}, and the windings from {past} outward lie past it"
        in FLAT
    )
    assert f"The edge near {inside} was measured at one slice" in FLAT


def test_the_band_and_the_registered_estimates_are_the_registrations():
    lo, hi = (
        int(v) for v in re.search(r"FL_Z_BEGIN=(\d+) FL_Z_END=(\d+)", REG).groups()
    )
    assert (
        f"the middle {hi - lo:,} slices of PHerc. 0813's tracked range (z {lo} to {hi})"
        in FLAT
    )
    fit, flatten, render, studio = re.search(
        r"about ([\d.]+) h of fit, then about (\d+) h of flatten, (\d+) h of renders and (\d+) h of Studio",
        REG,
    ).groups()
    assert f"| about {fit} hours |" in FLAT
    total = int(flatten) + int(render) + int(studio)
    assert (
        f"about {total} hours ({flatten} h flatten, {render} h renders, {studio} h Studio)"
        in FLAT
    )
    assert "about a day and a half" in REG and "**about a day and a half**" in FLAT
    gpu = re.search(r"GPU memory up to about (\d+) GB", REG).group(1)
    assert f"inside the registered {gpu} GB" in FLAT
    assert "0.28" in REG and "as amendment 1 measured on three windings (0.28)" in FLAT
