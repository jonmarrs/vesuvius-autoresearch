"""Bind finding 83's report (reports/fiber_heldout_split.md) to the JSON files it is drawn from."""

from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import pytest

REPORTS = Path(__file__).resolve().parents[1] / "reports"
CC = "floor_connected_components"


@pytest.fixture(scope="module")
def data() -> tuple[str, dict, dict, dict]:
    names = (
        "fiber_heldout_split",
        "fiber_heldout_in_sample_rows",
        "fiber_heldout_mask_vs_label",
    )
    paths = [REPORTS / f"{n}.json" for n in names]
    if not all(p.exists() for p in paths):
        pytest.skip("finding 83 JSON not present")
    report = (REPORTS / "fiber_heldout_split.md").read_text()
    return (report, *(json.loads(p.read_text()) for p in paths))  # fmt: skip


def _rng(vals, fmt: str) -> str:
    return (
        f"{min(vals):{fmt}}–{max(vals):{fmt}}"
        if len(vals) > 2
        else ", ".join(f"{v:{fmt}}" for v in sorted(vals))
    )


def _groups(h: dict, i: dict) -> list[tuple[dict, list[str]]]:
    return [(i, [c for c in i if c.endswith("_512")]), (h, [c for c in h if c.startswith("s3")]),
            (i, [c for c in i if c.endswith("_256")]), (h, [c for c in h if c.startswith("s5")])]  # fmt: skip


def test_per_cube_tables(data):
    report, r, _, _ = data
    for c, v in r["cubes"].items():
        o, k, t = v["rows"]["oracle"], v["rows"][CC], v["rows"]["tracer"]
        stem = c.rsplit("_", 1)[0]
        row = (f"| {stem} | {v['n_fibers_scored']} | {v['mask_density']:.4f} | {v['mask_enrichment']:.2f} | "
               f"{o['erl']:.2f} | {k['coverage']:.4f} | {k['precision']:.4f} | {k['erl']:.2f} | "
               f"{k['erl_merge_penalized']:.2f} | {k['merges']} |")  # fmt: skip
        assert row in report, row
        row = (f"| {stem} | {t['erl']:.2f} | {t['erl_merge_penalized']:.2f} | {t['coverage']:.4f} | "
               f"{t['precision']:.4f} | {t['merges']} |")  # fmt: skip
        assert row in report, row


def test_comparison_table(data):
    report, r, ins, d = data
    h, i = r["cubes"], ins["cubes"]
    for (
        c,
        v,
    ) in (
        i.items()
    ):  # the in-sample snapshot is the current annotations, by construction
        assert v["rows"][CC]["coverage"] == r["in_sample_cc_coverage"].get(
            str(v["size_class"]), {}
        ).get(c, v["rows"][CC]["coverage"])
    qs = [
        ("cc coverage", lambda v: v["rows"][CC]["coverage"], ".4f"),
        ("tracer coverage", lambda v: v["rows"]["tracer"]["coverage"], ".4f"),
        ("mask enrichment", lambda v: v["mask_enrichment"], ".2f"),
        ("mask density", lambda v: v["mask_density"], ".4f"),
        ("cc precision", lambda v: v["rows"][CC]["precision"], ".4f"),
        ("oracle ERL", lambda v: v["rows"]["oracle"]["erl"], ".2f"),
        ("cc ERL ÷ tracer ERL", lambda v: v["rows"][CC]["erl"] / v["rows"]["tracer"]["erl"], ".2f"),
        ("tracer ERLpen ÷ cc ERLpen",
         lambda v: v["rows"]["tracer"]["erl_merge_penalized"] / v["rows"][CC]["erl_merge_penalized"], ".2f"),
    ]  # fmt: skip
    for name, f, fmt in qs:
        cells = [_rng([f(src[c]) for c in cs], fmt) for src, cs in _groups(h, i)]
        row = f"| {name} | " + " | ".join(cells) + " |"
        assert row in report, row
    cells = [_rng([d[c]["recall"] for c in cs], ".4f") for _, cs in _groups(h, i)]
    row = (
        "| mask voxel recall of villa's label (post hoc) | " + " | ".join(cells) + " |"
    )
    assert row in report, row


def test_diagnostic_table(data):
    report, _, _, d = data
    assert len(d) == 21
    for c, v in d.items():
        src = {"scrollgt_build_copy": "ScrollGT build copy"}.get(
            v["label_source"], v["label_source"]
        )
        row = (f"| {c.rsplit('_', 1)[0]} | {v['split'].replace('_', ' ')} | {src} | {v['label_density']:.4f} | "
               f"{v['recall']:.4f} | {v['precision']:.4f} |")  # fmt: skip
        assert row in report, row


def test_verdict_lines(data):
    report, r, _, _ = data
    p = r["predictions"]
    assert r["status"] == "OK" and r["excluded"] == [] and len(r["eligible"]) == 10
    assert p == {"P1_s3_median_cc_coverage_below_0.8130": False, "P2_both_s5_cc_coverage_below_0.8666": True,
                 "P3_cc_raw_erl_above_tracer_on_every_eligible_cube": True,
                 "P4_tracer_pen_above_cc_on_75pct_of_s3": True}  # fmt: skip
    for line in (
        "**P1 FAILED.**",
        "**P2 HELD.**",
        "**P3 HELD, 10 of 10.**",
        "**P4 HELD, 8 of 8.**",
    ):
        assert line in report
    assert all(v["semantic_landing"] == 1.0 for v in r["cubes"].values())
    enr = [v["mask_enrichment"] for v in r["cubes"].values()]
    assert f"at {min(enr):.2f}–{max(enr):.2f}× its" in report


