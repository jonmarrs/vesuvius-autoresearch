"""The finding-133 report states the numbers in its records, numbers only, and registers no verdict of its own."""

import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0800_studio_band.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0800_studio_band.json").read_text())
DESCRIBED = json.loads((ROOT / "reports/first_letters_0800_described.json").read_text())
F129 = json.loads((ROOT / "reports/first_letters_0813_studio_band.json").read_text())
F129_OUTER = json.loads(
    (ROOT / "reports/first_letters_0813_outer_sheets.json").read_text()
)
STRATEGY = (ROOT / "docs/RESEARCH_STRATEGY.md").read_text()
FLAT_STRATEGY = " ".join(STRATEGY.split())
REG_TEXT = (ROOT / RECORD["registration"]).read_text()
REG = " ".join(REG_TEXT.split())
N = 90


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


def _names(names: list[str]) -> str:
    return ", ".join(names[:-1]) + " and " + names[-1]


def test_every_step_of_the_chain_and_the_read_exited_zero():
    assert RECORD["finding"] == 133 and RECORD["registration_commit"] == "05822dc0"
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
    assert "amendment 1 at `21c0943c`" in REPORT
    assert "## Amendment 1" in REG_TEXT


def test_the_three_choices_are_the_earlier_findings_records():
    f131 = json.loads((ROOT / "reports/first_letters_0211_dense_read.json").read_text())
    f132 = json.loads((ROOT / "reports/studio_skip_empty_windows.json").read_text())
    f134 = json.loads(
        (ROOT / "reports/first_letters_0211_snap_passes.json").read_text()
    )
    assert (f131["finding"], f131["verdict"]) == (131, "DENSE_READS_SAME")
    assert (f132["finding"], f132["verdict"]) == (132, "SKIP_ADOPTED")
    assert (f134["finding"], f134["consequence"]) == (134, "three_passes")
    assert (
        "finding 132 `SKIP_ADOPTED`, finding 131 `DENSE_READS_SAME` and finding 134 `three_passes`, so "
        "`STUDIO_SKIP_EMPTY=1`, `FL_DENSIFY=2` and `FL_SNAP_PASSES=3`" in FLAT
    )
    # the registration's table and amendment map those verdicts to those settings
    assert "`SKIP_ADOPTED` | `STUDIO_SKIP_EMPTY=1`" in REG
    assert "| any other, or no record | `FL_DENSIFY=2`" in REG
    assert (
        "`FL_SNAP_PASSES=3` only if the record's `consequence` is `three_passes`" in REG
    )


def test_no_verdict_is_claimed_and_no_image_is_shipped():
    assert "verdict" not in RECORD and "and the read has no automatic verdict" in REG
    assert "**The read has no automatic verdict.**" in REPORT
    assert "I have not looked at them" in FLAT
    assert not re.search(r"!\[|\.png\)", REPORT)  # links no image
    for record in (RECORD, DESCRIBED):
        assert "/home/" not in json.dumps(record)  # numbers and winding names only


def test_the_first_start_and_the_memory_pressure_are_disclosed():
    mem = DESCRIBED["memory_pressure"]
    assert (
        "09:08:20" in mem["first_start_killed"]
        and "71.55%" in mem["first_start_killed"]
    )
    assert "killed by systemd-oomd at 09:08:20 during the 300-step fit" in FLAT
    assert "(`attempt1_oomkilled/`), and nothing of it was used" in FLAT
    fit, summ = mem["fit_loading"], mem["summarise"]
    assert (fit["first_over"], fit["last_over"]) == ("12:27:41", "12:27:45")
    assert (
        f"({fit['first_over']} to {fit['last_over']}), over 50% for about 6 s, at most {fit['user_psi10_max']}%"
        in FLAT
    )
    assert (
        f"({summ['first_over']} to {summ['last_over']}), over 50% on {summ['samples_over_50']} of "
        f"{summ['samples']} samples" in FLAT
    )
    assert f"at most {summ['user_psi10_max']}%" in FLAT
    # the sampler writes MiB
    assert (
        summ["unit_anon_mib_max"] < 0.8 * 1024
        and "anonymous memory stayed under 0.8 GiB" in FLAT
    )
    assert f"at least {summ['avail_mib_min'] / 1024:.1f} GiB stayed available" in FLAT
    assert f"reached {summ['unit_file_mib_max'] / 1024:.1f} GiB" in FLAT
    assert (
        mem["between_user_psi10_max"] < 23
        and "Between the two it stayed under 23%" in FLAT
    )


