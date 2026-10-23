"""The findings summary's headline numbers must match the artifacts they come from.

`reports/SPIRAL_FINDINGS_SUMMARY.md` is the third document read as current, beside the README and
FINDINGS. On 2026-10-23, changing one of its 1,211 numbers by one in its last digit was caught by a
test for 83 of them, and most of those were finding numbers or figures bound for the README. The
figures in the findings' own titles, the ones a reader quotes, were bound for none of 49–70.

Each test here recomputes a figure from the committed JSON, or from the report table where no JSON
holds it, and asserts the summary states it, rounded once from the raw value.
"""

import json
import re
import statistics
from pathlib import Path

from scipy import stats

_REPO = Path(__file__).resolve().parent.parent
_REPORTS = _REPO / "reports"
_SUMMARY = _REPORTS / "SPIRAL_FINDINGS_SUMMARY.md"


def _flat(path: Path) -> str:
    # compare on unquoted, single-spaced text so rewrapping is harmless
    lines = (re.sub(r"^> ?", "", line) for line in path.read_text().splitlines())
    return " ".join(" ".join(lines).split())


def _json(rel: str):
    return json.loads((_REPORTS / rel).read_text())


def _pct(x: float, dp: int = 2) -> str:
    return f"{x * 100:+.{dp}f}%".replace("-", "−")


def _cv(xs) -> float:
    return statistics.stdev(xs) / statistics.mean(xs)


def _cv_ci(cv: float, df: int) -> tuple[float, float]:
    # the chi-square interval on a standard deviation, as the reports compute it
    return (
        cv * (df / stats.chi2.ppf(0.975, df)) ** 0.5,
        cv * (df / stats.chi2.ppf(0.025, df)) ** 0.5,
    )


def test_holding_the_flatten_fixed_finding_49():
    d = _json("flat_displacement_floor.json")
    floor = abs(d["zero"] / d["rad0"] - 1)
    assert abs(d["F"] - floor) < 1e-12
    pixels = abs(d["zero"] - d["rad0"])
    # the stock render spread it collapses from, finding 48
    ratio = 0.0304 / floor
    text = _flat(_SUMMARY)
    assert (
        f"**49. Holding the flatten fixed collapses the floor {round(ratio, -3):.0f}×, "
        f"to {pixels} pixels.**"
    ) in text
    assert f"differ by **{floor * 100:.4f}%**" in text
    assert f"all {pixels} px is the scorer" in text


def test_displacing_the_surface_finding_50():
    d = _json("flat_displacement_verdict.json")
    gap = _json("gap_fix_mechanism.json")
    text = _flat(_SUMMARY)
    assert (
        f"costs ink in both directions: {_pct(d['in'])} inward, {_pct(d['out'])} outward.**"
    ) in text
    assert d["in"] < 0 and d["out"] < 0
    # IN against the gap fix's own ink loss from the same shift
    ratio = d["in"] / gap["ink  total_fg_pixels"]["rel"]
    assert f"IN loses **{ratio:.2f}×** what the gap fix lost" in text


def test_the_deterministic_flatten_floor_finding_53():
    d = _json("pooled_fit_only_floor.json")
    det, stock = d["det"]["curbase"], d["stock"]["curbase"]
    cv_det, cv_stock = _cv(det), _cv(stock)
    lo, hi = _cv_ci(cv_det, len(det) - 1)
    f = cv_det**2 / cv_stock**2
    p = 2 * min(stats.f.sf(f, 5, 5), stats.f.cdf(f, 5, 5))
    top = max(det) / sorted(det)[-2] - 1
    text = _flat(_SUMMARY)
    assert f"fit RNG dominates: seed CV {cv_det:.2f} [{lo:.2f}, {hi:.2f}].**" in text
    assert (
        f"give a within-group CV of {cv_det:.4f} against {cv_stock:.4f} on the same fits "
        f"with stock flattens — indistinguishable, F(5,5) p={p:.3f}"
    ) in text
    assert f"as top scorer by {_pct(top, 1)}" in text


