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


def test_faithfulness_claim_matches_finding_72():
    d = json.loads(_F72.read_text())
    s = d["summary"]
    assert len(d["segments"]) == 8 and s["n_included"] == 8
    assert max(abs(v) for v in s["prob_d_ap"].values()) < 0.001
    assert s["prob_resolved_pos"] == 0 and s["prob_resolved_neg"] == 0
    assert "(|ΔAP| < 0.001 in all 8, none resolved)" in _text()


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
    assert "Eighteen of my registered predictions failed" in txt


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
    p = d["predictions"]
    assert (
        p["P2_s3_leads_tracer_on_6_of_8"] is False
        and p["P3_median_pen_ratio_within_0.85_1.15"] is False
    )
    assert (
        f"on at least 6 of 8 cubes: it kept it on {lead}; its median merge-penalized ERL would stay within "
        f"0.85–1.15 of the native rows: {ratio:.2f})" in txt
    )