def test_the_fit_is_finding_112s_table_and_the_selection_its_positive_windings():
    fit = RECORD["fit"]
    assert fit["verdict"] == "PARTLY_ON_SHEETS" and not fit["p1"] and fit["p2"]
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
    assert "**`PARTLY_ON_SHEETS`** (line P2 met; P1 missed)" in REPORT
    assert "`PARTLY_ON_SHEETS` or better" in REG
    # P1 fails on the share alone: its median line is met twice over
    assert (
        full["excess_median"] >= 0.07
        and full["share_of_windings_with_positive_excess"] < 0.80
    )
    f129 = F129["fit"]["full"]["excess_median"]
    assert (
        f"The median, {full['excess_median']}, is about twice PHerc. 0813's {f129}"
        in FLAT
    )
    assert 1.9 < full["excess_median"] / f129 < 2.1
    parts = fit["full_by_index"]
    for part in parts:
        assert (
            f"| w{part['first']:03d} to w{part['last']:03d} | {part['excess_median']} | {part['positive']} "
            f"| {part['on_sheet_median']} |"
        ) in REPORT
    by = RECORD["by_winding"]
    assert all(row["excess"] > 0 for row in by.values())
    dropped = sorted({f"w{i:03d}" for i in range(10, 130)} - set(by))
    assert len(dropped) == 120 - N == 30
    assert dropped == DESCRIBED["fit_windings_by_excess_sign"]["not_positive_windings"]
    assert _names(dropped) in FLAT
    assert max(_index(w) for w in dropped) < 105
    assert "Every winding from w105 outward is positive" in FLAT
    assert sum(round(p["windings"] * (1 - p["positive"])) for p in parts) == len(
        dropped
    )


def test_the_windings_left_out_lie_between_the_sheets():
    s = DESCRIBED["fit_windings_by_excess_sign"]
    pos, neg = s["positive"], s["not_positive"]
    assert (pos["windings"], neg["windings"]) == (N, 120 - N) and s[
        "displace_voxels"
    ] == 6.0
    assert (
        f"| nodes inside the predicted sheet | {pos['on_sheet_median']} | {neg['on_sheet_median']} |"
        in REPORT
    )
    assert (
        f"| the same, moved 6 voxels each way | {pos['displaced_median']} | {neg['displaced_median']} |"
        in REPORT
    )
    assert (
        f"| median distance to the sheet, voxels | {pos['abs_distance_median_voxels_median']} "
        f"| {neg['abs_distance_median_voxels_median']} |" in REPORT
    )
    # moved half a spacing, the left-out windings lie more on the sheet; the read ones less
    assert neg["displaced_median"] > neg["on_sheet_median"]
    assert pos["displaced_median"] < pos["on_sheet_median"]
    between = [w for w in s["not_positive_windings"] if 50 <= _index(w) <= 129]
    assert len(between) == s["not_positive_between_w050_and_w129"] == 17
    runs = DESCRIBED["windings"]
    fall = (
        runs["w050"]["sheet_runs_beyond_median"]
        - runs["w129"]["sheet_runs_beyond_median"]
    )
    assert fall == 60
    assert (
        f"79 windings apart, the median number of predicted-sheet runs beyond the winding falls by {fall:g}"
        in FLAT
    )
    assert f"and {len(between)} of the 30 are in that range" in FLAT


