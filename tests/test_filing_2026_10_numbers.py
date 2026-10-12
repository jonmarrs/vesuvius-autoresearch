"""Every number in the October 2026 filing draft must match the artifact it comes from.

Same discipline as test_filing_numbers_match_sources.py for September: a figure in the filing text is a
claim, and the claim is only as good as the file it was read from. Each test recomputes the figure from the
committed JSON and asserts the draft states it.
"""

import json
from pathlib import Path

import pytest

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

    pp = _REPO.parent / name / "pyproject.toml"
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
    assert "Fourteen of my registered predictions failed" in txt


def test_scrollgt_cite_is_its_newest_tag():
    """The URL field cited v0.4.1 after v0.5.0 was tagged; tie it to the sibling checkout's newest tag."""
    import subprocess

    sg = _REPO.parent / "scrollgt"
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

    sg = _REPO.parent / "scrollgt"
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
