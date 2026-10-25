"""docs/VILLA_DRAFT_volume_seed_heading.md: every figure from finding 100's `keep` arm, and the patch is that arm.

The draft proposes deleting the 35° skip from villa's `tracing/volume.py` `_seed_heading`. Finding 100's `keep` arm
measured exactly that: each skipped dot traced from villa's own CT axis, signed along its presence direction. These
tests recompute the draft's numbers from reports/neural_tracer_steep_heading.json, and check that villa's own
`_seed_heading`, patched as repro/fibers/villa_volume_seed_heading.patch patches it, returns the `keep` arm's heading.
"""

from __future__ import annotations

import ast
import json
import re
import statistics
import subprocess
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/VILLA_DRAFT_volume_seed_heading.md"
PATCH = ROOT / "repro/fibers/villa_volume_seed_heading.patch"
F100 = ROOT / "reports/neural_tracer_steep_heading.json"
F99 = ROOT / "reports/neural_tracer_heading_residual.json"
EVIDENCE = ROOT / "reports/evidence/villa_volume_seed_heading_tests.txt"
RERUN = ROOT / "reports/evidence/villa_volume_seed_heading_rerun.json"
RERUN_LOG = ROOT / "reports/evidence/villa_volume_seed_heading_rerun_chain.txt"
VOLUME = "vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume.py"
VILLA = ROOT / "villa"

S5 = ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]


def _text() -> str:
    return " ".join(DRAFT.read_text().split())


def _d():
    d = json.loads(F100.read_text())
    s3 = [c for c in d["baseline_rows_tol2"] if c.startswith("s3_")]
    ins = [c for c in d["baseline_rows_tol2"] if c not in S5 + s3]
    assert len(s3) == 8 and len(ins) == 11
    return d, s3, ins


def _span(vals, fmt="{:.3f}"):
    return f"{fmt.format(min(vals))}–{fmt.format(max(vals))}"


def _signed(x):
    return f"{x:+.3f}".replace("-", "−")


def test_the_table_is_finding_100s_keep_arm():
    d, s3, _ = _d()
    b, k, rec = d["baseline_rows_tol2"], d["rows_tol2"]["keep"], d["baseline_records"]
    assert d["status"] == "OK" and d["verdict"]["manipulation_ok"]["keep"] is True
    for c in S5 + s3:
        row = (
            f"| {c} | {rec[c]['no_heading']:,} of {rec[c]['dots']:,} | {b[c]['coverage']:.3f} → "
            f"{k[c]['coverage']:.3f} | {b[c]['precision']:.3f} → {k[c]['precision']:.3f} | "
            f"{b[c]['erl_merge_penalized']:.2f} → {k[c]['erl_merge_penalized']:.2f} |"
        )
        assert row in DRAFT.read_text(), row
    # the baseline is finding 97 and 98's runs, the skip its only drop on these cubes
    assert all(d["records"]["keep"][c]["offered"]["skipped"] == 0 for c in S5 + s3)


def test_the_example_and_the_summary():
    d, s3, ins = _d()
    b, k, rec = d["baseline_rows_tol2"], d["rows_tol2"]["keep"], d["baseline_records"]
    txt = _text()
    c = "s5_16997_03997_04497_256"
    kr = d["records"]["keep"][c]
    assert (
        kr["no_heading"] == 0
        and kr["traced"] + kr["owned_dots"] == kr["dots"] == rec[c]["dots"]
    )
    assert kr["traced"] == kr["offered"]["agree"] + kr["offered"]["rescued"]
    assert (
        f"`tracing.volume` skipped {rec[c]['no_heading']} of the cube's {rec[c]['dots']} seed dots on the 35° test "
        f"and traced {rec[c]['traced']}. With this PR it skips none on that test and traces {kr['traced']}, "
        f"{kr['offered']['rescued']} of them dots that fail it; the rest of the {kr['dots']} lie on fibers already "
        f"written. Coverage of the cube's hand-traced fibers rises from {b[c]['coverage']:.3f} to "
        f"{k[c]['coverage']:.3f}, and precision from {b[c]['precision']:.3f} to {k[c]['precision']:.3f}."
        in txt
    )

    def fac(c):
        return k[c]["coverage"] / b[c]["coverage"]

    share = [rec[c]["no_heading"] / rec[c]["dots"] for c in S5]
    assert (
        f"the two Scroll-5 cubes gain {fac(S5[0]):.2f}× and {fac(S5[1]):.2f}× coverage, where the skip dropped "
        f"{share[0]:.2f} and {share[1]:.2f} of the seed dots." in txt
    )
    assert all(fac(c) > 1 for c in s3)
    assert (
        f"On Scroll 3 coverage rises on all eight cubes, by {_span([fac(c) for c in s3])}×."
        in txt
    )
    dp = [k[c]["precision"] - b[c]["precision"] for c in S5 + s3]
    assert f"Precision moves by {_signed(min(dp))} to {_signed(max(dp))}." in txt
    drops = [rec[c]["no_heading"] for c in ins]
    dpi = [abs(k[c]["precision"] - b[c]["precision"]) for c in ins]
    assert (
        f"the skip dropped only {min(drops)}–{max(drops)} dots per cube, and coverage moves by "
        f"{_span([fac(c) for c in ins])}×, precision by at most {max(dpi):.3f}." in txt
    )
    # the sheet arm, named as recovering more and not proposed
    sh = d["rows_tol2"]["sheet"]
    assert (
        f"gave {sh[S5[0]]['coverage'] / b[S5[0]]['coverage']:.2f}× and "
        f"{sh[S5[1]]['coverage'] / b[S5[1]]['coverage']:.2f}× coverage. That is a new rule the model never trained on, "
        "so it is not proposed here." in txt
    )