def test_the_registered_numbers_are_the_records():
    ro = RECORD["render_orientation"]
    assert ro["flip"] == 0 and len(ro["keep"]) == N
    assert f"| none; kept: {N} |" in REPORT
    assert f"| {_spread(ro['share_of_normals_pointing_inward'])} |" in REPORT
    assert RECORD["reading_orientation"]["both"] == N
    assert f"both (mirrored and upside down): {N} |" in REPORT
    assert f"| {_spread(RECORD['ink_share'])} |" in REPORT
    assert f"| {_spread(RECORD['largest_tile_ink_share'])} |" in REPORT
    assert f"| {RECORD['tiles_scored']:,} |" in REPORT
    assert f"| {RECORD['rendered_pixels']:,} |" in REPORT
    first = RECORD["inspection_order_first_ten"]
    assert ", ".join(first) in FLAT
    assert (
        f"(median {F129['ink_share']['median']} and {F129['largest_tile_ink_share']['median']})"
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
    worst = max(
        RECORD["by_winding"],
        key=lambda w: RECORD["by_winding"][w]["geometry"]["inward_against_axis"],
    )
    assert (
        f"The most inward winding, {worst}, points inward on {most} of its nodes"
        in FLAT
    )
    assert f"still points outward on {round(1 - most, 4)} of its nodes" in FLAT
    assert (
        f"gives a median {g['inward_against_band_centre_median']} inward here" in FLAT
    )


def test_the_stacked_pairs_are_the_records():
    st = RECORD["stacked"]
    assert st["line"] == 0.3
    assert all((v > st["line"]) == (k in st["stacked"]) for k, v in st["pairs"].items())
    names = st["stacked"]
    assert (
        f"Of the {len(st['pairs'])} pairs of neighbouring windings (both read, indices one apart), "
        f"{len(names)} have more than 30%" in FLAT
    )
    assert _names(names) in FLAT
    f129 = F129["stacked"]
    assert (
        f"On PHerc. 0813, {len(f129['stacked'])} of {len(f129['pairs'])} pairs were stacked"
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
    assert (
        f"| final nodes within 2 voxels of the snapped triangles | {g['on_snapped_triangles_median']} |"
        in REPORT
    )


def test_the_trusted_shares_are_the_records():
    g, by = RECORD["geometry"], RECORD["by_winding"]
    trusted = {w: r["geometry"]["trusted"] for w, r in by.items()}
    assert g["trusted_median"] == round(float(statistics.median(trusted.values())), 4)
    assert (
        f"Median {g['trusted_median']} ({min(trusted.values())} to {max(trusted.values())})"
        in FLAT
    )
    assert min(trusted.values()) >= 0.8 and "No winding is under 0.4" in FLAT
    f129 = {w: r["geometry"]["trusted"] for w, r in F129["by_winding"].items()}
    assert (
        f"At PHerc. 0813 the median was {F129['geometry']['trusted_median']}, and "
        f"{sum(v < 0.4 for v in f129.values())} of its {len(f129)} windings were under 0.4"
        in FLAT
    )
    assert f"layers inward is a median {g['other_side_median']}" in FLAT


def test_the_snap_passes_are_quoted_from_the_snaps_own_report():
    sp = DESCRIBED["snap_passes"]
    rows = [sp["before_pass_1"], sp["before_pass_2"], sp["before_pass_3"]]
    assert all(r["windings"] == N for r in rows)
    assert (
        "| nodes within 2 voxels of the sheet run's centre | "
        + " | ".join(str(r["already_on_median"]) for r in rows)
        + " |"
    ) in REPORT
    assert (
        "| median move of the pass, voxels | "
        + " | ".join(f"{r['median_abs_off_median']:g}" for r in rows)
        + " |"
    ) in REPORT
    assert (
        "| share of nodes whose move was rejected as a jump | "
        + " | ".join(str(r["rejected_median"]) for r in rows)
        + " |"
    ) in REPORT
    added = round(rows[2]["already_on_median"] - rows[1]["already_on_median"], 3)
    assert f"Passes 2 and 3 added {added}" in FLAT
    f129 = sp["pherc0813_before_its_one_pass"]
    assert f129["windings"] == F129["windings"]
    assert f"(0.427 against {f129['already_on_median']})" in FLAT
    assert f"(0.074 against {f129['rejected_median']})" in FLAT
    assert "How this band would have read with one pass was not tested" in FLAT


def test_the_outer_sheet_check_is_quoted_from_its_numbers():
    assert DESCRIBED["finding"] == 133 and (ROOT / DESCRIBED["script"]).exists()
    assert DESCRIBED["z_working"] == (10250 + 11750) / 2
    assert f"at z {DESCRIBED['z_working']:.0f}" in FLAT
    for w, row in DESCRIBED["windings"].items():
        lo, hi = row["sheet_runs_beyond_p10_p90"]
        gap = row["outermost_sheet_minus_winding_radius_working_median"]
        cell = f"{row['sheet_runs_beyond_median']:g} ({lo:g} to {round(hi, 1):g})"
        assert f"| {w} | {cell} | {gap} |" in REPORT, w
    last = DESCRIBED["windings"]["w129"]
    gap = last["outermost_sheet_minus_winding_radius_working_median"]
    assert gap > 0 and last["sheet_runs_beyond_median"] > 0
    assert (
        f"the outermost fitted winding still has a median of {last['sheet_runs_beyond_median']:g} "
        f"predicted-sheet runs outside it, {gap:.0f} voxels ({gap * 8.64e-3:.1f} mm at 8.64 µm)"
        in FLAT
    )
    assert "8.64 µm" in REG
    # PHerc. 0813's fit ran past its edge; this one stops short
    f129 = F129_OUTER["windings"]["w129"][
        "outermost_sheet_minus_winding_radius_working_median"
    ]
    assert f129 < 0 < gap


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
    assert "That is about 14 h in all" in REG
    # the first start, from its kept step log (07:45:23 to its kill at 09:08:20)
    first = 2773 + 893 + 0 + 1163 + 148
    assert first == (9 * 3600 + 8 * 60 + 20) - (7 * 3600 + 45 * 60 + 23)
    assert f"{_hms(first)} in all" in FLAT
    hh, mm = divmod(round((total + first) / 60), 60)
    assert f"With it, the run took {hh} h {mm} min" in FLAT
    steps = RECORD["steps"]
    assert f"| snap, three passes | {steps['snap']['seconds']} s |" in REPORT
    assert f"| orient | {steps['orient']['seconds']} s |" in REPORT
    assert f"| summarise | {_hms(steps['summarise']['seconds'])} |" in REPORT
    for name in ("flatten", "render", "studio"):
        s = steps[name]
        assert (
            f"{_hms(s['seconds_total'])} (median {s['seconds_median']} s, at most {s['seconds_max']} s)"
            in REPORT
        ), name
    assert chain["read"]["seconds"] < _read_seconds(
        RECORD
    )  # overlapped: less than its steps' sum


def test_the_overlap_is_measured_as_registered():
    steps, read = RECORD["steps"], RECORD["chain"]["steps"]["read"]["seconds"]
    one_after_another = _read_seconds(RECORD)
    ratio = round(read / one_after_another, 2)
    assert (
        f"The read took {read:,} s against {one_after_another:,} s for its steps one after another: **{ratio}**"
        in FLAT
    )
    assert ratio <= 0.8 and "at most 0.8 of the sum of its step times" in REG
    together = steps["render"]["seconds_total"] + steps["studio"]["seconds_total"]
    wall = (20 * 3600 + 34 * 60 + 45) - (17 * 3600 + 35 * 60 + 25)
    assert (
        f"from 17:35:25 to 20:34:45, {_hms(wall)}, against {_hms(together)} of their steps"
        in FLAT
    )
    assert f"took {round(read / N / 60, 1)} minutes" in FLAT
    f129 = F129["chain"]["steps"]["read"]["seconds"] / F129["windings"] / 60
    assert f"against {round(f129, 1)} at PHerc. 0813" in FLAT
    s = steps["studio"]
    assert (
        f"Studio took a median {s['seconds_median']} s a winding against "
        f"{F129['steps']['studio']['seconds_median']} s there, and {round(s['seconds_total'] / (3.5 * 3600), 1)} "
        "of the registered 3.5 hours" in FLAT
    )
    assert "about 3.5 h of Studio with the skip" in REG
    f = steps["flatten"]["seconds_total"]
    assert (
        f"took {f / (5 * 3600):.2f} to {f / (4 * 3600):.2f} of its registered 4 to 5 hours"
        in FLAT
    )
    assert f"at a median {steps['flatten']['seconds_median']} s a winding" in FLAT


def test_the_canvases_disk_and_gpu_are_the_records():
    c = RECORD["render_canvas_megapixels"]
    assert f"median {c['median']} million pixels ({c['min']} to {c['max']})" in FLAT
    assert f"against PHerc. 0813's {F129['render_canvas_megapixels']['median']}" in FLAT
    assert "canvases about 1.2 times as long" in REG
    disk = RECORD["bytes_on_disk"] | RECORD["chain"]["bytes_on_disk"]
    assert (
        f"the inputs take {disk['inputs'] / 1e9:.1f} GB and the tracks {disk['tracks'] / 1e9:.1f} GB"
        in FLAT
    )
    assert (
        "from a 13.1 GB track store" in REG
        and "(the track store's listing was 13.1 GB)" in FLAT
    )
    assert f"The renders take {disk['renders'] / 1e9:.1f} GB" in FLAT
    assert f"Studio's maps {disk['studio_maps'] / 1e9:.1f} GB" in FLAT
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
    assert "reports/first_letters_0800_studio_band.md" in STRATEGY
    assert "finding 133" in FLAT_STRATEGY
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
    g = RECORD["geometry"]
    assert (
        f"a median {g['predicted_sheet_within_2_median']['final']} of the rendered nodes"
        in FLAT_STRATEGY
    )
    assert "(the read took 0.68 of its steps' time)" in FLAT_STRATEGY
    # finding 133's paragraph comes after finding 129's and before the kill criterion
    at = FLAT_STRATEGY.index("first_letters_0800_studio_band.md")
    assert FLAT_STRATEGY.index("first_letters_0813_studio_band.md") < at
    assert at < FLAT_STRATEGY.index("**Kill criterion.**")
