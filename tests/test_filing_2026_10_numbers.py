"""Every number in the October 2026 filing draft must match the artifact it comes from.

Same discipline as test_filing_numbers_match_sources.py for September: a figure in the filing text is a
claim, and the claim is only as good as the file it was read from. Each test recomputes the figure from the
committed JSON and asserts the draft states it.
"""

import json
import statistics
from pathlib import Path

import pytest

from scripts.sibling_checkouts import main_checkout

_REPO = Path(__file__).resolve().parent.parent
_DRAFT = _REPO / "docs/PRIZE_FILING_2026-10_DRAFT.md"
_F72 = _REPO / "reports/scorer_vs_labels.json"
_F71 = _REPO / "reports/interp_vs_labels.json"
_F70 = _REPO / "reports/interp_windows.json"

pytestmark = pytest.mark.skipif(
    not (_DRAFT.exists() and _F72.exists() and _F71.exists() and _F70.exists()),
    reason="draft or source artifact absent",
)


def _text() -> str:
    # the draft wraps lines; compare on single-spaced text
    return " ".join(_DRAFT.read_text().split())


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%".replace("-", "−")


def test_segment_count_range_matches_finding_72():
    d = json.loads(_F72.read_text())
    totals = [r["d_total"] for r in d["segments"]]
    assert f"{_pct(min(totals))} to {_pct(max(totals))} per segment" in _text()


@pytest.mark.skipif(
    not (_REPO / "reports/supervised_reanalysis.json").exists(),
    reason="supervised re-analysis artifact absent",
)
def test_faithfulness_claim_matches_finding_72():
    # Quoted where the labels are defined, as the correction (finding 77) registered for this draft.
    d = json.loads((_REPO / "reports/supervised_reanalysis.json").read_text())
    rows = [r for r in d["f72"]["prob"]["rows"] if r["status"] == "compared"]
    resolved = [r for r in rows if r["d_ap_ci"][0] > 0 or r["d_ap_ci"][1] < 0]
    assert len(rows) == 8 and all(abs(r["d_ap"]) < 0.01 for r in rows)
    assert len(resolved) == 1
    txt = _text()
    assert (
        "(where the labels are defined, its |ΔAP| is < 0.01 in all 8; 1 of 8 resolved, by "
        f"{abs(resolved[0]['d_ap']):.3f})" in txt
    )
    # the whole-surface figure, which the supervised rows do not reproduce
    assert "|ΔAP| < 0.001 in all 8, none resolved" not in txt


def test_the_eight_labelled_segments_are_named():
    d = json.loads(_F72.read_text())
    txt = _text()
    for r in d["segments"]:
        assert f"`{r['segment']}`" in txt


def test_failed_prediction_fraction_matches_finding_72():
    s = json.loads(_F72.read_text())["summary"]
    assert round(s["frac_windows_abs_d_ge_5pct"] * 100) == 15
    assert "the count was sensitive in 15% of windows, not ≥ 25%" in _text()
    held = json.loads(_F72.read_text())["predictions_held"]
    assert held["p1_count_sensitive_ge_25pct_windows"] is False
    assert held["p2_faithfulness_abs_dAP_lt_0.01_in_6"] is True


def test_finding_70_magnitude_and_its_failed_prediction():
    d = json.loads(_F70.read_text())
    lo, hi = d["summary"]["d_fg_range"]
    assert round(max(abs(lo), abs(hi)) * 100) == 20
    assert d["predictions_held"]["fg_abs_below_1pct_every_window"] is False
    assert "it moved up to ±20%" in _text()


def test_finding_71_prediction_1_failed_on_exclusions():
    d = json.loads(_F71.read_text())
    assert d["predictions_held"]["p1_abs_dAP_lt_0.02_in_6_of_8"] is False
    assert d["summary"]["n_excluded"] == 3
    assert "failed on three exclusions" in _text()


