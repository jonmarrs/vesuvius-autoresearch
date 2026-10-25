"""reports/neural_tracer_steep_heading.md (finding 100): every figure from its JSON and the run's logs."""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_steep_heading as sh  # noqa: E402

D = json.loads((ROOT / "reports/neural_tracer_steep_heading.json").read_text())
F99 = json.loads((ROOT / "reports/neural_tracer_heading_residual.json").read_text())
REPORT = " ".join((ROOT / "reports/neural_tracer_steep_heading.md").read_text().split())
REG = " ".join((ROOT / sh.__doc__.split()[0]).read_text().split())
CHAIN = (ROOT / "reports/evidence/neural_tracer_steep_heading_chain.txt").read_text()
WRAP = (ROOT / "reports/evidence/neural_tracer_steep_heading_wrapper.txt").read_text()
V = D["verdict"]
B2, B4 = D["baseline_rows_tol2"], D["baseline_rows_tol4"]
R2, R4 = D["rows_tol2"], D["rows_tol4"]
COV, PEN, PREC = sh.COV, sh.PEN, sh.PREC
S5, S3, HELD, IN = sh.HELD_S5, sh.S3, sh.HELD, sh.IN_SAMPLE


def span(vals, fmt="{:.3f}"):
    return f"{fmt.format(min(vals))}–{fmt.format(max(vals))}"


def factor(arm, c, rows=R2, base=B2, key=COV):
    return rows[arm][c][key] / base[c][key]


def test_the_verdict_is_the_registered_rule_on_these_rows():
    assert D["status"] == "OK" and D["smoke_identical"] is True and D["failed"] == []
    again = sh.verdict(R2, B2, D["records"], D["baseline_records"])
    assert again == V
    assert [V[f"prediction_P{i}"] for i in range(1, 6)] == [
        True,
        False,
        True,
        True,
        True,
    ]
    assert V["manipulation_ok"] == {"sheet": True, "keep": True}
    assert f'**Answer, the registered reading:** "{V["reading"]}".' in REPORT
    assert "Four of the five predictions held. P2 failed." in REPORT


def test_the_two_held_out_scroll_5_cubes():
    a, b = S5
    f = [factor("sheet", c) for c in S5]
    assert (
        f"Sheet's coverage rises from {B2[a][COV]:.3f} to {R2['sheet'][a][COV]:.3f} and from {B2[b][COV]:.3f} to "
        f"{R2['sheet'][b][COV]:.3f} ({f[0]:.2f}× and {f[1]:.2f}×)." in REPORT
    )
    assert "adds 1.20–1.43× coverage" in REPORT and (
        round(f[0], 2),
        round(f[1], 2),
    ) == (1.20, 1.43)
    p = [factor("sheet", c, key=PEN) for c in S5]
    assert f"Merge-penalized ERL rises {p[0]:.2f}× and {p[1]:.2f}×." in REPORT
    d = [R2["sheet"][c][PREC] - B2[c][PREC] for c in S5]
    assert (
        f"Precision moves by {d[0]:+.3f} and {d[1]:+.3f}.".replace("-", "−") in REPORT
    )
    k = [factor("keep", c) for c in S5]
    assert f"keep reaches {k[0]:.2f}× and {k[1]:.2f}×." in REPORT
    gain = [(k[i] - 1) / (f[i] - 1) for i in range(2)]
    assert (
        min(gain) >= 0.5 and max(gain) <= 2 / 3
    )  # "about half to two thirds of that gain"
    assert "villa's own axis recovers about half to two thirds of that gain" in REPORT
    t4 = [factor("sheet", c, R4, B4) for c in S5]
    assert (
        f"sheet's coverage rises {t4[0]:.2f}× and {t4[1]:.2f}× on the two Scroll-5 cubes"
        in REPORT
    )


def test_scroll_3():
    f = [factor("sheet", c) for c in S3]
    assert sum(x > 1 for x in f) == 8 and statistics.median(f) < sh.P2_MEDIAN
    assert (
        f"Coverage rises on all eight cubes, but by only {span(f)}×, a median of {statistics.median(f):.3f}×."
        in REPORT
    )
    assert "1.00–1.02× on Scroll 3" in REPORT and span(f, "{:.2f}") == "1.00–1.02"
    p = [factor("sheet", c, key=PEN) for c in S3]
    assert f"Merge-penalized ERL moves by {span(p, '{:.2f}')}×." in REPORT
    assert f"added at most {(max(f) - 1) * 100:.1f}% to coverage" in REPORT
    d = [R2["sheet"][c][PREC] - B2[c][PREC] for c in S3]
    assert f"cost up to {-min(d):.3f} of precision" in REPORT
    rec = D["baseline_records"]
    off = [rec[c]["no_heading"] / (rec[c]["dots"] - rec[c]["owned_dots"]) for c in S3]
    assert f"It skipped {span(off, '{:.2f}')} of the dots it offered there." in REPORT


