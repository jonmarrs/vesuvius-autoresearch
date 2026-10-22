"""reports/tolerance4_rescore.md (finding 94): every figure from reports/tolerance4_rescore.json."""

import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import tolerance4_rescore as t4  # noqa: E402

D = json.loads((ROOT / "reports/tolerance4_rescore.json").read_text())
REPORT = " ".join((ROOT / "reports/tolerance4_rescore.md").read_text().split())
ENTRANT = " ".join((ROOT / "reports/neural_tracer_entrant.md").read_text().split())
PREREG = " ".join(
    (ROOT / "docs/preregistration/2026-10-20_tolerance4_rescore.md").read_text().split()
)
PEN = t4.PEN
N, T, CC = D["rows_neural"], D["rows_tracer"], D["rows_cc"]
PN, PT, PC = D["published_neural"], D["published_tracer"], D["published_cc"]
G = D["groups"]
INS, S3 = G["in_sample"], G["s3"]
I256 = [c for c in INS if c.endswith("_256")]
I512 = [c for c in INS if c.endswith("_512")]
OFFSET5 = {  # neural_tracer_gt_offset.json's five cubes (mean shift at least a voxel), #157
    "s1_00497_01497_03997_256",
    "s1_08997_02997_02497_256",
    "s5_14997_01497_01497_256",
    "s5_06494_01994_03994_512",
    "s5_06994_00994_04994_512",
}
med = statistics.median


def test_the_five_offset_cubes_are_neural_tracer_gt_offset_jsons():
    shifts = json.loads((ROOT / "reports/neural_tracer_gt_offset.json").read_text())[
        "cubes"
    ]
    assert {c for c, v in shifts.items() if math.hypot(*v["shift"]) >= 1} == OFFSET5


def test_the_result_is_ok_on_the_published_labellings():
    assert (
        D["status"] == "OK" and D["identity_problems"] == {} and D["tolerance"] == 4.0
    )
    for name, rows, pub in (("tracer", T, PT), ("cc", CC, PC)):
        assert len(rows) == 21 and all(
            t4.identity_problems(pub[c], rows[c]) == [] for c in rows
        ), name
    assert "All 42 labellings" in REPORT and "The status is `OK`" in REPORT


def test_the_rows_are_at_the_tolerances_compared():
    """Every row records its own tolerance and scoring version. The neural tracer's tolerance-4 rows, finding 91's,
    keep its published rows' fixed fields, as our tracer's and connected components' do."""
    for rows, tol in ((N, 4.0), (T, 4.0), (CC, 4.0), (PN, 2.0), (PT, 2.0), (PC, 2.0)):
        assert len(rows) == 21
        assert {(r["tolerance"], r["scoring_version"]) for r in rows.values()} == {
            (tol, 3)
        }
    assert all(t4.identity_problems(PN[c], N[c]) == [] for c in N)


def test_the_verdict_is_recomputed_and_quoted():
    v = t4.verdict(N, T)
    assert {
        k: v[k]
        for k in (
            "predictions",
            "s3_leading_tracer",
            "in_sample_trailing_tracer",
            "readings",
        )
    } == {
        k: D[k]
        for k in (
            "predictions",
            "s3_leading_tracer",
            "in_sample_trailing_tracer",
            "readings",
        )
    }
    assert v["predictions"] == {
        "P1_s3_leads_tracer_on_6_of_8": True,
        "P2_in_sample_trails_tracer_on_9_of_11": False,
    }
    lead, trail = D["s3_leading_tracer"][0], D["in_sample_trailing_tracer"][0]
    assert (
        f"| **held:** {lead} of 8 |" in REPORT
        and f"| **failed:** {trail} of 11 |" in REPORT
    )
    assert f"P1 held ({lead} of 8) and P2 failed ({trail} of 11)" in PREREG


def test_the_group_table():
    names = {
        "in_sample": "in sample",
        "s3": "Scroll 3",
        "s5_held_out": "held-out Scroll 5",
    }
    for g, name in names.items():
        cs = G[g]
        cells = [f"{med(X[c][PEN] for c in cs):.2f}" for X in (N, T, CC, PN, PT)]
        assert f"| {name} | {len(cs)} | " + " | ".join(cells) + " |" in REPORT, name


def _ratio(cubes, a, b):
    return [a[c][PEN] / b[c][PEN] for c in cubes]


def test_the_scroll3_lead_widens():
    r4, r2 = _ratio(S3, N, T), _ratio(S3, PN, PT)
    assert (
        f"a median {med(r4):.2f} ({min(r4):.2f}–{max(r4):.2f}) at tolerance 4, against {med(r2):.2f} at 2"
        in REPORT
    )
    assert (
        all(N[c][PEN] > CC[c][PEN] for c in S3)
        and "It also leads connected components on all 8" in REPORT
    )
    assert f"widens to a median {med(r4):.2f} times our tracer" in ENTRANT


def test_the_in_sample_deficit_narrows_and_reverses_on_the_512_cubes():
    r4, r2 = _ratio(INS, N, T), _ratio(INS, PN, PT)
    assert (
        f"Over ours it is a median {med(r4):.2f} at tolerance 4, against {med(r2):.2f} at 2"
        in REPORT
    )
    assert all(N[c][PEN] < T[c][PEN] for c in I256) and len(I256) == 8
    assert all(N[c][PEN] > T[c][PEN] for c in I512) and len(I512) == 3
    assert (
        f"leads on all 3 in-sample 512³ ones (median {med(N[c][PEN] for c in I512):.2f} against "
        f"{med(T[c][PEN] for c in I512):.2f})" in REPORT
    )
    assert (
        len(set(I512) & OFFSET5) == 2
        and "Two of those three are among the five cubes" in REPORT
    )
    assert all(N[c][PEN] < T[c][PEN] for c in G["s5_held_out"])
    assert "The in-sample deficit reverses on the three 512³ cubes." in ENTRANT


def test_the_thin_tracer_gains_most():
    def gain(a, b, cubes):
        return med(a[c][PEN] / b[c][PEN] for c in cubes)

    n = (gain(N, PN, INS), gain(N, PN, S3))
    t = (gain(T, PT, INS), gain(T, PT, S3))
    c = (gain(CC, PC, INS), gain(CC, PC, S3))
    assert min(n) > max(t) > max(c)
    assert (
        f"rises a median {n[0]:.2f} times in sample and {n[1]:.2f} times on Scroll 3, against our tracer's "
        f"{t[0]:.2f} and {t[1]:.2f} and connected components' {c[0]:.2f} and {c[1]:.2f}"
        in REPORT
    )


def test_the_run_is_the_registered_one():
    assert "registered at 04cb7e51" in REPORT and "scored 11:24–12:20 PDT" in REPORT