def test_derived_figures(data):
    report, r, ins, d = data
    h, i = r["cubes"], ins["cubes"]
    s3 = [c for c in h if c.startswith("s3")]
    s5h = [c for c in h if c.startswith("s5")]
    i512 = [c for c in i if c.endswith("_512")]
    i256 = [c for c in i if c.endswith("_256")]
    i5 = [c for c in i256 if c.startswith("s5")]

    def med(src, cs, f):
        return st.median(f(src[c]) for c in cs)

    def cov(v):
        return v["rows"][CC]["coverage"]

    def tcov(v):
        return v["rows"]["tracer"]["coverage"]

    def pen(v, k):
        return v["rows"][k]["erl_merge_penalized"]

    assert f"Scroll-3 cubes is {med(h, s3, cov):.3f}, not below 0.8130" in report
    assert f"in-sample 512³ median is {med(i, i512, cov):.3f}" in report
    assert r["descriptive"]["s3_cc_coverage_median"] == med(h, s3, cov)
    assert (
        f"(median {med(h, s3, cov):.3f}) matches" in report
        and f"(median\n{med(i, i512, cov):.3f})" in report
    )
    assert (
        f"median coverage is {med(h, s3, tcov):.3f}, against {med(i, i512, tcov):.3f}"
        in report
    )
    rec = {c: v["recall"] for c, v in d.items()}
    assert (f"median voxel recall {st.median(rec[c] for c in s3):.3f}, against "
            f"{st.median(rec[c] for c in i512):.3f}") in report  # fmt: skip
    s5_rec = ", ".join(f"{rec[c]:.4f}" for c in s5h).replace(", ", " and ")
    assert f"{s5_rec}, against {_rng([rec[c] for c in i5], '.4f')}" in report
    in_rec = [rec[c] for c in i]
    assert f"only {100 * min(in_rec):.0f}–{100 * max(in_rec):.0f}% of villa's" in report
    ratio = [h[c]["rows"][CC]["erl"] / h[c]["rows"]["tracer"]["erl"] for c in s3]
    ratio5 = [h[c]["rows"][CC]["erl"] / h[c]["rows"]["tracer"]["erl"] for c in s5h]
    assert (
        f"by {_rng(ratio, '.2f')}× on Scroll 3 and {min(ratio5):.2f}–{max(ratio5):.2f}× on"
        in report
    )
    lead = [pen(h[c], "tracer") / pen(h[c], CC) for c in s3]
    assert all(x > 1 for x in lead) and f"by\n  {_rng(lead, '.2f')}×." in report
    lead5 = sorted(pen(h[c], "tracer") / pen(h[c], CC) for c in s5h)
    assert f"by {lead5[0]:.2f}× and {lead5[1]:.2f}×" in report
    in256_lead = sum(pen(i[c], "tracer") > pen(i[c], CC) for c in i256)
    assert in256_lead == 1 and "leads on only 1 of 8" in report
    enr5 = sorted(h[c]["mask_enrichment"] for c in s5h)
    lo_enr = min(i[c]["mask_enrichment"] for c in i256)
    assert f"falls to {enr5[0]:.2f} and {enr5[1]:.2f}, about half the lowest" in report
    assert f"value ({lo_enr:.2f})" in report and 0.45 < enr5[1] / lo_enr < 0.56
    tpen5 = sorted(pen(h[c], "tracer") for c in s5h)
    tpen_in = [pen(i[c], "tracer") for c in i256]
    ccpen5 = sorted(pen(h[c], CC) for c in s5h)
    ccpen_in = [pen(i[c], CC) for c in i256]
    assert (
        f"({tpen5[0]:.2f}\n  and {tpen5[1]:.2f}, against {_rng(tpen_in, '.2f')} in sample)"
        in report
    )
    assert (
        f"further, to {ccpen5[0]:.2f} and {ccpen5[1]:.2f} ({_rng(ccpen_in, '.2f')} in"
        in report
    )
    assert (
        max(ccpen5) < min(ccpen_in) / 3
        and f"lowest in-sample 256³ value ({min(ccpen_in):.2f})" in report
    )
    m5 = sorted(h[c]["rows"][CC]["merges"] for c in s5h)
    m_in = [i[c]["rows"][CC]["merges"] for c in i256]
    assert f"{m5[0]} and {m5[1]} merges, against {min(m_in)}–{max(m_in)}" in report
    dens5 = [h[c]["mask_density"] for c in s5h]
    assert (
        f"(density {_rng(dens5, '.4f').replace(', ', '–')}, against {_rng([i[c]['mask_density'] for c in i256], '.4f')})"
        in report
    )
    cov5 = sorted(cov(h[c]) for c in s5h)
    assert (
        f"falls to {cov5[0]:.2f} and {cov5[1]:.2f}, against\n{_rng([cov(i[c]) for c in i5], '.2f')}"
        in report
    )
    lab = {c: v["label_density"] for c, v in d.items()}
    assert (
        f"`s5_16997_03997_04497` has the densest label of any cube ({lab['s5_16997_03997_04497_256']:.4f})"
        in report
    )
    assert lab["s5_16997_03997_04497_256"] == max(lab.values())
    assert (
        f"(0.0179) lies within the\nin-sample range ({_rng([lab[c] for c in i], '.4f')})"
        in report
    )
    assert (
        f"(Scroll 3: {_rng([lab[c] for c in s3], '.4f')}, against {_rng([lab[c] for c in i512], '.4f')} in"
        in report
    )