def test_precision_heading_and_in_sample():
    d = [R2["sheet"][c][PREC] - B2[c][PREC] for c in HELD]
    assert max(abs(x) for x in d) < 0.0175
    assert (
        f"sheet's precision is within 0.017 of the baseline's ({min(d):+.3f} to {max(d):+.3f})".replace(
            "-", "−"
        )
        in REPORT
    )
    above = sum(R2["sheet"][c][COV] > R2["keep"][c][COV] for c in HELD)
    assert (
        f"Sheet's coverage is above keep's on {above} of the 10 held-out cubes."
        in REPORT
    )
    s, k = [factor("sheet", c) for c in IN], [factor("keep", c) for c in IN]
    assert (
        f"Sheet's coverage factors lie in {span(s)} on the eleven in-sample cubes, and keep's in {span(k)}."
        in REPORT
    )
    assert f"**held** ({span(s + k)}×)" in REPORT and max(s + k) - 1 < 0.015 + 5e-4
    assert "within 1.5% of coverage and 0.003 of precision" in REPORT
    assert max(abs(R2[a][c][PREC] - B2[c][PREC]) for a in sh.ARMS for c in IN) < 0.003
    assert "both arms' precision moves by at most 0.003" in REPORT


def test_the_ranking_against_our_tracer_does_not_change():
    for rows, base, ours in (
        (R2, B2, D["our_tracer_tol2"]),
        (R4, B4, D["our_tracer_tol4"]),
    ):
        for a in sh.ARMS:
            for c in sh.ALL_CUBES:
                assert (rows[a][c][PEN] > ours[c][PEN]) == (
                    base[c][PEN] > ours[c][PEN]
                ), (a, c)
    assert (
        "On no cube, at either tolerance, does either arm change whether the neural tracer leads or trails"
        in REPORT
    )


def test_the_table_is_the_json():
    rb, rs, rk = D["baseline_records"], D["records"]["sheet"], D["records"]["keep"]
    s, k, o = R2["sheet"], R2["keep"], D["our_tracer_tol2"]
    for c in HELD:
        row = (
            f"| {c[:-4]} | {B2[c][COV]:.3f} → **{s[c][COV]:.3f}** ({k[c][COV]:.3f}) | {B2[c][PREC]:.3f} → "
            f"{s[c][PREC]:.3f} ({k[c][PREC]:.3f}) | {B2[c][PEN]:.2f} → {s[c][PEN]:.2f} ({k[c][PEN]:.2f}; "
            f"{o[c][PEN]:.2f}) | {rb[c]['traced']:,} → {rs[c]['traced']:,} ({rk[c]['traced']:,}) |"
        )
        assert row in REPORT, c


def test_the_predictions_table():
    f = [factor("sheet", c) for c in S3]
    assert (
        f"| P1 (moderate) | sheet's coverage at least {sh.P1_FACTOR}× on both held-out Scroll-5 cubes | **held**"
        in REPORT
    )
    assert (
        f"| P2 (moderate) | sheet's coverage rises on at least {sh.P2_RISE_AT_LEAST} of 8 Scroll-3 cubes, median at "
        f"least {sh.P2_MEDIAN}× | **failed**: it rises on {sum(x > 1 for x in f)}, median {statistics.median(f):.3f}×"
        in REPORT
    )
    n3 = sum(R2["sheet"][c][PREC] - B2[c][PREC] >= -sh.P3_DROP for c in HELD)
    assert f"| P3 (moderate) | sheet's precision at most {sh.P3_DROP} lower on at least {sh.P3_AT_LEAST} of 10 held-out cubes | **held** ({n3} of 10) |" in REPORT  # fmt: skip
    n4 = sum(R2["sheet"][c][COV] > R2["keep"][c][COV] for c in HELD)
    assert f"| P4 (low) | sheet's coverage above keep's on at least {sh.P4_AT_LEAST} of 10 held-out cubes | **held** ({n4} of 10) |" in REPORT  # fmt: skip
    lo, hi = sh.P5_BAND
    assert (
        f"| P5 (high) | both arms' coverage {lo}–{hi}× on all 11 in-sample cubes | **held**"
        in REPORT
    )
    # the registration's own estimates, quoted
    assert "coverage would rise about 1.3× and 1.5× on the two Scroll-5 cubes" in REG
    assert "rise a median 1.10× (1.03–1.18)" in REG
    assert "The registration estimated about 1.3× and 1.5× on the two Scroll-5 cubes, and a median 1.10× on Scroll 3." in REPORT  # fmt: skip


