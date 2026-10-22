"""Bind finding 77's re-analysis (reports/supervised_reanalysis.md) to the JSON it is drawn from.

The re-analysis (docs/preregistration/2026-10-04_supervised_reanalysis.md) decides, for each of findings
71-76, whether its registered verdict survives on villa's supervised region. Here each tally is recomputed
from its per-segment rows, each verdict from the finding's own registered rule, and each figure the report,
the spiral summary, the corrected reports and the villa #1818 draft quote from it is checked against them.
The October filing draft's figures are bound in test_filing_2026_10_numbers.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_JSON = _REPO / "reports/supervised_reanalysis.json"

pytestmark = pytest.mark.skipif(
    not _JSON.exists(), reason="supervised re-analysis artifact absent"
)


def _flat(rel: str) -> str:
    # documents wrap lines, and a quoted draft marks each line; compare on single-spaced text
    lines = (_REPO / rel).read_text().splitlines()
    return " ".join(" ".join(ln.removeprefix(">") for ln in lines).split())


def _pct(x: float, nd: int = 1) -> str:
    return f"{x:+.{nd}f}%".replace("-", "−")


def _median(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    return (xs[n // 2] + xs[(n - 1) // 2]) / 2


def _compared(c: dict) -> list[dict]:
    return [r for r in c["rows"] if r["status"] == "compared"]


def _rel(c: dict) -> tuple[float, float, float]:
    """Per-segment ΔAP relative to arm A, in percent: median, min, max."""
    v = [100 * r["d_ap"] / r["ap_a"] for r in _compared(c)]
    return _median(v), min(v), max(v)


def _resolved(c: dict) -> list[dict]:
    return [r for r in _compared(c) if r["d_ap_ci"][0] > 0 or r["d_ap_ci"][1] < 0]


@pytest.fixture(scope="module")
def d() -> dict:
    return json.loads(_JSON.read_text())


def _comparisons(d: dict):
    yield "f71", d["f71"]
    for f in ("f72", "f73"):
        for k in ("prob", "strip"):
            yield f"{f}.{k}", d[f][k]
    for f, xs in (("f74", ("0.25", "1.0", "2.0")), ("f75", ("0.5", "2.0"))):
        for x in xs:
            yield f"{f}.{x}", d[f][x]


def test_each_tally_is_its_rows(d):
    for name, c in _comparisons(d):
        rows, t = _compared(c), c["tally"]
        assert len(c["rows"]) == 8 and t["n_compared"] == len(rows) == 8, name
        assert t["resolved_b"] == sum(r["d_ap_ci"][0] > 0 for r in rows), name
        assert t["resolved_a"] == sum(r["d_ap_ci"][1] < 0 for r in rows), name
        assert t["b_ge_a"] == sum(r["d_ap"] >= 0 for r in rows), name
        assert t["abs_lt_0_01"] == sum(abs(r["d_ap"]) < 0.01 for r in rows), name
        assert t["median_d_ap"] == pytest.approx(_median([r["d_ap"] for r in rows]))
        for r in rows:
            assert r["domain"] == "mesh-valid AND supervised", name
            assert r["d_ap"] == pytest.approx(r["ap_b"] - r["ap_a"]), name


def test_each_verdict_is_its_findings_registered_rule(d):
    # 71: a direction is claimed only if resolved in >= 6 of 8; otherwise no consistent difference.
    t = d["f71"]["tally"]
    assert t["survives"] is (t["resolved_b"] < 6 and t["resolved_a"] < 6) is True
    # 72 P2: the scorer probability's |ΔAP| < 0.01 in at least 6 gated segments.
    assert d["f72"]["survives_p2"] is (d["f72"]["prob"]["tally"]["abs_lt_0_01"] >= 6)
    assert d["f72"]["survives_p2"] is True
    # 73 P2: smooth's scorer AP >= linear's in at least 6. It failed; it survives by failing again.
    assert d["f73"]["survives_p2"] is (d["f73"]["prob"]["tally"]["b_ge_a"] < 6) is True
    # 74: 0.5 (arm A) resolved better than each other step in >= 6 of 8 (inkagree summarize --k 6).
    f74 = [d["f74"][x]["tally"] for x in ("0.25", "1.0", "2.0")]
    assert d["f74"]["survives"] is all(t["resolved_a"] >= 6 for t in f74) is False
    # 75: 1.0 (arm A) resolved better than 0.5, and 2.0 better than 1.0, each in >= 6 of 8.
    survives = (
        d["f75"]["0.5"]["tally"]["resolved_a"] >= 6
        and d["f75"]["2.0"]["tally"]["resolved_b"] >= 6
    )
    assert d["f75"]["survives"] is survives is True
    # 76 Q2: the AP ratio rises with the dilation, and is higher at r = 8 than at r = 0.
    q2 = d["f76"]["q2"]
    assert [q["dilation_px"] for q in q2] == [0, 1, 2, 4, 8]
    for q in q2:
        assert q["ratio"] == pytest.approx(q["ap_scorer"] / q["ap_strip"])
    r = [q["ratio"] for q in q2]
    rises = all(b >= a for a, b in zip(r, r[1:], strict=False)) and r[-1] > r[0]
    assert d["f76"]["q2_ratio_rises"] is rises is True
    # 76 Q1: no window qualifies, so no correlation was computed.
    assert (
        d["f76"]["n_windows"] == 0
        and d["f76"]["windows"] == []
        and not d["f76"]["q1_rho"]
    )


def test_the_report_table_is_the_json(d):
    rep = _flat("reports/supervised_reanalysis.md")
    t = d["f71"]["tally"]
    assert abs(t["median_d_ap"]) < 0.001 and t["abs_lt_0_01"] == 8
    assert (
        f"{t['resolved_a'] + t['resolved_b']} of 8 resolved; \\|ΔAP\\| < 0.01 in all 8; "
        "median ΔAP ≈ 0" in rep
    )
    assert f"median AP {t['median_ap_a']:.2f} on supervised pixels" in rep
    t = d["f72"]["prob"]["tally"]
    assert f"| \\|ΔAP\\| < 0.01 in {t['abs_lt_0_01']} of 8 | **survives** |" in rep
    assert f"smooth ≥ linear in {d['f73']['prob']['tally']['b_ge_a']} of 8" in rep
    c = d["f73"]["strip"]
    assert (
        f"resolved in **{c['tally']['resolved_b']} of 8** (was 6), median "
        f"**{_pct(_rel(c)[0], 2)}** of AP" in rep
    )
    t25, t20 = d["f74"]["0.25"], d["f74"]["2.0"]
    assert (
        f"beats 0.25 ({t25['tally']['resolved_a']} of 8, {_pct(_rel(t25)[0])}) and 2.0 "
        f"({t20['tally']['resolved_a']} of 8, {_pct(_rel(t20)[0])})" in rep
    )
    c = d["f74"]["1.0"]
    med, lo, hi = _rel(c)
    assert (
        f"**vs 1.0: {c['tally']['resolved_a']} of 8 resolved, median {_pct(med)} "
        f"(range {_pct(lo)} … {_pct(hi)})**" in rep
    )
    c5, c2 = d["f75"]["0.5"], d["f75"]["2.0"]
    assert (
        f"1.0 beats 0.5 ({c5['tally']['resolved_a']} of 8, **{_pct(_rel(c5)[0])}**; was −8.3%); "
        f"2.0 beats 1.0 ({c2['tally']['resolved_b']} of 8, **{_pct(_rel(c2)[0])}**; was +10.3%)"
        in rep
    )
    q2 = d["f76"]["q2"]
    assert f"ratio rises {q2[0]['ratio']:.2f} → {q2[-1]['ratio']:.2f}" in rep


def test_the_window_rule_and_its_coverage_are_stated_as_applied(d):
    rep = _flat("reports/supervised_reanalysis.md")
    assert "≥ 25% of a 2048-px window's mesh-valid domain supervised" in rep
    # finding 76 reads finding 72's canvas: its prob rows give each segment's supervised share
    share = [r["domain_px"] / r["mesh_domain_px"] for r in _compared(d["f72"]["prob"])]
    lo, hi = round(100 * min(share)), round(100 * max(share))
    assert f"supervision covers {lo}–{hi}% of each segment's mesh-valid domain" in rep


def test_the_summary_marks_each_re_analysed_finding(d):
    s = _flat("reports/SPIRAL_FINDINGS_SUMMARY.md")
    c = d["f71"]
    pos = sum(r["d_ap"] > 0 for r in _compared(c))
    assert c["tally"]["resolved_b"] == 1 and c["tally"]["resolved_a"] == 0
    assert (
        "**71. [RE-ANALYSED by 77: survives on the supervised region, but its sign does not: "
        f"there smooth's ΔAP is > 0 in {pos} of 8, resolved in 1.]" in s
    )
    c = d["f72"]["prob"]
    lt = sum(abs(r["d_ap"]) < 0.001 for r in _compared(c))
    assert (
        f"**72. [RE-ANALYSED by 77: survives; on the supervised region |ΔAP| < 0.01 in all "
        f"{c['tally']['abs_lt_0_01']}, < 0.001 in {lt}, resolved in {len(_resolved(c))}.]"
        in s
    )
    c = d["f73"]["strip"]
    assert (
        "**73. [RE-ANALYSED by 77: survives; on the supervised region the raw render's secondary "
        f"gain is resolved in {c['tally']['resolved_b']} of 8, about {_pct(_rel(c)[0])} of AP.]"
        in s
    )
    assert (
        f"**75. [RE-ANALYSED by 77: survives, smaller: {_pct(_rel(d['f75']['0.5'])[0])} and "
        f"{_pct(_rel(d['f75']['2.0'])[0])} on the supervised region.]" in s
    )
    q2 = d["f76"]["q2"]
    assert (
        f"**76. [RE-ANALYSED by 77: Q2 survives, {q2[0]['ratio']:.2f} → {q2[-1]['ratio']:.2f} on "
        "the supervised region; Q1 is undetermined, since no window qualifies.]" in s
    )
    assert "**74. [CORRECTED by 77: does not survive as stated;" in s


def test_the_corrected_reports_note_what_changed(d):
    c = d["f71"]
    pos = sum(r["d_ap"] > 0 for r in _compared(c))
    assert (
        f"there smooth's ΔAP is > 0 in {pos} of 8 and resolved in {len(_resolved(c))}"
        in _flat("reports/surface_interpolation_vs_labels.md")
    )
    c = d["f72"]["prob"]
    lt = sum(abs(r["d_ap"]) < 0.001 for r in _compared(c))
    (r,) = _resolved(c)
    assert r["d_ap_ci"][1] < 0  # arm A, linear
    assert (
        f"there it is < 0.001 in {lt} of 8, and 1 is resolved ({r['segment']}, "
        f"ΔAP {r['d_ap']:+.4f}, toward linear)".replace("-", "−")
        in _flat("reports/scorer_vs_labels_surface_interpolation.md")
    )


def test_the_villa_1818_draft_quotes_the_supervised_numbers(d):
    txt = _flat("docs/VILLA_DRAFT_1818_smooth_measurements.md")
    assert (
        "scored inside each segment's `supervision.zarr`, where the labels are defined"
        in txt
    )
    assert max(abs(r["d_ap"]) for r in _compared(d["f71"])) < 0.0002
    assert "unchanged by smooth (|ΔAP| < 0.0002)" in txt
    c = d["f73"]["strip"]
    assert (
        f"ΔAP > 0 resolved in {c['tally']['resolved_b']} of 8 segments, about "
        f"{_rel(c)[0]:+.1f}% relative" in txt
    )
    assert not _resolved(d["f72"]["prob"])[1:] and not _resolved(d["f73"]["prob"])[1:]
    assert "does not consistently change in either case" in txt
    # The count figures do not involve the labels: findings 72 and 73's own artifacts.
    fine = json.loads((_REPO / "reports/scorer_vs_labels.json").read_text())
    coarse = json.loads((_REPO / "reports/scorer_vs_labels_coarse.json").read_text())
    f = [r["d_total"] for r in fine["segments"]]
    c = [r["d_total"] for r in coarse["segments"]]
    lo, hi = coarse["summary"]["window_d_range"]
    assert (
        f"change is {_pct(100 * min(f))} to {_pct(100 * max(f))} per segment on 20-voxel meshes, "
        f"and {_pct(100 * min(c))} to {_pct(100 * max(c))} per segment "
        f"({_pct(100 * lo, 0)} to {_pct(100 * hi, 0)} per 2048-px window)" in txt
    )
