"""The finding-139 report states the numbers in its records, numbers only, and claims nothing about the direction."""

import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0125_studio_band.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0125_studio_band.json").read_text())
DESCRIBED = json.loads((ROOT / "reports/first_letters_0125_described.json").read_text())
F133 = json.loads((ROOT / "reports/first_letters_0800_studio_band.json").read_text())
F133_D = json.loads((ROOT / "reports/first_letters_0800_described.json").read_text())
F129 = json.loads((ROOT / "reports/first_letters_0813_studio_band.json").read_text())
REG = " ".join((ROOT / RECORD["registration"]).read_text().split())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
N = 98


def _spread(s: dict) -> str:
    return f"median {s['median']} ({s['min']} to {s['max']})"


def _hms(seconds: int) -> str:
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    if h:
        return f"{h} h {m} min {s} s"
    return f"{m} min {s} s" if m else f"{s} s"


def test_every_step_exited_zero_and_no_verdict_or_image():
    assert RECORD["finding"] == 139 and RECORD["registration_commit"] == "2d801cbb"
    assert all(g["exit"] == 0 for g in RECORD["chain"]["steps"].values())
    for name in ("flatten", "render", "studio"):
        s = RECORD["steps"][name]
        assert s["attempted"] == s["exited_zero"] == N and s["failed"] == []
    assert RECORD["windings"] == RECORD["read"] == N
    assert f"{N} of {N} (none failed)" in REPORT
    assert (
        "verdict" not in RECORD and "**The read has no automatic verdict.**" in REPORT
    )
    assert "I have not looked at them" in FLAT and not re.search(r"!\[|\.png\)", REPORT)
    for record in (RECORD, DESCRIBED):
        assert "/home/" not in json.dumps(record)


def test_the_report_claims_nothing_about_the_direction():
    assert "**Nothing here measures the direction.**" in REPORT
    assert "FL_SENSE=CW" in REG and "not on any evidence about this scroll" in REG
    assert "every image stands turned by 180 degrees" in FLAT
    assert (
        "clockwise is right" in FLAT and "says nothing about the direction" in STRATEGY
    )


def test_the_fit_is_finding_112s_table_and_the_selection_its_positive_windings():
    fit = RECORD["fit"]
    assert fit["verdict"] == "ON_SHEETS" and fit["p1"] and fit["p2"]
    full, smoke = fit["full"], fit["smoke"]
    assert (
        f"| {full['excess_median']} (p10 {full['excess_p10']}, p90 {full['excess_p90']}) |"
        in REPORT
    )
    assert f"| {full['share_of_windings_with_positive_excess']} |" in REPORT
    assert (
        f"| median excess of the 300-step fit (the floor; at most 0.03) | {smoke['excess_median']} |"
        in REPORT
    )
    for part in fit["full_by_index"]:
        assert (
            f"| w{part['first']:03d} to w{part['last']:03d} | {part['excess_median']} | {part['positive']} "
            f"| {part['on_sheet_median']} |"
        ) in REPORT
    dropped = sorted({f"w{i:03d}" for i in range(10, 130)} - set(RECORD["by_winding"]))
    assert (
        dropped == DESCRIBED["fit_windings_by_excess_sign"]["not_positive_windings"]
        and len(dropped) == 22
    )
    assert ", ".join(dropped[:-1]) + " and " + dropped[-1] in FLAT
    pos = DESCRIBED["fit_windings_by_excess_sign"]["positive"]
    neg = DESCRIBED["fit_windings_by_excess_sign"]["not_positive"]
    assert (
        f"| nodes inside the predicted sheet | {pos['on_sheet_median']} | {neg['on_sheet_median']} |"
        in REPORT
    )
    assert neg["displaced_median"] > neg["on_sheet_median"]


def test_the_read_and_geometry_numbers_are_the_records():
    assert f"| {_spread(RECORD['ink_share'])} |" in REPORT
    assert f"| {_spread(RECORD['largest_tile_ink_share'])} |" in REPORT
    assert (
        f"| {RECORD['tiles_scored']:,} |" in REPORT
        and f"| {RECORD['rendered_pixels']:,} |" in REPORT
    )
    assert ", ".join(RECORD["inspection_order_first_ten"]) in FLAT
    g = RECORD["geometry"]
    assert (
        RECORD["render_orientation"]["flip"] == 0
        and g["rendered_against_the_axis_rule"] == []
    )
    assert f"| {_spread(g['inward_against_axis'])} |" in REPORT
    assert (
        f"still points outward on {round(1 - g['inward_against_axis']['max'], 4)} of its nodes"
        in FLAT
    )
    w2, on = g["predicted_sheet_within_2_median"], g["predicted_sheet_on_sheet_median"]
    assert (
        f"| nodes within 2 voxels of the predicted sheet | {w2['snapped']} | {w2['final']} |"
        in REPORT
    )
    assert (
        f"| nodes inside the predicted sheet | {on['snapped']} | {on['final']} |"
        in REPORT
    )
    for label, value in zip(("inner third of radii", "middle third", "outer third"),
                            g["final_within_2_by_radius_tercile_median"], strict=True):  # fmt: skip
        assert f"| {label} | {value} |" in REPORT
    trusted = {w: r["geometry"]["trusted"] for w, r in RECORD["by_winding"].items()}
    assert g["trusted_median"] == round(float(statistics.median(trusted.values())), 4)
    low = sorted(w for w, v in trusted.items() if v < 0.4)
    assert (
        low == [f"w{i}" for i in range(122, 129)]
        and f"{len(low)} windings are under 0.4" in FLAT
    )
    st = RECORD["stacked"]
    assert (
        f"Of the {len(st['pairs'])} pairs" in FLAT
        and f"{len(st['stacked'])} have more than 30%" in FLAT
    )
    assert (
        f"At PHerc. 0800, {len(F133['stacked']['stacked'])} of {len(F133['stacked']['pairs'])} were"
        in FLAT
    )
    assert (
        f"PHerc. 0813, {len(F129['stacked']['stacked'])} of {len(F129['stacked']['pairs'])}"
        in FLAT
    )