def test_the_manipulation_and_the_tallies():
    tally = {a: {} for a in sh.ARMS}
    for a in sh.ARMS:
        for c in HELD:
            assert D["records"][a][c]["no_heading"] == 0, (a, c)
            for kind, n in D["records"][a][c]["offered"].items():
                tally[a][kind] = tally[a].get(kind, 0) + n
    sheet = tally["sheet"]["rescued"] + tally["sheet"]["rescued_far"]
    assert tally["keep"]["rescued_far"] == 0
    assert all(
        tally[a][k] == 0 for a in sh.ARMS for k in ("skipped", "degenerate", "error")
    )
    assert f"Sheet traced {sheet:,} skipped dots across the ten held-out cubes; keep traced {tally['keep']['rescued']:,}." in REPORT  # fmt: skip
    assert f"{tally['sheet']['rescued_far']} of sheet's dots had a presence direction more than 45° out of the sheet" in REPORT  # fmt: skip
    skipped = [D["baseline_records"][c]["no_heading"] for c in HELD]
    assert f"The baseline had skipped {min(skipped)}–{max(skipped)} per cube." in REPORT
    # finding 99's steep shares on the two Scroll-5 cubes, and the pre-flight's dot count
    f99 = F99["cubes"]
    steep = [sum((f99[c]["near_gt"][g]["steep_sheet_share"] or 0) * f99[c]["counts"][g] for g in ("disagree", "ok"))
             / f99[c]["classified"] for c in S5]  # fmt: skip
    assert f"These are the cubes with {steep[0]:.2f} and {steep[1]:.2f} of their dots in sheets tilted more than 45°" in REPORT  # fmt: skip
    assert f99[sh.SMOKE]["dots"] == 910 and "result on all 910 dots" in REPORT


def _at(line_prefix: str, text: str) -> str:
    return re.search(
        rf"^{re.escape(line_prefix)}.*?T(\d\d:\d\d:\d\d)", text, re.M
    ).group(1)


def test_the_timings_are_the_logs():
    assert (
        _at("LOOP_STOPPED", WRAP) == "01:09:57"
        and _at("SMOKE_OK ", CHAIN) == "01:11:05"
    )
    assert (
        _at("CHAIN_COMPLETE", CHAIN) == "02:55:18"
        and _at("LOOP_RESTARTED", WRAP) == "02:55:48"
    )
    assert (
        _at("SCORE_RC 0", WRAP) == "04:15:34"
        and "CHAIN_START 9d31f36d villa ccb431818" in CHAIN
    )
    assert (
        "the loop was stopped at 01:09:57" in REPORT
        and "the smoke ran from 01:09:57 to 01:11:05" in REPORT
    )
    assert (
        "the 42 runs ran from 01:11:05 to 02:55:18" in REPORT
        and "the loop restarted at 02:55:48, 1 h 46 min" in REPORT
    )
    assert "until 04:15:34" in REPORT and "at 9d31f36d, villa `ccb431818`" in REPORT
    done = re.findall(r"^DONE (\w+) (\S+)", CHAIN, re.M)
    assert len(done) == 42 and "FAILED" not in CHAIN
    order = [(a, c) for s in (HELD, IN) for a in sh.ARMS for c in s]
    assert (
        done == order
    )  # sheet, then keep, on the held-out set, then both on the in-sample set


def test_the_post_run_edit_is_disclosed():
    """The chain's refusal prefix was renamed after the run, to the one the repository's chain guard requires; no
    refusal fired during the run."""
    chain = (ROOT / "repro/fibers/run_neural_tracer_steep_heading_chain.sh").read_text()
    assert "SH_ABORTED" not in chain and "ABORTED" not in CHAIN
    assert (
        "Its refusal messages were renamed from `SH_ABORTED` to `SC_ABORTED`" in REPORT
    )
