"""reports/neural_tracer_seeding.md (finding 93): every figure from reports/neural_tracer_seeding.json, the probe and
finding 92's funnel."""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_seeding_analysis as sa  # noqa: E402


def _text(rel):
    return " ".join((ROOT / rel).read_text().split())


D = json.loads((ROOT / "reports/neural_tracer_seeding.json").read_text())
F = json.loads((ROOT / "reports/neural_tracer_pitch_funnel.json").read_text())["cubes"]
REPORT = _text("reports/neural_tracer_seeding.md")
PITCH = _text("reports/neural_tracer_pitch.md")
PREREG = _text("docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md")
PEN, COV = sa.PEN, sa.COV
A, B, N, P, COMP = (
    D["rows_A"],
    D["rows_B"],
    D["native_rows"],
    D["pitch_rows"],
    D["comparators"],
)
G = D["groups"]
ALL = sa.f91.ALL
med = statistics.median


def _ratios(X, key=PEN):
    return [X[c][key] / N[c][key] for c in ALL]


def _leads(X, cubes):
    return sum(X[c][PEN] > COMP[c]["tracer"][PEN] for c in cubes)


def test_the_result_is_the_registered_analysis_on_every_run():
    assert D["status"] == "OK" and D["smoke"] == {
        "cube": sa.SMOKE_CUBE,
        "identical_to_finding_91": True,
    }
    assert D["failed_runs"] == {"A": [], "B": []} and D["scored"] == {"A": 21, "B": 21}
    assert D["identity_problems"] == {"A": {}, "B": {}} and D[
        "manipulation_problems"
    ] == {"A": {}, "B": {}}
    assert (
        D["arms"]["A"]["smoothing"] == sa.ARMS["A"]["smoothing"]
        and D["arms"]["B"]["settings"] == sa.ARMS["B"]["settings"]
    )
    probe = json.loads((ROOT / "reports/neural_tracer_seed_probe.json").read_text())[
        "cubes"
    ]
    for arm in "AB":
        assert all(
            D["funnel"][arm][c]["dots"] == probe[c][arm]["flags_smooth"]["dots"]
            for c in ALL
        )
    assert "The analysis' status is `OK`" in REPORT and "All 42 runs finished" in REPORT


def test_the_verdict_is_recomputed_and_quoted():
    v = sa.verdict(A, B, N, COMP)
    assert {k: v[k] for k in ("predictions", "conclusion")} == {
        k: D[k] for k in ("predictions", "conclusion")
    }
    assert (
        not any(v["predictions"].values())
        and v["conclusion"] == "the seeding scale is not the cause: the note stands"
    )
    assert f"| **failed:** {D['median_pen_ratio_A']:.2f} |" in REPORT
    assert f"| **failed:** {D['s3_leading_tracer_A'][0]} of 8 |" in REPORT
    assert f"| **failed:** {D['median_pen_ratio_B']:.2f} |" in REPORT
    assert (
        "**Answer: the seeding scale is not the cause.** All three predictions failed."
        in REPORT
    )


def test_the_group_table():
    names = {
        "in_sample": "in sample",
        "s3": "Scroll 3",
        "s5_held_out": "held-out Scroll 5",
    }
    for g, name in names.items():
        cs = G[g]
        cells = [f"{med(X[c][PEN] for c in cs):.2f}" for X in (A, B, N, P)]
        cells.append(f"{med(COMP[c]['tracer'][PEN] for c in cs):.2f}")
        assert f"| {name} | {len(cs)} | " + " | ".join(cells) + " |" in REPORT, name


def test_the_ratio_table():
    for label, X in (
        ("A: 9.6 µm, seeded as natively", A),
        ("B: native, seeded as at 9.6 µm", B),
        ("finding 92: 9.6 µm, villa's seeding", P),
    ):
        p, c = _ratios(X), _ratios(X, COV)
        below = sum(x < 1 for x in p)
        row = (f"| {label} | {med(p):.2f} ({min(p):.2f}–{max(p):.2f}) | {below} of 21 | "
               f"{med(c):.2f} ({min(c):.2f}–{max(c):.2f}) |")  # fmt: skip
        assert row in REPORT, row