def test_the_pooled_fit_only_floor_finding_57():
    d = _json("pooled_fit_only_floor.json")
    lo, hi = d["ci"]
    text = _flat(_SUMMARY)
    assert (
        f"**57. The current tier's fit-only floor, pooled: {d['pooled_cv']:.4f} "
        f"[{lo:.3f}, {hi:.3f}], df = {d['df']}.**"
    ) in text
    assert d["band"] == "BETWEEN" and "BETWEEN, as registered" in text
    # the MDE scales with the CV, so the interval's top gives the upper resolution
    top = d["mde_3v3"] * hi / d["pooled_cv"]
    assert (
        f"**3v3 resolves ~{d['mde_3v3'] * 100:.0f}%** at the point estimate "
        f"(~{round(top * 100, -1):.0f}% at the interval's top)"
    ) in text


def test_the_slice_step_range_finding_66():
    d = _json("step2_across_surfaces.json")
    assert d["all_positive"] and d["min"] == min(d["per_surface"].values())
    assert (
        f"raises `total_fg_pixels` by {_pct(d['min'], 1)} to {_pct(d['max'], 1)}, "
        "surface-dependent.**"
    ) in _flat(_SUMMARY)


def test_the_same_winding_extension_finding_68():
    d = _json("samewinding_extension_verdict.json")["primary 6v6 render-matched"]
    text = _flat(_SUMMARY)
    assert (
        f"gives **{_pct(d['rel'])} [{_pct(d['lo'])}, {_pct(d['hi'])}]**, so the constraints "
        f"buy at most {-d['lo'] * 100:.1f}% of reading and removing them gains at most "
        f"{d['hi'] * 100:.1f}%"
    ) in text
    # the title's "about ±9%" is the interval's half-width
    assert f"bounded at about ±{(d['hi'] - d['lo']) / 2 * 100:.0f}% on reading" in text


def test_the_surface_interpolation_windows_finding_70():
    d = _json("interp_windows.json")
    w = d["windows"]
    fg = [x["d_fg"] for x in w]
    pooled = sum(x["smooth"]["fg"] for x in w) / sum(x["linear"]["fg"] for x in w) - 1
    text = _flat(_SUMMARY)
    assert (
        f"on {len(w)} full-height windows of one flat chosen on coverage alone: per-window "
        f"Δ`total_fg_pixels` from {_pct(min(fg), 1)} to {_pct(max(fg), 1)} (median |Δ| "
        f"{statistics.median(abs(x) for x in fg) * 100:.1f}%), **pooled {_pct(pooled)}**"
    ) in text
    assert f"up to ±{round(max(abs(x) for x in fg) * 100, -1):.0f}%" in text
    falls = sum(x["d_line"] < 0 for x in w)
    assert f"line score falls in {falls} of {len(w)} windows" in text
    assert not d["predictions_held"]["fg_abs_below_1pct_every_window"]
    assert "My prediction (|Δ| < 1% every window) FAILED." in text


def test_the_same_fit_relayout_finding_55():
    d = _json("layout_rescoring/same_fit_relayout_replication.json")
    lo, hi = d["band"]
    assert d["in_band"] and lo <= d["sd_ln_ratio"] <= hi
    table = (_REPORTS / "the_flatten_noise_is_local_rescoring.md").read_text()
    sd = re.search(
        r"\| ink-weighted sd of the per-block change \| \*\*([\d.]+)\*\* \|", table
    )
    lose = re.search(r"\| blocks that LOSE ink \| \*\*(\d+ of \d+)\*\* \|", table)
    text = _flat(_SUMMARY)
    assert (
        f"Per 2 kpx block it is **{sd.group(1)}** (sd), {lose.group(1)} blocks lose ink"
    ) in text
    assert (
        f"six more same-fit pairs (sd ln ratio **{d['sd_ln_ratio']:.4f}**, inside the band "
        "written in advance)"
    ) in text
    assert len(d["ln_ratio"]) == 6
    assert (
        f"Layout noise is **~{d['layout_share_of_fit_variance'] * 100:.0f}%** of fit-to-fit "
        "variance"
    ) in text