def test_the_steep_sheet_shares_are_finding_99s():
    c = json.loads(F99.read_text())["cubes"]

    def steep(k):
        r = c[k]
        return sum((r["near_gt"][g]["steep_sheet_share"] or 0) * r["counts"][g] for g in ("disagree", "ok")) / r["classified"]  # fmt: skip

    a, b = (steep(k) for k in S5)
    assert (
        f"On the two Scroll-5 cubes the share of dots in sheets tilted more than 45° is {a:.2f} and {b:.2f}."
        in _text()
    )


def _hunk_removals() -> list[str]:
    """The production lines the patch removes from volume.py."""
    out, current = [], None
    for line in PATCH.read_text().splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif current == VOLUME and line.startswith("-") and not line.startswith("---"):
            out.append(line[1:])
    return out


def test_the_patch_removes_only_the_35_degree_skip():
    removed = _hunk_removals()
    code = [
        ln for ln in removed if not ln.startswith(("Tracing streams", "a dot whose"))
    ]
    assert code == [
        "    if abs(h @ direction) < np.cos(np.radians(35)):",
        "        return None",
    ]
    text = PATCH.read_text()
    assert text.count("\n+++ b/") == 2  # volume.py and the new test, nothing else
    assert (
        "+++ b/vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/test_volume_seed_heading.py"
        in text
    )
    added = sum(
        ln.startswith("+") and not ln.startswith("+++") for ln in text.splitlines()
    )
    gone = sum(
        ln.startswith("-") and not ln.startswith("---") for ln in text.splitlines()
    )
    assert (added, gone) == (23, 4)
    assert "(+23/−4" in _text()


def _villa_seed_heading(source: str, patched: bool):
    """villa's own `_seed_heading`, from its source, optionally with the patch's two lines removed."""
    tree = ast.parse(source)
    fn = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_seed_heading"
    )
    src = ast.get_source_segment(source, fn)
    assert src is not None
    if patched:  # the two removed lines, as one block
        block = "\n".join(_hunk_removals()[-2:]) + "\n"
        assert src.count(block) == 1
        src = src.replace(block, "")

    class SeedHeadingError(Exception):
        pass

    box: dict = {}
    ns = {
        "np": np,
        "SeedHeadingError": SeedHeadingError,
        "_WORKER_VOL": None,
        "ct_seed_heading": lambda vol, xyz, family: box["h"],
    }
    exec(compile(src, "volume.py:_seed_heading", "exec"), ns)
    return ns["_seed_heading"], box