def test_the_bullets():
    a_cov, p_cov = med(_ratios(A, COV)), med(_ratios(P, COV))
    a_pen, p_pen = med(_ratios(A)), med(_ratios(P))
    assert (
        f"Arm A's coverage is {a_cov:.2f} of native, against finding 92's {p_cov:.2f}, but its ERLpen is "
        f"{a_pen:.2f} against {p_pen:.2f}" in REPORT
    )
    above = sum(A[c][PEN] > P[c][PEN] for c in ALL)
    assert all(A[c][PEN] < COMP[c]["tracer"][PEN] for c in G["s3"])
    assert (
        f"It beats finding 92's run on {above} of 21 cubes, and trails our tracer on all 8 Scroll-3 cubes"
        in REPORT
    )
    traces = med(D["funnel"]["B"][c]["traced"] / F[c]["native"]["traced"] for c in ALL)
    dots = {
        arm: med(D["funnel"][arm][c]["dots"] / F[c]["native"]["dots"] for c in ALL)
        for arm in "AB"
    }
    assert (
        f"Arm B starts {traces:.2f} as many traces as native from {dots['B']:.2f} of the seeds"
        in REPORT
    )
    assert (
        f"Its ERLpen is {med(_ratios(B)):.2f} of native, and it still leads our tracer on {_leads(B, G['s3'])} of 8"
        in REPORT
    )
    assert (
        f"Arm A's seeds are a median {dots['A']:.2f} of native, and arm B's {dots['B']:.2f}"
        in REPORT
    )
    nh = {
        "A": med(
            D["funnel"]["A"][c]["no_heading"] / D["funnel"]["A"][c]["dots"] for c in ALL
        ),
        "native": med(
            F[c]["native"]["no_heading"] / F[c]["native"]["dots"] for c in ALL
        ),
        "pitch": med(F[c]["pitch"]["no_heading"] / F[c]["pitch"]["dots"] for c in ALL),
    }
    pct = {k: round(100 * v) for k, v in nh.items()}
    assert f"still turns away {pct['A']}% of seed dots" in REPORT
    assert (
        f"against {pct['native']}% natively and {pct['pitch']}% in finding 92" in REPORT
    )
    trails = [
        sum(X[c][PEN] < COMP[c]["tracer"][PEN] for c in G["in_sample"]) for X in (A, B)
    ]
    assert (
        trails == [11, 11]
        and "Both trail our tracer on all 11 in-sample cubes" in REPORT
    )


def test_the_answer_paragraph_and_the_pointers():
    a, p, b = med(_ratios(A)), med(_ratios(P)), med(_ratios(B))
    assert f"lifts merge-penalized ERL only from {p:.2f} to {a:.2f} of native" in REPORT
    assert (
        f"a little: {b:.2f} of native, with the Scroll-3 lead kept on {_leads(B, G['s3'])} of 8 cubes"
        in REPORT
    )
    assert (
        f"merge-penalized ERL rises only from {p:.2f} to {a:.2f} of native. Seeding the native cubes as sparsely "
        f"costs only a little ({b:.2f}), and keeps the Scroll-3 lead on {_leads(B, G['s3'])} of 8 cubes"
        in PITCH
    )
    assert (
        "Finding 93 then tested seeding per micrometre, and seeding is not why the score fell."
        in PITCH
    )
    assert "The run is proposed, not registered" not in PITCH
    assert (
        "finding 93, `reports/neural_tracer_seeding.md`. All three predictions failed"
        in PREREG
    )


def test_the_run_times_are_the_chains():
    """From the chain log: CHAIN_START 00:22:53, CHAIN_COMPLETE 01:28:20; stop.sh at 00:22:45 (wrapper log)."""
    assert (
        "Traced 00:22:53–01:28:20 PDT on 2026-10-20 with the loop paused (`stop.sh` at 00:22:45)"
        in REPORT
    )
    assert "registered at c23d3a08" in REPORT
