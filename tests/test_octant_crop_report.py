"""reports/octant_crop_rescore.md (finding 95): every figure from reports/octant_crop_rescore.json and finding 94's."""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import octant_crop_rescore as oc  # noqa: E402

OCJ = json.loads((ROOT / "reports/octant_crop_rescore.json").read_text())
T = json.loads((ROOT / "reports/tolerance4_rescore.json").read_text())
REPORT = " ".join((ROOT / "reports/octant_crop_rescore.md").read_text().split())
F94 = " ".join((ROOT / "reports/tolerance4_rescore.md").read_text().split())
PREREG = " ".join(
    (ROOT / "docs/preregistration/2026-10-21_octant_crop.md").read_text().split()
)
PEN = oc.PEN
OCT = OCJ["octants"]
med = statistics.median


def _rows(tol):
    return {
        k: {e: {float(tol): OCT[k][e][tol]} for e in ("neural", "tracer")} for k in OCT
    }


def test_the_result_is_ok_and_the_whole_cubes_are_finding_94s():
    assert OCJ["status"] == "OK" and OCJ["identity_problems"] == {} and len(OCT) == 24
    for c in oc.CUBES:
        assert OCJ["whole_cube_tol4"][c]["neural"][PEN] == T["rows_neural"][c][PEN]
        assert OCJ["whole_cube_tol4"][c]["tracer"][PEN] == T["rows_tracer"][c][PEN]
    assert "The status is `OK`" in REPORT


def test_the_verdict_is_recomputed_and_quoted():
    v = oc.verdict(_rows("4.0"))
    assert v == {k: OCJ[k] for k in v}
    lead = v["neural_leads_at_4"][0]
    assert v["prediction_P1_leads_on_16_of_24"] is True
    assert (
        f"| **held:** {lead} of 24 |" in REPORT
        and f"leads on {lead} of the 24 octants" in REPORT
    )
    assert (
        f"P1 held ({lead} of 24)" in PREREG
        and f"the lead held on {lead} of 24 at tolerance 4" in F94
    )


def test_the_octant_table():
    for tol, label in (("4.0", "4"), ("2.0", "2")):
        n = [OCT[k]["neural"][tol][PEN] for k in OCT]
        t = [OCT[k]["tracer"][tol][PEN] for k in OCT]
        r = [a / b for a, b in zip(n, t, strict=True)]
        leads = sum(a > b for a, b in zip(n, t, strict=True))
        row = (f"| {label} | {med(n):.2f} | {med(t):.2f} | {med(r):.2f} ({min(r):.2f}–{max(r):.2f}) | "
               f"{leads} of 24 |")  # fmt: skip
        assert row in REPORT, row


def test_the_lead_narrows_and_each_cubes_count():
    r_oct = med(
        OCT[k]["neural"]["4.0"][PEN] / OCT[k]["tracer"]["4.0"][PEN] for k in OCT
    )
    r_whole = med(T["rows_neural"][c][PEN] / T["rows_tracer"][c][PEN] for c in oc.CUBES)
    assert (
        f"a median {r_oct:.2f} on the octants, against {r_whole:.2f} on the whole cubes"
        in REPORT
    )
    per = [
        sum(
            OCT[k]["neural"]["4.0"][PEN] > OCT[k]["tracer"]["4.0"][PEN]
            for k in OCT
            if k.startswith(c)
        )
        for c in oc.CUBES
    ]
    assert (
        f"It leads on {per[0]}, {per[1]} and {per[2]} of each cube's 8 octants"
        in REPORT
    )
    assert all(OCT[k]["neural"]["2.0"][PEN] < OCT[k]["tracer"]["2.0"][PEN] for k in OCT)
    fibers = med(OCT[k]["neural"]["4.0"]["n_gt_fibers"] for k in OCT)
    assert f"An octant holds a median {fibers} ground-truth fibers" in REPORT


def test_the_scroll5_256_cubes_trail_too():
    s5 = [
        c
        for c in T["groups"]["in_sample"]
        if c.startswith("s5_") and c.endswith("_256")
    ]
    assert len(s5) == 3 and all(
        T["rows_neural"][c][PEN] < T["rows_tracer"][c][PEN] for c in s5
    )
    pairs = ", ".join(
        f"{T['rows_neural'][c][PEN]:.2f} against {T['rows_tracer'][c][PEN]:.2f}"
        for c in s5
    )
    assert (
        f"trails on all three ({pairs.rsplit(', ', 1)[0]} and {pairs.rsplit(', ', 1)[1]})"
        in REPORT
    )


def test_the_run_is_the_registered_one():
    assert (
        "registered at b5acd9bb" in REPORT and "00:29–01:06 PDT on 2026-10-21" in REPORT
    )