@pytest.mark.skipif(not (VILLA / VOLUME).exists(), reason="villa checkout absent")
def test_patched_villa_seed_heading_is_the_keep_arm(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import neural_tracer_heading_arm as arms

    source = (VILLA / VOLUME).read_text()
    before, box_b = _villa_seed_heading(source, patched=False)
    after, box_a = _villa_seed_heading(source, patched=True)
    rng = np.random.default_rng(100)
    kinds = set()
    for _ in range(2000):
        h = rng.normal(size=3)
        h /= np.linalg.norm(h)
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        normal = np.cross(h, rng.normal(size=3))
        normal /= np.linalg.norm(normal)
        box_b["h"] = box_a["h"] = h
        for fn, arm in ((before, "villa"), (after, "keep")):
            got = fn((None, "H", d))
            want, kind = arms.choose(h, normal, d, arm)
            kinds.add((arm, kind))
            assert (got is None) == (want is None)
            if want is not None:
                np.testing.assert_array_equal(got, want)
    assert kinds == {
        ("villa", "agree"),
        ("villa", "skipped"),
        ("keep", "agree"),
        ("keep", "rescued"),
    }


@pytest.mark.skipif(not (VILLA / VOLUME).exists(), reason="villa checkout absent")
def test_the_patch_applies_to_the_pinned_villa():
    r = subprocess.run(
        ["git", "-C", str(VILLA), "apply", "--check", str(PATCH)],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert r.returncode == 0, r.stderr


def test_the_image_is_the_scorers_coverage():
    """The figure's record (scripts/villa_seed_heading_figure.py): its covered share reproduces ScrollGT's coverage,
    and the draft quotes its length shares."""
    rec = json.loads(
        (ROOT / "reports/figures/villa_volume_seed_heading_s5_16997.json").read_text()
    )
    d, _, _ = _d()
    c = rec["cube"]
    assert c == "s5_16997_03997_04497_256" and rec["tolerance"] == 2.0
    assert rec["json_coverage"] == {
        "before": d["baseline_rows_tol2"][c]["coverage"],
        "after": d["rows_tol2"]["keep"][c]["coverage"],
    }
    for k in ("before", "after"):
        assert rec["scorer_coverage"][k] == rec["json_coverage"][k]
        assert abs(rec["covered_share"][k] - rec["json_coverage"][k]) < 5e-5
    ls = rec["length_share"]
    assert abs(sum(ls.values()) - 1) < 1e-9
    txt = _text()
    assert (
        f"Orange is the {ls['covered only without the skip']:.3f} of the ground-truth length covered only with this "
        f"PR. Red is the {ls['covered only with the skip']:.3f} covered only on main."
        in txt
    )


def test_the_villa_test_counts_are_the_transcript():
    ev = EVIDENCE.read_text()
    main, patched = ev.split("== volume.py patched")
    assert "villa 322cb0899" in ev and "5 failed, 4 passed" in main
    failed = sorted(
        int(x)
        for x in re.findall(
            r"^FAILED \S+signed_along_the_presence_direction\[(\d+)\]$", main, re.M
        )
    )
    assert failed == [36, 60, 89, 91, 120]
    assert "20 passed" in patched and "failed" not in patched
    # the nine cases: eight angles and the dot without a CT heading
    assert (
        "@pytest.mark.parametrize('degrees', [0, 34, 36, 60, 89, 91, 120, 179])"
        in PATCH.read_text()
    )
    assert (
        "Without the change 5 of its 9 cases fail (the dots at 36°, 60°, 89°, 91° and 120°); with it all 9 pass, and "
        "so do the 11 in `test_volume_performance.py`." in _text()
    )


def test_the_rerun_on_villa_main_reproduces_both_runs():
    """repro/fibers/run_villa_seed_heading_rerun.sh, compared and scored by scripts/villa_seed_heading_rerun.py:
    villa's CLI at 322cb0899 traced the two Scroll-5 cubes as at ccb431818, without the patch and with it."""
    r = json.loads(RERUN.read_text())
    d, _, _ = _d()
    assert (r["status"], r["villa"], r["source_villa"]) == (
        "IDENTICAL",
        "322cb0899",
        "ccb431818",
    )
    assert r["scoring_version"] == 3 and r["tolerance"] == 2.0
    # the comparison tells the two runs apart
    assert r["before_identical_to_after"] == {c: False for c in S5}
    want = {"before": d["baseline_rows_tol2"], "after": d["rows_tol2"]["keep"]}
    for side in ("before", "after"):
        assert set(r["runs"][side]) == set(S5)
        for c, run in r["runs"][side].items():
            assert run["identical_to_source"] is True
            assert run["counts"] == run["source_counts"]
            assert run["row_tol2"] == {k: want[side][c][k] for k in run["row_tol2"]}
    no_heading = {
        s: [r["runs"][s][c]["counts"]["no_heading"] for c in S5] for s in r["runs"]
    }
    assert no_heading == {
        "before": [d["baseline_records"][c]["no_heading"] for c in S5],
        "after": [0, 0],
    }
    log = RERUN_LOG.read_text()
    assert re.findall(r"^CHAIN_START repo \w+ villa (\w+)", log, re.M) == [r["villa"]]
    assert re.findall(r"^(DONE \w+ \S+)", log, re.M) == [
        f"DONE {s} {c}" for s in ("before", "after") for c in S5
    ]
    assert "FAILED" not in log and "CHAIN_COMPLETE" in log
    # the loop's pause, from the wrapper that stopped and restarted it around the chain
    wrap = (
        ROOT / "reports/evidence/villa_volume_seed_heading_rerun_wrapper.txt"
    ).read_text()
    assert "status rc=1" in wrap and "chain rc=0" in wrap
    (stop,) = re.findall(r"^2026-10-25 (\d\d:\d\d):\d\d stop\.sh rc=0$", wrap, re.M)
    (h, m, sec) = re.findall(
        r"^2026-10-25 (\d\d):(\d\d):(\d\d) start\.sh rc=0$", wrap, re.M
    )[0]
    start = f"{h}:{int(m) + (int(sec) >= 30):02d}"
    assert f"(the loop paused {stop}–{start})" in _text()
    assert (
        "On the two Scroll-5 cubes, villa's CLI at `322cb0899` gives the same traces point for point as at "
        "`ccb431818`, both without this PR and with it, so their rows above hold on main. The Scroll-3 and in-sample "
        "cubes were not re-run." in _text()
    )