def test_about_one_percent_per_window_in_villas_pipeline():
    d = json.loads(_F72.read_text())
    ws = sorted(abs(w["d"]) for r in d["segments"] for w in r["windows"])
    n = len(ws)
    median = (ws[n // 2] + ws[(n - 1) // 2]) / 2
    assert 0.005 <= median < 0.015  # "about 1%"
    assert "about 1% per window on villa's 20-voxel segment meshes" in _text()


_F73 = _REPO / "reports/scorer_vs_labels_coarse.json"


@pytest.mark.skipif(not _F73.exists(), reason="finding 73 artifact absent")
def test_coarse_grid_numbers_match_finding_73():
    d = json.loads(_F73.read_text())
    txt = _text()
    totals = [r["d_total"] for r in d["segments"]]
    assert f"{_pct(min(totals))} to {_pct(max(totals))} per segment" in txt
    lo, hi = d["summary"]["window_d_range"]
    assert f"({_pct(lo)} to {_pct(hi)} per window)" in txt
    ws = sorted(abs(w["d"]) for r in d["segments"] for w in r["windows"])
    n = len(ws)
    assert f"{100 * (ws[n // 2] + ws[(n - 1) // 2]) / 2:.1f}% median" in txt
    ge = sum(r["prob"]["d_ap"] >= 0 for r in d["segments"])
    assert ge == 2 and "2 of 8, not ≥ 6" in txt
    # the raw-render size (~1% of AP) is bound to the supervised re-analysis:
    # test_band_and_route_numbers_are_the_supervised_ones


_VAL = _REPO / "reports/inkagree_validation.json"


@pytest.mark.skipif(not _VAL.exists(), reason="inkagree validation artifact absent")
def test_inkagree_validation_claim_matches_its_artifact():
    v = json.loads(_VAL.read_text())
    assert v["n_ok"] == v["n"] == 16
    assert "reproduces findings 71 and 72 exactly (16 of 16 segment results" in _text()
    assert "https://github.com/jonmarrs/inkagree" in _DRAFT.read_text()


_SUP = _REPO / "reports/supervised_reanalysis.json"


def _rel_median(rows):
    r = sorted(x["d_ap"] / x["ap_a"] for x in rows if x["status"] == "compared")
    n = len(r)
    return 100 * (r[n // 2] + r[(n - 1) // 2]) / 2


@pytest.mark.skipif(not _SUP.exists(), reason="supervised re-analysis artifact absent")
def test_band_and_route_numbers_are_the_supervised_ones():
    d, txt = json.loads(_SUP.read_text()), _text()
    f74 = d["f74"]
    assert (
        f74["0.25"]["tally"]["resolved_a"] == 8
        and round(-_rel_median(f74["0.25"]["rows"])) == 6
    )
    assert (
        f74["2.0"]["tally"]["resolved_a"] == 8
        and round(-_rel_median(f74["2.0"]["rows"])) == 20
    )
    assert f74["1.0"]["tally"]["resolved_a"] < 6  # no consistent difference vs 1.0
    assert (
        "(0.25: 8 of 8, about −6% of AP)" in txt and "(2.0: 8 of 8, about −20%)" in txt
    )
    assert "Against 1.0 there is no consistent difference" in txt
    f75 = d["f75"]
    assert (
        f75["0.5"]["tally"]["resolved_a"] == 8
        and round(-_rel_median(f75["0.5"]["rows"])) == 5
    )
    assert (
        f75["2.0"]["tally"]["resolved_b"] == 8
        and round(_rel_median(f75["2.0"]["rows"])) == 8
    )
    assert "(8 of 8, about +5% AP)" in txt and "(8 of 8, about +8%)" in txt
    assert (
        d["f73"]["strip"]["tally"]["resolved_b"] == 8
        and round(_rel_median(d["f73"]["strip"]["rows"])) == 1
    )
    assert "1% of AP)" in txt


_F76 = _REPO / "reports/objective_vs_labels.json"


@pytest.mark.skipif(not _F76.exists(), reason="finding 76 artifact absent")
def test_objective_vs_labels_claim_matches_finding_76():
    d = json.loads(_F76.read_text())
    assert d["predictions_held"]["p1_scorer_rho_gt_0.3_ci_excludes_0"] is False
    assert f"ρ = {d['q1']['scorer']['rho']:+.2f}" in _text()


def _sibling_version(name: str) -> str | None:
    import re

    pp = main_checkout().parent / name / "pyproject.toml"
    if not pp.exists():
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', pp.read_text(), re.M)
    return m.group(1) if m else None


@pytest.mark.parametrize(
    "tool, pattern",
    [
        ("inkdelta", "[inkdelta](https://github.com/jonmarrs/inkdelta) {v} "),
        ("inkagree", "now {v}, which evaluates"),
    ],
)
def test_cited_tool_versions_are_the_current_ones(tool, pattern):
    """The draft said inkdelta 0.5.1 for days after 0.5.2 shipped; tie the cite to the tool's own pyproject."""
    v = _sibling_version(tool)
    if v is None:
        pytest.skip(f"{tool} checkout not beside this repo")
    assert pattern.format(v=v) in _text(), f"draft does not cite {tool} {v}"


_F83 = _REPO / "reports/fiber_heldout_split.json"


@pytest.mark.skipif(not _F83.exists(), reason="finding 83 artifact absent")
def test_fiber_heldout_numbers_match_finding_83():
    d, txt = json.loads(_F83.read_text()), _text()
    assert (
        len(d["cubes"]) == 10 and "adds 10 annotated cubes the model never saw" in txt
    )

    def median(xs):
        xs = sorted(xs)
        return (xs[len(xs) // 2] + xs[(len(xs) - 1) // 2]) / 2

    s3 = d["descriptive"]["s3_cc_coverage"]
    assert len(s3) == 8 and round(median(s3.values()), 3) == round(
        d["descriptive"]["s3_cc_coverage_median"], 3
    )
    in512 = round(median(d["in_sample_cc_coverage"]["512"].values()), 3)
    s3_claim = (
        f"{median(s3.values()):.3f}, against {in512:.3f} on the in-sample 512³ cubes"
    )
    assert txt.count(s3_claim) == 2, (
        s3_claim
    )  # once in part (2), once in the failed-prediction list
    assert d["predictions"]["P1_s3_median_cc_coverage_below_0.8130"] is False
    assert d["predictions"]["P2_both_s5_cc_coverage_below_0.8666"] is True

    s5 = sorted(d["descriptive"]["s5_cc_coverage"].values(), reverse=True)
    in256 = d["in_sample_cc_coverage"]["256"].values()
    assert (
        f"Coverage is {s5[0]:.2f} and {s5[1]:.2f}, against {min(in256):.2f}–{max(in256):.2f} on the in-sample "
        "Scroll-5 256³ cubes" in txt
    )
    assert "Twenty-two of my registered predictions failed" in txt


def test_scrollgt_cite_is_its_newest_tag():
    """The URL field cited v0.4.1 after v0.5.0 was tagged; tie it to the sibling checkout's newest tag."""
    import subprocess

    sg = main_checkout().parent / "scrollgt"
    try:
        out = subprocess.run(
            ["git", "-C", str(sg), "tag", "--list", "v*", "--sort=-v:refname"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        out = []
    if not out:
        pytest.skip("scrollgt checkout with tags not beside this repo")
    assert (
        f"https://github.com/jonmarrs/scrollgt/tree/{out[0]}" in _DRAFT.read_text()
    ), f"cite ScrollGT {out[0]}"


def test_scrollgt_0_7_0_claims_match_its_released_data():
    """The 0.7.0 bullet's figures, read from the data at ScrollGT's v0.7.0 tag: every row re-scored with its scoring
    version 3, and the held-out cubes where our tracer leads connected components on merge-penalized ERL."""
    import os
    import subprocess

    sg = main_checkout().parent / "scrollgt"
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(sg), *args], capture_output=True, text=True, env=env
        )

    listing = git("ls-tree", "--name-only", "v0.7.0", "data/")
    if listing.returncode != 0:
        pytest.skip("scrollgt checkout with tag v0.7.0 not beside this repo")
    metas = [json.loads(git("show", f"v0.7.0:{d}/meta.json").stdout)
             for d in listing.stdout.split() if d.startswith("data/fibers_")]  # fmt: skip
    rows = [r for m in metas for r in m["floors"].values()]
    assert len(metas) == 21 and all(r["scoring_version"] == 3 for r in rows)
    held = [m["floors"] for m in metas if m["split"] == "held_out"]
    leads = sum(f["tracer_strict_relink"]["erl_merge_penalized"] > f["floor_connected_components"]["erl_merge_penalized"]
                for f in held)  # fmt: skip
    text = " ".join(_text().split())
    assert f"All {len(rows)} published rows were re-scored" in text
    assert f"on {leads} of {len(held)} cubes, not {len(held)}" in text


_F84 = _REPO / "reports/fiber_miss_diagnostic.json"
_NEW_S5 = ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")


@pytest.mark.skipif(not _F84.exists(), reason="finding 84 artifact absent")
def test_scroll5_miss_numbers_match_finding_84():
    d, txt = json.loads(_F84.read_text()), _text()
    cubes, v = d["cubes"], d["verdict"]
    assert v["status"] == "OK" and not any(v["frame_offset_flag"].values())
    new = [cubes[k] for k in _NEW_S5]
    gain = max(c["shift"]["gain"] for c in new)
    assert f"the best shift within ±4 voxels gains at most {gain:.4f}" in txt
    c01 = [c["sweep"]["coverage"]["0.1"] for c in new]
    in_s5 = [
        c["sweep"]["coverage"]["0.5"]
        for k, c in cubes.items()
        if k.startswith("s5_") and c["split"] != "held_out"
    ]
    assert max(c01) < min(in_s5)  # "still below every in-sample Scroll-5 cube"
    assert f"at P ≥ 0.1 coverage is {c01[0]:.3f} and {c01[1]:.3f}" in txt

    def hard(c):
        return 100 * (1 - c["sweep"]["coverage"]["0.05"])

    ins = [hard(c) for c in cubes.values() if c["split"] != "held_out"]
    s3 = [hard(c) for k, c in cubes.items() if k.startswith("s3_")]
    assert (
        f"{hard(new[0]):.1f}% and {hard(new[1]):.1f}% of their hand-traced fiber has no voxel at P ≥ 0.05"
        f" within 2 voxels, against {min(ins):.1f}–{max(ins):.1f}% in sample and {min(s3):.1f}–{max(s3):.1f}%"
        " on Scroll 3" in txt
    )
    assert v["predictions"]["P2_threshold_0.1_does_not_rescue"] is True
    assert v["predictions"]["P3_misses_no_softer_than_in_sample"] is False
    soft = {round(c["sweep"]["soft_miss_fraction"], 3) for c in new}
    assert len(soft) == 1
    assert (
        f"the soft-miss fraction is {soft.pop():.3f} on both, above the in-sample maximum of "
        f"{v['in_sample_s5_max_soft_miss']:.3f}" in txt
    )


_F85 = _REPO / "reports/afv_generator_entrant.json"
_F85_GT = _REPO / "reports/erl_coverage_conditioning.json"


@pytest.mark.skipif(
    not (_F85.exists() and _F85_GT.exists()), reason="finding 85 artifacts absent"
)
def test_generator_numbers_match_finding_85():
    d, g, txt = json.loads(_F85.read_text()), json.loads(_F85_GT.read_text()), _text()
    assert d["status"] == "OK" and not d["failed_runs"]
    rows, comp = d["generator_rows"], d["comparators"]
    assert len(rows) == 21
    other = [r["coverage"] for k, r in rows.items() if k not in _NEW_S5]
    assert (
        f"cover {100 * min(other):.0f}–{100 * max(other):.0f}% of the hand-traced fiber length on {len(other)} cubes"
        in txt
    )
    new = [rows[k]["coverage"] for k in _NEW_S5]
    assert (
        f"and {100 * new[0]:.0f}% and {100 * new[1]:.0f}% on the two new Scroll-5 cubes"
        in txt
    )
    s3 = d["s3_cubes"]
    pen_lead = sum(
        rows[k]["erl_merge_penalized"] > comp[k]["tracer"]["erl_merge_penalized"]
        for k in s3
    )
    assert (
        pen_lead == len(s3) == 8
        and "ranked it above our tracer on all 8 Scroll-3 cubes" in txt
    )
    e = g["entrant_gt_normalized"]
    raw = sum(e[k]["generator"]["erl_gt"] < e[k]["tracer"]["erl_gt"] for k in e)
    pen = sum(e[k]["generator"]["erl_pen_gt"] < e[k]["tracer"]["erl_pen_gt"] for k in e)
    assert (
        f"on {raw} of {len(e)} cubes (raw) and {pen} of {len(e)} (merge-penalized)"
        in txt
    )
    p = d["predictions"]
    in_sample = [k for k in rows if k.startswith(("s1_", "s5_")) and k not in _NEW_S5]
    above = sum(rows[k]["erl"] > comp[k]["tracer"]["erl"] for k in in_sample)
    assert p["P1_raw_erl_above_tracer_on_9_of_11"] is False and len(in_sample) == 11
    assert f"beat our tracer's on 9 of 11 in-sample cubes: it did on {above})" in txt
    # Qualzz20/afv_fiber_9um model card at revision e189af75 (read 2026-10-12): "Native pitch is 8.64 or 9.362 µm"
    assert d["revision"].startswith("e189af75")
    assert "finer than the 8.64 and 9.362 µm pitches its fine-tune trained on" in txt


_F91 = _REPO / "reports/neural_tracer_entrant.json"


@pytest.mark.skipif(not _F91.exists(), reason="finding 91 artifact absent")
def test_neural_tracer_numbers_match_finding_91():
    d, txt = json.loads(_F91.read_text()), _text()
    assert d["status"] == "OK" and not d["failed_runs"]
    assert all(d["predictions"].values()) and len(d["predictions"]) == 4
    assert "(finding 91; all four predictions held)" in txt
    rows, comp, s3 = d["neural_rows"], d["comparators"], d["s3_cubes"]
    assert len(rows) == 21 and len(s3) == 8
    assert d["checkpoint"].startswith("scrollprize/fiber_single_small@")

    def pen(k, who=None):
        return (comp[k][who] if who else rows[k])["erl_merge_penalized"]

    def cov(k, who=None):
        return (comp[k][who] if who else rows[k])["coverage"]

    # Scroll 3: first on merge-penalized ERL against every entrant
    for who in ("tracer", "generator", "cc"):
        assert all(pen(k) > pen(k, who) for k in s3), who
    ratio = [pen(k) / pen(k, "tracer") for k in s3]
    med = statistics.median
    assert (
        f"It is above our tracer on 8 of 8 cubes ({min(ratio):.2f}–{max(ratio):.2f}×, median "
        f"{med(pen(k) for k in s3):.2f} against {med(pen(k, 'tracer') for k in s3):.2f}), and above #1934's "
        "generator and connected components on 8 of 8" in txt
    )
    below = sum(cov(k) < cov(k, "tracer") for k in s3)
    assert (
        f"median coverage {med(cov(k) for k in s3):.3f}, against our tracer's "
        f"{med(cov(k, 'tracer') for k in s3):.3f} (below it on {below} of 8) and connected components' "
        f"{med(cov(k, 'cc') for k in s3):.3f}" in txt
    )
    # The 11 cubes the mask trained on, and the two held-out Scroll-5 cubes
    in_sample = [k for k in rows if k not in s3 and k not in _NEW_S5]
    assert len(in_sample) == 11 and all(k.startswith(("s1_", "s5_")) for k in in_sample)
    leads = sum(pen(k, "tracer") > pen(k) for k in in_sample)
    assert (
        f"our tracer leads on all {leads} (median {med(pen(k) for k in in_sample):.2f} against "
        f"{med(pen(k, 'tracer') for k in in_sample):.2f})" in txt
    ) and leads == 11
    assert (
        f"On the two held-out Scroll-5 cubes its coverage is {cov(_NEW_S5[0]):.3f} and {cov(_NEW_S5[1]):.3f}"
        in txt
    )
    # "both repeated cubes reproduce exactly"
    repeat = d["descriptive_repeat"]
    assert len(repeat) == 2 and "both repeated cubes reproduce exactly" in txt
    for k, r in repeat.items():
        assert {m: r["second_run"][m] for m in rows[k] if m != "stop_reasons"} == {
            m: v for m, v in rows[k].items() if m != "stop_reasons"
        }, k


_PR2044 = _REPO / "docs/VILLA_DRAFT_ink_metrics_sequential_folds.md"
_PR2044_LOG = _REPO.parent.parent / "spiral_out/inkfix_measure/measure.log"


@pytest.mark.skipif(not _PR2044.exists(), reason="#2044 draft absent")
def test_2044_memory_figures_match_its_measurement():
    """The #2044 paragraph's figures, read from the table that went out verbatim in the PR body (and, when the raw
    measurement log is beside the repo, from that log)."""
    import re

    rows = {}
    for line in _PR2044.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[0].startswith("w"):
            rows[(cells[0].split(",")[0], cells[1])] = cells
    txt = _text()
    stock = rows[("w120–w129", "stock")]
    seq = rows[("w120–w129", "`--sequential-folds`")]
    killed_s = re.search(r"OOM-killed (\d+) s in", stock[2]).group(1)
    assert (
        f"stock scoring was killed for lack of memory {killed_s} s in, at {stock[3]}"
        in txt
    )
    assert f"`--sequential-folds` scored it with a {seq[3]} peak in {seq[4]}" in txt
    w, h = (
        int(x.replace(",", ""))
        for x in re.search(r"([\d,]+) × ([\d,]+)", stock[0]).groups()
    )
    assert (
        f"(w120–w129, {stock[0].split(', ')[1]} = {round(w * h / 1e6)}M px)"
        in _PR2044.read_text()
    )
    assert f"on the w120–w129 strip ({round(w * h / 1e6)}M px)" in txt
    inner = [int(re.search(r"ok, ([\d,]+)", c[2]).group(1).replace(",", "")) for k, c in rows.items()
             if k[0] == "w010–w019"]  # fmt: skip
    assert len(inner) == 3 and (max(inner) - min(inner)) / min(inner) < 0.00005
    assert "the three modes' counts agree to within 0.005%" in txt
    assert "one RTX 4090, each run in a 26 GiB memory cgroup" in " ".join(
        _PR2044.read_text().split()
    )
    assert "one RTX 4090 in a 26 GiB memory limit" in txt
    if _PR2044_LOG.exists():
        log = _PR2044_LOG.read_text()
        assert (
            re.search(
                r"outer_sequential rc_seconds=0 (\d+) anon_peak_GB=([\d.]+)", log
            ).groups()
            == (
                seq[4].replace(",", "").removesuffix(" s"),
                "13.77",
            )
            and seq[3] == "13.8 GB"
        )
        assert (
            "outer_stock rc_seconds=scope-killed anon_peak_GB=27.55" in log
            and stock[3] == "≥ 27.6 GB"
        )


def test_quantified_claims_match_their_sources():
    """The figures added when the draft was made quantitative (2026-10-12), each read from its artifact."""
    import re

    txt = _text()

    # #2022: the five failures listed in the PR body that went out, and the 4-GPU probe
    body = (_REPO / "docs/villa_pr_autoresearch_runner_body.md").read_text()
    n_ways = sum(line.startswith("- **") for line in body.splitlines())
    assert n_ways == 5 and f"the launch failed in {n_ways} measured ways" in txt
    assert f"failed the documented launch in {n_ways} ways" in txt
    rep = (_REPO / "reports/villa_runner_layout_vs_autoresearch_doc.md").read_text()
    gpus = (
        re.search(r"CUDA_VISIBLE_DEVICES=([\d,]+)` as the doc says", rep)
        .group(1)
        .split(",")
    )
    assert f"--nproc-per-node={len(gpus)}" in rep
    assert (
        f"{len(gpus)} GPUs pinned as documented, it ran the fit as 1 process, not {len(gpus)}"
        in txt
    )
    summ = " ".join((_REPO / "reports/SPIRAL_FINDINGS_SUMMARY.md").read_text().split())
    assert "Launched as documented, it exits 2 before starting" in summ
    assert "it exited with status 2 before starting" in txt
    draft = (_REPO / "docs/VILLA_DRAFT_autoresearch_runner_section.md").read_text()
    assert "+11 / −10" in draft and "#2022 fixed the doc (1 file, +11/−10)" in txt

    # inkdelta 0.3.0 on villa's own runner layout
    table = re.findall(r"^\| `(check|compare|noise)[^|]*` \| ([^|]+) \|$", rep, re.M)
    failed = [r for r in table if "FAIL" in r[1] or "INVALID" in r[1]]
    assert (
        len(table) == 4
        and f"0.3.0 failed {len(failed)} of the {len(table)} runs we tried" in txt
    )

    # the loop metric's fit-to-fit noise (finding 57)
    f = json.loads((_REPO / "reports/pooled_fit_only_floor.json").read_text())
    lo, hi = f["ci"]
    assert (
        f"{100 * f['pooled_cv']:.1f}% (pooled CV, 95% CI {100 * lo:.1f}–{100 * hi:.1f}%, finding 57)"
        in txt
    )

    # grid-size scaling, in part (2) as well as the disclosure
    d73 = json.loads(_F73.read_text())
    ws = sorted(abs(w["d"]) for r in d73["segments"] for w in r["windows"])
    n = len(ws)
    assert (
        f"about 1% per window on 20-voxel meshes, a {100 * (ws[n // 2] + ws[(n - 1) // 2]) / 2:.1f}% median"
        in txt
    )

    # ScrollGT 0.5.0 (finding 82)
    d82 = json.loads((_REPO / "reports/scrollgt_current_annotations.json").read_text())
    grow = [
        c["current"]["oracle"]["n_gt_fibers"] / c["old"]["oracle"]["n_gt_fibers"] - 1
        for c in d82["cubes"].values()
    ]
    assert (
        f"({100 * min(grow):.0f}–{100 * max(grow):.0f}% more annotated fibers)" in txt
    )
    cov = [
        v["coverage_old_to_current"]["floor_connected_components"]
        for v in d82["descriptive"].values()
    ]
    old, cur = [c[0] for c in cov], [c[1] for c in cov]
    assert (
        f"falls from {min(old):.2f}–{max(old):.2f} to {min(cur):.2f}–{max(cur):.2f}"
        in txt
    )

    # ScrollGT 0.7.0's exploit, on our tracer (finding 85 control)
    g = json.loads(_F85_GT.read_text())["deletion_control"]
    base, cut = g[0], next(r for r in g if r["min_voxels"] == 400)
    assert base["min_voxels"] == 0
    rise = round(100 * (cut["erl"] / base["erl"] - 1))
    assert (
        f"under 400 voxels raised it {rise}% ({base['erl']:.2f} → {cut['erl']:.2f}) while coverage fell from "
        f"{base['coverage']:.2f} to {cut['coverage']:.2f}" in txt
    )


def test_finding_82_fiber_growth_range_is_the_scored_one():
    """Finding 82 published "28–53% more fibers"; the scored counts give 22–53% (s5_14997: 147 -> 179). Bind every
    statement of the range to the JSON so it cannot drift again."""
    d82 = json.loads((_REPO / "reports/scrollgt_current_annotations.json").read_text())
    grow = [
        c["current"]["oracle"]["n_gt_fibers"] / c["old"]["oracle"]["n_gt_fibers"] - 1
        for c in d82["cubes"].values()
    ]
    rng = f"{100 * min(grow):.0f}–{100 * max(grow):.0f}% more"
    for f in (
        "reports/scrollgt_current_annotations.md",
        "reports/SPIRAL_FINDINGS_SUMMARY.md",
    ):
        t = " ".join((_REPO / f).read_text().split())
        assert rng in t, f
        assert "28–53% more" not in t.replace('from "28–53%"', "").replace(
            "from 28–53%", ""
        ), f


_F92 = _REPO / "reports/neural_tracer_pitch.json"


@pytest.mark.skipif(not _F92.exists(), reason="finding 92 artifact absent")
def test_pitch_numbers_match_finding_92():
    d, txt = json.loads(_F92.read_text()), _text()
    assert d["status"] == "OK" and not d["failed_runs"] and not d["identity_problems"]
    rows, native = d["pitch_rows"], d["native_rows"]
    assert len(rows) == 21 and all(
        r["erl_merge_penalized"] < native[c]["erl_merge_penalized"]
        for c, r in rows.items()
    )
    ratio = d["median_pen_ratio_pitch_over_native"]
    lead, s3 = d["s3_leading_tracer"]
    trails, ins = d["in_sample_trailing_tracer"]
    assert (lead, s3, trails, ins) == (0, 8, 11, 11)
    assert (
        f"it scores lower on all 21 cubes (merge-penalized ERL a median {ratio:.2f} of the rows above) and leads our "
        f"tracer on none of the {s3} Scroll-3 cubes. It still trails on all {ins} in-sample cubes"
        in txt
    )
    # ScrollGT 0.8.1 carries the same note on its published row.
    assert (
        "0.8.1 notes, wherever that lead is claimed, that it depends on the pitch: resampled to its 9.6 µm training "
        f"pitch, the tracer leads ours on none of the {s3} Scroll-3 cubes (finding 92). No row changes."
        in txt
    )
    p = d["predictions"]
    assert (
        p["P2_s3_leads_tracer_on_6_of_8"] is False
        and p["P3_median_pen_ratio_within_0.85_1.15"] is False
    )
    assert (
        f"on at least 6 of 8 cubes: it kept it on {lead}; its median merge-penalized ERL would stay within "
        f"0.85–1.15 of the native rows: {ratio:.2f})" in txt
    )


_F93 = _REPO / "reports/neural_tracer_seeding.json"


@pytest.mark.skipif(not _F93.exists(), reason="finding 93 artifact absent")
def test_seeding_numbers_match_finding_93():
    d, txt = json.loads(_F93.read_text()), _text()
    assert (
        d["status"] == "OK"
        and d["conclusion"] == "the seeding scale is not the cause: the note stands"
    )
    assert not any(d["predictions"].values())
    a, b = d["median_pen_ratio_A"], d["median_pen_ratio_B"]
    pitch = json.loads(_F92.read_text())["median_pen_ratio_pitch_over_native"]
    lead_a, s3 = d["s3_leading_tracer_A"]
    rows_b, comp = d["rows_B"], d["comparators"]
    lead_b = sum(
        rows_b[c]["erl_merge_penalized"] > comp[c]["tracer"]["erl_merge_penalized"]
        for c in d["groups"]["s3"]
    )
    assert (lead_a, s3, lead_b) == (0, 8, 7)
    assert (
        f"Seeded per micrometre there, it recovers only to {a:.2f} of the native rows (from {pitch:.2f}) and leads our "
        f"tracer on {lead_a} of {s3} Scroll-3 cubes. Seeded as sparsely at 7.91 µm, it keeps {b:.2f} and its lead on "
        f"{lead_b} of {s3}." in txt
    )
    assert (
        f"recover to at least 0.85 of the native rows: {a:.2f}; regain its Scroll-3 lead on at least 6 of 8 cubes: "
        f"{lead_a}; and, seeded as sparsely at 7.91 µm, fall to at most 0.80: {b:.2f})"
        in txt
    )
    assert "findings 91–94 in" in txt and "`reports/neural_tracer_seeding.md`" in txt


_GTO = _REPO / "reports/neural_tracer_gt_offset.json"


@pytest.mark.skipif(
    not (_GTO.exists() and _F91.exists()), reason="placement artifacts absent"
)
def test_placement_and_offset_numbers_match_their_measurements():
    e, g, txt = json.loads(_F91.read_text()), json.loads(_GTO.read_text()), _text()
    s3 = e["s3_cubes"]
    s5 = [c for c in e["neural_rows"] if c.startswith("s5_") and c.endswith("_512")]

    def ratio(ent, tol4=False):
        def row(c):
            if tol4:
                return e["descriptive_tolerance_4"][c][
                    "tracer" if ent == "neural" else ent
                ]
            return e["neural_rows"][c] if ent == "neural" else e["comparators"][c][ent]

        med = statistics.median
        return med(row(c)["erl_merge_penalized"] for c in s3) / med(
            row(c)["erl_merge_penalized"] for c in s5
        )

    assert len(s5) == 3 and (
        f"({ratio('neural'):.2f}× and {ratio('generator'):.2f}×), and at a 4-voxel tolerance most of that goes "
        f"({ratio('neural', True):.2f}× and {ratio('generator', True):.2f}×)" in txt
    )
    cubes = g["cubes"]
    norm = {c: sum(v * v for v in cubes[c]["shift"]) ** 0.5 for c in cubes}
    big = [c for c in g["groups"]["in_sample"] if norm[c] >= 1]
    off = [cubes[c]["ct"]["t_star"] * norm[c] for c in big]
    gain = [cubes[c]["neural"]["le2_shifted"] - cubes[c]["neural"]["le2"] for c in big]
    assert (
        f"On {len(big)} of the 11 in-sample cubes the ground truth itself sits about a voxel off the CT's fibers"
        in txt
    )
    assert (
        f"the CT alone puts the fibers' centres {min(off):.2f}–{max(off):.2f} voxels off"
        in txt
    )
    assert (
        f"recovers part of the gap ({min(gain):.2f}–{max(gain):.2f} of this tracer's share within 2 voxels)"
        in txt
    )
    # ScrollGT 0.8.2 carries the same measurement as a note on those cubes.
    shifts = [norm[c] for c in big]
    assert (
        f"0.8.2 notes, on those {len(big)} in-sample cubes, that the hand-traced centrelines sit about a voxel off the "
        f"CT's fibers: the two thin entrants agree on a shift of {min(shifts):.2f}–{max(shifts):.2f} voxels, and the CT "
        f"puts the fibers' centres {min(off):.2f}–{max(off):.2f} voxels off (#157). It also notes, where the neural "
        "tracer's in-sample deficit is claimed, that the deficit is a tolerance-2 result on the 512³ cubes (finding "
        "94). No row changes." in txt
    )
    assert (
        "0.8.2 (the placement note on five in-sample cubes, #157, and the tolerance note, finding 94)"
        in txt
    )


_F94 = _REPO / "reports/tolerance4_rescore.json"


@pytest.mark.skipif(not _F94.exists(), reason="finding 94 artifact absent")
def test_tolerance4_numbers_match_finding_94():
    d, txt = json.loads(_F94.read_text()), _text()
    assert d["status"] == "OK" and not d["identity_problems"]
    assert d["predictions"] == {
        "P1_s3_leads_tracer_on_6_of_8": True,
        "P2_in_sample_trails_tracer_on_9_of_11": False,
    }
    pen, med = "erl_merge_penalized", statistics.median
    n, t, pn, pt, g = (
        d["rows_neural"],
        d["rows_tracer"],
        d["published_neural"],
        d["published_tracer"],
        d["groups"],
    )
    s3, ins = g["s3"], g["in_sample"]
    i512 = [c for c in ins if c.endswith("_512")]
    lead, s3n = d["s3_leading_tracer"]
    trail, insn = d["in_sample_trailing_tracer"]
    assert (lead, s3n, trail, insn) == (8, 8, 8, 11)

    def ratio(cubes, a, b):
        return med(a[c][pen] / b[c][pen] for c in cubes)

    assert (
        f"Its Scroll-3 lead holds and widens: a median {ratio(s3, n, t):.2f} times our tracer's merge-penalized ERL, "
        f"against {ratio(s3, pn, pt):.2f} at 2, on {lead} of {s3n} cubes. Its in-sample deficit narrows from "
        f"{ratio(ins, pn, pt):.2f} to {ratio(ins, n, t):.2f} of ours, and reverses on the three in-sample 512³ cubes "
        f"(median {med(n[c][pen] for c in i512):.2f} against {med(t[c][pen] for c in i512):.2f})"
        in txt
    )
    assert (
        f"finding 94 prediction 2 (at tolerance 4, villa's neural tracer would still trail our tracer on at least 9 of "
        f"11 in-sample cubes: it trailed on {trail})." in txt
    )
    assert "findings 91–94 in" in txt and "`reports/tolerance4_rescore.md`" in txt


def test_octant_result_matches_finding_95_and_preserves_its_scope():
    d = json.loads((_REPO / "reports/octant_crop_rescore.json").read_text())
    assert d["status"] == "OK" and not d["identity_problems"]
    rows = d["octants"]
    pen = "erl_merge_penalized"
    lead4 = sum(
        r["neural"]["4.0"][pen] > r["tracer"]["4.0"][pen] for r in rows.values()
    )
    lead2 = sum(
        r["neural"]["2.0"][pen] > r["tracer"]["2.0"][pen] for r in rows.values()
    )
    assert [lead4, len(rows)] == d["neural_leads_at_4"]
    text = _text()
    assert (
        f"{lead4} of {len(rows)}, while at tolerance 2 it leads on {lead2} of {len(rows)}"
        in text
    )
    assert "this tests scoring-window size, not tracing context" in text
    assert "Finding 95 is in `reports/octant_crop_rescore.md`" in text


def _json(rel: str) -> dict:
    p = _REPO / rel
    if not p.exists():
        pytest.skip(f"{rel} not present")
    return json.loads(p.read_text())


def test_install_route_ink_count_is_the_published_image_against_the_source_build():
    # Finding 66 measured the source build against the published image (+5.0% to +9.2%). The draft
    # states the reverse direction, so it is published / source - 1, not the same figures negated.
    d = _json("reports/step2_across_surfaces.json")
    ink = d["ink"]
    pairs = {"up1": ("detfit_up1", "tif_score_pr1905"), "s4": ("detfit_s4", "step2_s4"),
             "s5": ("detfit_s5", "step2_s5"), "s6": ("detfit_s6", "step2_s6")}  # fmt: skip
    short = []
    for surface, (published, source) in pairs.items():
        assert ink[source] / ink[published] - 1 == pytest.approx(
            d["per_surface"][surface]
        )
        short.append(100 * (1 - ink[published] / ink[source]))
    lo, hi = f"{min(short):.0f}", f"{max(short):.0f}"
    assert f"(finding 66: −{lo}% to −{hi}% ink count)" in _text()
    flat = lambda rel: " ".join((_REPO / rel).read_text().split())  # noqa: E731
    assert f"the published image's lower ink count (−{lo} to −{hi}%)" in flat(
        "reports/SPIRAL_FINDINGS_SUMMARY.md"
    )
    assert f"The published image's {lo}–{hi}% lower ink count" in flat(
        "reports/install_route_band_vs_labels.md"
    )


def test_failed_prediction_figures_are_rounded_once_from_their_sources():
    txt = _text()
    # finding 79: the two seed-noise ratios and their intervals
    d = _json("reports/soft_count_study.json")
    p, c = d["pinned_q1"], d["current_q1"]
    q = lambda r: f"R = {r['R']:.2f} [{r['ci'][0]:.2f}, {r['ci'][1]:.2f}]"  # noqa: E731
    assert p["ci"][0] < 1 < p["ci"][1] and c["ci"][1] < 1
    assert f"{q(p)}, no detectable difference; it was on current code, {q(c)})" in txt
    # the shared-p95 re-score of finding 70
    s = _json("reports/shared_p95_rescore.json")
    assert s["prediction_held"]["median_abs_d_shared_below_2.5pct"] is False
    med = 100 * s["summary"]["median_abs_d_shared"]
    assert f"the median |Δ| stayed at {med:.1f}%, not < 2.5%" in txt
    # finding 80: the one 256³ cube the tracer leads, and the cubes it leads on
    cubes = _json("reports/tracer_rescore.json")["cubes"]
    pen = {k: (v["tracer_v2"]["erl_merge_penalized"], v["cc_v2"]["erl_merge_penalized"])
           for k, v in cubes.items()}  # fmt: skip
    lead = [k for k, (t, cc) in pen.items() if t > cc]
    small = [k for k in lead if k.endswith("_256")]
    big = [k for k in cubes if k.endswith("_512")]
    assert len(small) == 1 and set(big) <= set(lead) and len(big) == 3
    n256 = sum(k.endswith("_256") for k in cubes)
    assert all(v["ran"] for v in cubes.values()) and n256 == 8
    assert f"Re-measured with the corrected scorer on all {len(cubes)} cubes:" in txt
    assert txt.count("all eight 256³ cubes") == 2
    t, cc = pen[small[0]]
    stem = small[0].split("_")[:2]
    assert f"it leads on `{'_'.join(stem)}`, {t:.2f} vs {cc:.2f})" in txt
    assert (
        f"on merge-penalized ERL it is ahead on {len(lead)} of {len(cubes)}, "
        "all three 512³ cubes among them" in txt
    )


def test_scale_and_tolerance_figures_match_their_measurements():
    txt = _text()
    if not _F73.exists():
        pytest.skip("finding 73 artifact absent")
    d = json.loads(_F73.read_text())
    lo, hi = d["summary"]["window_d_range"]
    ws = sorted(abs(w["d"]) for r in d["segments"] for w in r["windows"])
    med = 100 * (ws[len(ws) // 2] + ws[(len(ws) - 1) // 2]) / 2
    assert (
        f"a {med:.1f}% median and −{-100 * lo:.0f}% to +{100 * hi:.0f}% per window on "
        "80-voxel grids" in txt
    )
    # where villa's labels are defined: each segment's supervised share of its mesh-valid area
    seg = _json("reports/scorer_sparsity_annotated.json")["per_segment"].values()
    share = [100 * s["in_px"] / (s["in_px"] + s["out_px"]) for s in seg]
    cover = f"({min(share):.0f}–{max(share):.0f}% of each segment's mesh-valid area"
    flat = lambda rel: " ".join((_REPO / rel).read_text().split())  # noqa: E731
    assert len(share) == 8 and cover in txt
    for rel in (
        "reports/SPIRAL_FINDINGS_SUMMARY.md",
        "reports/surface_interpolation_vs_labels.md",
    ):
        assert cover in flat(rel), rel
    # finding 78: the share of villa's annotated ink its scorer marks
    rec = _json("reports/scorer_sparsity_annotated.json")["pooled"]["recall_inside"]
    assert f"its count is sparse (about {100 * rec:.0f}% of annotated ink)" in txt
    # finding 94: villa's neural tracer against ours off Scroll 3, at tolerances 2 and 4
    if not _F94.exists():
        pytest.skip("finding 94 artifact absent")
    t4 = json.loads(_F94.read_text())
    for who in (
        "tracer",
        "cc",
        "neural",
    ):  # the published rows are tolerance 2, the re-score 4
        assert {r["tolerance"] for r in t4[f"published_{who}"].values()} == {2.0}
        assert {r["tolerance"] for r in t4[f"rows_{who}"].values()} == {4.0}
    g = t4["groups"]
    other = g["in_sample"] + g["s5_held_out"]
    leads = lambda tracer, neural: [  # noqa: E731
        c
        for c in other
        if neural[c]["erl_merge_penalized"] > tracer[c]["erl_merge_penalized"]
    ]
    at2 = leads(t4["published_tracer"], t4["published_neural"])
    at4 = leads(t4["rows_tracer"], t4["rows_neural"])
    assert t4["tolerance"] == 4 and not at2 and len(at4) == 3
    assert (
        f"at tolerance 2 trails on the other {len(other)} cubes, for reasons only partly "
        "measured (at 4 it leads on three of them, finding 94)" in txt
    )


_F95 = _REPO / "reports/octant_crop_rescore.json"


@pytest.mark.skipif(
    not (_F95.exists() and _F94.exists()), reason="finding 95 artifact absent"
)
def test_octant_numbers_match_finding_95():
    d, t4, txt = json.loads(_F95.read_text()), json.loads(_F94.read_text()), _text()
    assert (
        d["status"] == "OK"
        and not d["identity_problems"]
        and d["prediction_P1_leads_on_16_of_24"] is True
    )
    pen, med = "erl_merge_penalized", statistics.median
    octs = d["octants"]
    lead, n = d["neural_leads_at_4"]
    assert (lead, n) == (19, 24) and lead == sum(
        o["neural"]["4.0"][pen] > o["tracer"]["4.0"][pen] for o in octs.values()
    )
    ratio = med(
        o["neural"]["4.0"][pen] / o["tracer"]["4.0"][pen] for o in octs.values()
    )
    s5 = [
        c
        for c in t4["groups"]["in_sample"]
        if c.startswith("s5_") and c.endswith("_256")
    ]
    assert len(s5) == 3 and all(
        t4["rows_neural"][c][pen] < t4["rows_tracer"][c][pen] for c in s5
    )
    assert "(finding 95, pre-registered; its prediction held)" in txt
    assert (
        f"At tolerance 4 its merge-penalized ERL is a median {ratio:.2f} times our tracer's across the octants."
        in txt
    )
    assert (
        "Nor is the scroll alone the cause, since the three Scroll-5 256³ cubes trail too."
        in txt
    )


_F96 = _REPO / "reports/neural_tracer_boundary.json"


@pytest.mark.skipif(
    not (_F96.exists() and _F94.exists()), reason="finding 96 artifact absent"
)
def test_boundary_caveat_matches_finding_96():
    d, t4, txt = json.loads(_F96.read_text()), json.loads(_F94.read_text()), _text()
    rows = d["rows"]
    assert d["status"] == "OK" and d["exploratory"] is True
    assert "(finding 96, exploratory: found after the fact, not pre-registered)" in txt
    r = d["radius_ct_voxels"]
    assert f"drops any seed whose {2 * r + 1}-voxel CT window crosses the edge" in txt
    nearest = {v["min_seed_face_distance_grid"] for v in rows.values()}
    assert len(rows) == 21 and nearest == {r / d["grid_scale"]}
    assert (
        f"No traced seed lies closer than {r / d['grid_scale']:.0f} trace-grid voxels ({r} CT voxels) to a face on any "
        f"of the {len(rows)} cubes." in txt
    )

    def span(size, key):
        vals = [v[key] for v in rows.values() if v["size"] == size]
        return vals, f"{min(vals):.2f}–{max(vals):.2f}"

    (nh256, s1), (pg256, s2) = (
        span(256, "no_heading_share"),
        span(256, "neural_pred_over_gt"),
    )
    (nh512, s3), (pg512, s4) = (
        span(512, "no_heading_share"),
        span(512, "neural_pred_over_gt"),
    )
    assert (len(nh256), len(nh512)) == (10, 11)
    assert (
        f"On the ten 256³ cubes it drops {s1} of its seed dots, and its output is {s2} of the ground-truth length. "
        f"On the eleven 512³ cubes those are {s3} and {s4}." in txt
    )
    # "both separate by cube size", "our tracer's coverage does not"
    assert min(nh256) > max(nh512) and max(pg256) < min(pg512)
    _, t256 = span(256, "tracer_coverage")
    tc = {
        s: [v["tracer_coverage"] for v in rows.values() if v["size"] == s]
        for s in (256, 512)
    }
    assert not (min(tc[256]) > max(tc[512]) or max(tc[256]) < min(tc[512])), t256
    # "Ten of the 13 cubes on which it trails at tolerance 2 are 256³": the published tolerance-2 rows
    trails = [c for c, n in t4["published_neural"].items()
              if n["erl_merge_penalized"] < t4["published_tracer"][c]["erl_merge_penalized"]]  # fmt: skip
    small = [c for c in trails if c.endswith("_256")]
    assert (len(small), len(trails)) == (10, 13)
    assert (
        "Ten of the 13 cubes on which it trails at tolerance 2 are 256³. Finding 96 could not say how much of the gap "
        "this explains; finding 97 measured it." in txt
    )
    in_sample_256 = [c for c in t4["groups"]["in_sample"] if c.endswith("_256")]
    assert len(t4["groups"]["in_sample"]) == 11 and len(in_sample_256) == 8
    assert (
        "Eight of the 11 are 256³ cubes, where a large part of the deficit is how we ran it (findings 96 and 97, below)."
        in txt
    )
    assert (
        "On the ten 256³ ones, our protocol kept it from seeding near the faces (finding 96)."
        in txt
    )
    assert (
        "Finding 96 is exploratory, not pre-registered. It is in `reports/neural_tracer_boundary.md`"
        in txt
    )


_F97 = _REPO / "reports/neural_tracer_ct_context.json"


@pytest.mark.skipif(not _F97.exists(), reason="finding 97 artifact absent")
def test_ct_context_result_matches_finding_97():
    d, txt = json.loads(_F97.read_text()), _text()
    pen = "erl_merge_penalized"
    assert d["status"] == d["status_scroll1"] == "OK" and d["smoke_identical"] is True
    for v in (d, d["scroll1"]):
        assert v["prediction_P1"] and v["prediction_P2"] and v["prediction_P3"]
    assert (
        "(finding 97, pre-registered and widened to Scroll 1 before the run; all three predictions held on both scrolls)"
        in txt
    )
    s5_in = [
        "s5_03997_01497_03997_256",
        "s5_07997_02997_05497_256",
        "s5_14997_01497_01497_256",
    ]
    s1 = [c for c in d["rows_tol2"] if c.startswith("s1_")]
    held_out = [c for c in d["rows_tol2"] if c not in s5_in + s1]
    cubes = list(d["rows_tol2"])
    assert (len(s1), len(held_out), len(cubes)) == (5, 2, 10)

    def span(vals, fmt="{:.3f}"):
        return f"{fmt.format(min(vals))}–{fmt.format(max(vals))}"

    rec, f96 = d["records"], d["finding_96_records"]
    after = span([rec[c]["no_heading_share"] for c in s5_in + s1])
    before = span([f96[c]["no_heading"] / f96[c]["dots"] for c in s5_in + s1])
    assert (
        f"it drops {after} of its seed dots on the eight in-sample ones, against {before}."
        in txt
    )
    factor = [
        d["rows_tol2"][c]["coverage"] / d["finding_91_rows_tol2"][c]["coverage"]
        for c in cubes
    ]
    assert f"Its coverage rises {span(factor, '{:.2f}')}× on all ten." in txt
    leads4 = [c for c in cubes if d["rows_tol4"][c][pen] > d["our_tracer_tol4"][c][pen]]
    assert len(leads4) == 8 and sum(c in s1 for c in leads4) == 4
    assert (
        "At tolerance 4 it then leads our tracer on 8 of the 10, 4 of the 5 Scroll-1 cubes among them."
        in txt
    )
    assert (
        "Given the scan around them, it leads on 8 of the 10 at tolerance 4 (finding 97)."
        in txt
    )
    ours2 = d["our_tracer_tol2"]
    assert all(d["rows_tol2"][c][pen] > ours2[c][pen] for c in held_out)
    assert all(d["rows_tol2"][c][pen] < ours2[c][pen] for c in s5_in + s1)

    def med(rows, group):
        return statistics.median(rows[c][pen] / ours2[c][pen] for c in group)

    now = (med(d["rows_tol2"], s5_in), med(d["rows_tol2"], s1))
    was = (med(d["finding_91_rows_tol2"], s5_in), med(d["finding_91_rows_tol2"], s1))
    assert (
        f"at a median {now[0]:.2f}–{now[1]:.2f} of our tracer rather than {was[0]:.2f}–{was[1]:.2f}."
        in txt
    )
    assert (
        "Finding 97 is in `reports/neural_tracer_ct_context.md`, with its committed JSON and pre-registration"
        in txt
    )


# Each failed registered prediction in the list, with how many it counts for. The stated total is their sum.
_FAILED = {
    "finding 70 (": 1,
    "finding 71 prediction 1": 1,
    "finding 72 prediction 1": 1,
    "per-crop normalisation as the cause": 1,
    "finding 73 prediction 2": 1,
    "finding 74 predictions 2 and 3": 2,
    "finding 75 predictions 1 and 2": 2,
    "finding 76 prediction 1": 1,
    "the correction's prediction 3": 1,
    "finding 79 prediction 1": 1,
    "finding 80 prediction 2": 1,
    "finding 83 prediction 1": 1,
    "finding 84 prediction 3": 1,
    "finding 85 prediction 1": 1,
    "finding 92 predictions 2 and 3": 2,
    "finding 93 predictions 1–3": 3,
    "finding 94 prediction 2": 1,
}


@pytest.mark.skipif(not _SUP.exists(), reason="supervised re-analysis artifact absent")
def test_failed_predictions_say_where_the_labels_change_them():
    # Findings 71-76's predictions are listed as registered, on the whole surface. Where the labels
    # are defined, three of them change, and one that held (71 P2) fails; the list says so.
    d, txt = json.loads(_SUP.read_text()), _text()
    rows = [r for r in d["f71"]["rows"] if r["status"] == "compared"]
    # 71 P1: |ΔAP| < 0.02 in at least 6 of the 8
    assert len(rows) == 8 and sum(abs(r["d_ap"]) < 0.02 for r in rows) >= 6
    # 71 P2, held on the whole surface: ΔAP > 0 in at most 5 of the 8
    pos = sum(r["d_ap"] > 0 for r in rows)
    assert pos > 5
    assert (
        "Re-analysed with inkagree's gate where the labels are defined, all 8 pass and it holds, "
        "while prediction 2, held on the whole surface, fails there: smooth's ΔAP > 0 in "
        f"{pos} of 8, not at most 5);" in txt
    )
    # 74 P3: step 1.0 vs 0.5, no consistent difference by the k = 6 rule
    t = d["f74"]["1.0"]["tally"]
    assert t["resolved_b"] < 6 and t["resolved_a"] < 6
    assert (
        f"where the labels are defined, prediction 3 holds: {t['resolved_a']} of 8)"
        in txt
    )
    # 76 P1: no window qualifies, so no correlation
    assert d["f76"]["n_windows"] == 0
    assert (
        "where the labels are defined it is undetermined, since no window qualifies)"
        in txt
    )


def test_the_failed_prediction_count_is_the_listed_tally():
    raw = _DRAFT.read_text()
    head = (
        "* **Twenty-two of my registered predictions failed**, and the reports say so:"
    )
    section = raw[
        raw.index(head) + len(head) : raw.index(
            "* **The effect's size depends on grid cell size**"
        )
    ]
    items = [" ".join(b.split()) for b in section.split("\n  * ")[1:]]
    assert len(items) == len(_FAILED), items
    for key in _FAILED:
        assert sum(it.startswith(key) for it in items) == 1, key
    assert sum(_FAILED.values()) == 22


_F98 = _REPO / "reports/neural_tracer_ct_context_512.json"


@pytest.mark.skipif(not _F98.exists(), reason="finding 98 artifact absent")
def test_ct_context_512_result_matches_finding_98():
    d, txt = json.loads(_F98.read_text()), _text()
    d97 = json.loads(_F97.read_text())
    pen = "erl_merge_penalized"
    assert (
        d["status_scroll5"] == d["status_scroll3"] == "OK"
        and d["smoke_identical"] is True
    )
    for v in (d["scroll5"], d["scroll3"]):
        assert v["prediction_P1"] and v["prediction_P2"] and v["prediction_P3"]
    assert d["scroll3"]["prediction_P4"] is True
    assert (
        "(finding 98, pre-registered; all four predictions held on both scrolls)" in txt
    )
    s5 = [c for c in d["rows_tol2"] if c.startswith("s5_")]
    s3 = [c for c in d["rows_tol2"] if c.startswith("s3_")]
    assert (len(s5), len(s3)) == (3, 8)

    def span(vals, fmt="{:.3f}"):
        return f"{fmt.format(min(vals))}–{fmt.format(max(vals))}"

    rec, f96 = d["records"], d["finding_96_records"]
    after = {
        g: span([rec[c]["no_heading_share"] for c in g]) for g in (tuple(s5), tuple(s3))
    }
    before = {
        g: span([f96[c]["no_heading"] / f96[c]["dots"] for c in g])
        for g in (tuple(s5), tuple(s3))
    }
    assert (
        f"it drops {after[tuple(s5)]} of its seed dots on the three in-sample Scroll-5 ones, against "
        f"{before[tuple(s5)]}, and {after[tuple(s3)]} on the eight held-out Scroll-3 ones, against {before[tuple(s3)]}."
        in txt
    )
    factor = [
        d["rows_tol2"][c]["coverage"] / d["finding_91_rows_tol2"][c]["coverage"]
        for c in s5 + s3
    ]
    small = [
        d97["rows_tol2"][c]["coverage"] / d97["finding_91_rows_tol2"][c]["coverage"]
        for c in d97["rows_tol2"]
    ]
    assert max(factor) < min(small)
    assert (
        f"Its coverage rises {span(factor, '{:.2f}')}× on all eleven, less than on the 256³ cubes"
        in txt
    )
    ours2, ours4 = d["our_tracer_tol2"], d["our_tracer_tol4"]
    assert all(d["rows_tol4"][c][pen] > ours4[c][pen] for c in s5 + s3)
    assert all(d["rows_tol2"][c][pen] > ours2[c][pen] for c in s3)
    assert all(d["rows_tol2"][c][pen] < ours2[c][pen] for c in s5)
    now = statistics.median(d["rows_tol2"][c][pen] / ours2[c][pen] for c in s5)
    was = statistics.median(
        d["finding_91_rows_tol2"][c][pen] / ours2[c][pen] for c in s5
    )
    assert f"at a median {now:.2f} of our tracer rather than {was:.2f}." in txt

    def leads(rows, ours, cubes):
        return sum(rows[c][pen] > ours[c][pen] for c in cubes)

    small_cubes = list(d97["rows_tol2"])
    n4 = leads(d["rows_tol4"], ours4, s5 + s3) + leads(
        d97["rows_tol4"], d97["our_tracer_tol4"], small_cubes
    )
    w4 = leads(d["finding_94_rows_tol4"], ours4, s5 + s3) + leads(
        d97["finding_94_rows_tol4"], d97["our_tracer_tol4"], small_cubes
    )
    n2 = leads(d["rows_tol2"], ours2, s5 + s3) + leads(
        d97["rows_tol2"], d97["our_tracer_tol2"], small_cubes
    )
    w2 = leads(d["finding_91_rows_tol2"], ours2, s5 + s3) + leads(
        d97["finding_91_rows_tol2"], d97["our_tracer_tol2"], small_cubes
    )
    assert (n4, w4, n2, w2) == (19, 11, 10, 8)
    assert (
        f"it leads our tracer on {n4} at tolerance 4 ({w4} with the cube alone) and on {n2} at tolerance 2 ({w2})."
        in txt
    )
    in_sample = s5 + [
        c
        for c in small_cubes
        if c.startswith("s1_")
        or c
        in (
            "s5_03997_01497_03997_256",
            "s5_07997_02997_05497_256",
            "s5_14997_01497_01497_256",
        )
    ]
    rows = {**d97["rows_tol2"], **d["rows_tol2"]}
    ours = {**d97["our_tracer_tol2"], **ours2}
    assert len(in_sample) == 11 and all(rows[c][pen] < ours[c][pen] for c in in_sample)
    assert (
        "In sample it still trails at tolerance 2 on all 11 cubes given the scan (findings 97 and 98)."
        in txt
    )
    assert (
        "Finding 98 is in `reports/neural_tracer_ct_context_512.md`, with its committed JSON and pre-registration."
        in txt
    )
    assert "findings 95–97 on 2026-10-23, and finding 98 on 2026-10-24" in txt


def test_scrollgt_0_9_0_is_described_as_released():
    """0.8.3 and 0.9.0 were merged on 2026-10-24 and tagged together as v0.9.0; the draft cites that tag."""
    txt = _text()
    assert "were merged on 2026-10-24 and tagged together as v0.9.0" in txt
    assert (
        "https://github.com/jonmarrs/scrollgt/tree/v0.9.0" in txt
        and "scrollgt/tree/v0.8.2" not in txt
    )
    assert (
        "The URL field cites `tree/v0.9.0`" in txt
    )  # the checklist names the cite it set
    assert "first on merge-penalized ERL on 10 of the 21, against 8" in txt