def test_the_described_checks_are_quoted_from_their_numbers():
    assert DESCRIBED["z_working"] == (10250 + 11750) / 2
    for w, row in DESCRIBED["windings"].items():
        lo, hi = row["sheet_runs_beyond_p10_p90"]
        cell = f"{row['sheet_runs_beyond_median']:g} ({lo:g} to {round(hi, 1):g})"
        assert (
            f"| {w} | {cell} | {row['outermost_sheet_minus_winding_radius_working_median']} |"
            in REPORT
        ), w
    cov = DESCRIBED["sheet_coverage"]["sets"]
    for key in ("raw_all", "raw_read", "raw_dropped", "final_read"):
        assert str(cov[key]["covered_share"]) in FLAT
    lost = round(cov["raw_all"]["covered_share"] - cov["raw_read"]["covered_share"], 3)
    assert f"Leaving the 22 out lost {lost} of the runs" in FLAT
    assert f"of {cov['raw_all']['runs_counted']:,} predicted-sheet runs" in FLAT
    f133 = F133_D["sheet_coverage"]["pherc0800"]["sets"]["final_read"]["covered_share"]
    assert f"at PHerc. 0800 the read windings covered {f133}" in FLAT
    sp = DESCRIBED["snap_passes"]
    shares = [
        sp[k]["already_on_median"]
        for k in ("before_pass_1", "before_pass_2", "before_pass_3")
    ]
    assert f"{shares[0]}, {shares[1]}, {shares[2]}" in FLAT
    mem = DESCRIBED["memory_pressure"]
    assert mem["samples_over_50"] == 0 and mem["user_psi10_max"] < 50
    assert f"peaked at {mem['user_psi10_max']}%" in FLAT and f"at {mem['at']}" in FLAT


def test_the_costs_are_the_records():
    chain = RECORD["chain"]["steps"]
    for name, label in (("fit_full", "fit, 30,000 steps"), ("fit_smoke", "fit, 300 steps"), ("sdt", "distance field"),
                        ("quality", "quality"), ("read", f"read, {N} windings")):  # fmt: skip
        assert f"| {label} | {_hms(chain[name]['seconds'])} |" in REPORT, name
    h, m = divmod(round(RECORD["chain"]["seconds"] / 60), 60)
    assert (
        f"| **all** | **{h} h {m} min** |" in REPORT and f"in {h} h {m} min" in STRATEGY
    )
    for name in ("flatten", "render", "studio"):
        s = RECORD["steps"][name]
        assert (
            f"{_hms(s['seconds_total'])} (median {s['seconds_median']} s, at most {s['seconds_max']} s)"
            in REPORT
        )
    c = RECORD["render_canvas_megapixels"]
    assert f"median {c['median']} million pixels ({c['min']} to {c['max']})" in FLAT
    disk = RECORD["bytes_on_disk"] | RECORD["chain"]["bytes_on_disk"]
    assert (
        f"the inputs take {disk['inputs'] / 1e9:.1f} GB and the tracks {disk['tracks'] / 1e9:.1f} GB"
        in FLAT
    )
    assert (
        f"The renders take {disk['renders'] / 1e9:.1f} GB and Studio's maps {disk['studio_maps'] / 1e9:.1f} GB"
        in FLAT
    )
    fit = RECORD["fit"]["steps"]
    assert (
        f"the fit peaked at {fit['full/fit']['gpu_peak_mib_all_processes']:,} MiB"
        in FLAT
    )


def test_the_strategy_carries_the_finding_after_finding_138():
    at = STRATEGY.index("first_letters_0125_studio_band.md")
    assert (
        STRATEGY.index("first_letters_0211_band_triage.md")
        < at
        < STRATEGY.index("**Kill criterion.**")
    )
    f = RECORD["fit"]["full"]
    assert (
        f"(median excess {f['excess_median']}, {f['share_of_windings_with_positive_excess']} of windings positive)"
        in STRATEGY
    )
