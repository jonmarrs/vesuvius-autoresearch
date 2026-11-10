"""scripts/afv_generator_cross_block_duplicates.py (finding 108's run): the catalogue gate, the patch it tests, the
registered decision rule, and the registration's figures from its evidence."""

from __future__ import annotations

import copy
import json
import statistics
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_cross_block_duplicates as xd  # noqa: E402

VILLA = Path("/home/jon/openclaw-workspace/Neo-VM/projects/villa")
PATCHED = (
    Path("/home/jon/openclaw-workspace/Neo-VM/projects/villa-wt-afv-seam-c3d9")
    / xd.CATALOG
)
MAIN = "7e6b82164d014ed485aa027011f31070923fc0a9"
REGISTRATION = (
    xd.ROOT / "docs/preregistration/2026-11-09_afv_generator_cross_block_duplicates.md"
)
EVIDENCE = (
    xd.ROOT
    / "reports/evidence/afv_generator_cross_block_duplicates_dev_2026-11-09.json"
)


def flat(path: Path) -> str:
    return " ".join(path.read_text().split())


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%"


def patch_lines(sign: str, name: str) -> list[str]:
    out, current = [], None
    for line in xd.PATCH.read_text().splitlines():
        if line.startswith("diff --git"):
            current = line.rsplit("/", 1)[1]
        elif (
            current == name and line.startswith(sign) and not line.startswith(sign * 3)
        ):
            out.append(line[1:])
    return out


def test_the_gate_s_strings_are_the_patch_s_catalogue_lines():
    added, removed = patch_lines("+", "catalog.py"), patch_lines("-", "catalog.py")
    assert xd.CALL.splitlines() == [
        line
        for line in added
        if "cross_block_duplicate(sp,lp)" in line or "ov.MAX_P90" in line
    ]
    assert xd.COMMENT[0].splitlines() == [
        line
        for line in added
        if line.strip().startswith("# Other") or "only the two tests" in line
    ]
    assert removed == xd.COMMENT[1].splitlines()
    assert "def cross_block_duplicate(a, b):" in added
    assert (
        sum(
            1
            for line in patch_lines("+", "test_stitch.py")
            if line.startswith("def test_")
        )
        == 2
    )


def test_the_catalogue_gate_accepts_the_patch_and_nothing_more(tmp_path):
    if not (VILLA / ".git").exists() or not PATCHED.exists():
        pytest.skip("the villa clone or the patched worktree is not on this machine")
    assert xd.catalog_problems(VILLA, MAIN, PATCHED) == []
    text = PATCHED.read_text()
    for mutant in (text.replace("GAP_CAP = 30.", "GAP_CAP = 31."), text.replace(xd.CALL, ""),
                   text.replace("match['contained'] == 'B'", "match['contained'] == 'A'") + "\n"):  # fmt: skip
        p = tmp_path / "catalog.py"
        p.write_text(mutant)
        assert xd.catalog_problems(VILLA, MAIN, p), mutant[:40]


def row(erl4: float, merges: int, dup: float) -> dict:
    return {
        "tol2": {"erl_merge_penalized": 10.0, "merges": merges},
        "tol4": {"erl_merge_penalized": erl4, "merges": merges},
        "duplicated_share": dup,
    }


def results(gains4, merges=(10, 10), dups=(0.10, 0.05), problems=()):
    return {
        c: {
            "identity_problems": list(problems),
            "rows": {
                "trim": row(30.0, merges[0], dups[0]),
                "trim+dup": row(30.0 * (1 + g), merges[1], dups[1]),
            },
        }
        for c, g in zip(bs.HELD_OUT, gains4, strict=True)
    }


def test_the_decision_rule():
    up = [0.05] * 8
    assert xd.verdict(results(up))["decision"] == "SUPPORTED"
    assert (
        xd.verdict(results([0.05] * 5 + [-0.01] * 3))["decision"] == "NOT_SUPPORTED"
    )  # P1: 5 of 8
    assert (
        xd.verdict(results([0.05] * 6 + [-0.01] * 2))["decision"] == "SUPPORTED"
    )  # 6 of 8 holds
    assert (
        xd.verdict(results(up, merges=(10, 11)))["decision"] == "NOT_SUPPORTED"
    )  # P3: 1.10 x
    assert (
        xd.verdict(results(up, merges=(20, 21)))["decision"] == "SUPPORTED"
    )  # 1.05 x holds
    assert xd.verdict(results([0.02] * 8))["decision"] == "PARTIAL"  # P2: median 0.02
    assert (
        xd.verdict(results(up, dups=(0.10, 0.08)))["decision"] == "PARTIAL"
    )  # P4: 0.8 x
    assert xd.verdict(results(up, problems=["x"]))["decision"] == "NO_VERDICT"
    v = xd.verdict(results(up))
    assert v["P1_tol4_up"] == [8, True] and v["P3_merges_tol2"] == [[80, 80], True]


def test_the_registration_is_the_rule_and_names_its_inputs():
    t = flat(REGISTRATION)
    assert "`scripts/afv_generator_cross_block_duplicates.py`" in t
    assert (
        "`repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`"
        in t
    )
    assert (
        "higher with the change on at least 6 of 8 cubes" in t and "at least 0.03" in t
    )
    assert "at most 1.05 times the trim's" in t and "at most 0.7 times the trim's" in t
    assert f"`{xd.DIAGNOSED}`" in t and xd.DIAGNOSED in bs.HELD_OUT
    for name in ("NO_VERDICT", "NOT_SUPPORTED", "PARTIAL", "SUPPORTED"):
        assert f"`{name}`" in t


def test_the_registration_s_figures_are_its_evidence():
    e, t = json.loads(EVIDENCE.read_text()), flat(REGISTRATION)
    rows = e["dev_screen"]["rows"]
    assert len(rows) == 8 and not set(rows) & set(bs.HELD_OUT)
    assert all(
        r["E16P"] | {"loose_suppressed": 0} == r["E16L"] | {"loose_suppressed": 0}
        for r in rows.values()
    )
    for tol, tau in (("tol4", "4"), ("tol2", "2")):
        g = [
            r["E16P"][f"{tol}_erl_merge_penalized"]
            / r["E16"][f"{tol}_erl_merge_penalized"]
            - 1
            for r in rows.values()
        ]
        assert all(x > 0 for x in g)
        assert (
            f"{pct(statistics.median(g))} at τ = {tau} ({pct(min(g))} to {pct(max(g))})"
            in t
        )
    for tol, tau in (("tol2", "2"), ("tol4", "4")):
        m = [sum(r[v][f"{tol}_merges"] for r in rows.values()) for v in ("E16", "E16P")]
        assert f"{m[0]} → {m[1]} at τ = {tau}" in t
    d = [
        statistics.median(r[v]["dup_share"] for r in rows.values())
        for v in ("E16", "E16P")
    ]
    assert f"The median duplicated share fell {d[0]:.3f} → {d[1]:.3f}" in t
    x = {
        k: [sum(r[v][f"x_{k}"] for r in rows.values()) for v in ("E16", "E16P")]
        for k in ("whole", "broken", "lost")
    }
    assert (f"whole ones rose {x['whole'][0]} → {x['whole'][1]}, broken fell {x['broken'][0]} → {x['broken'][1]} and "
            f"lost fell {x['lost'][0]} → {x['lost'][1]}") in t  # fmt: skip
    z = e["zone_residue"]
    band = z["where"]["patched"]["by_face_distance"]
    assert (
        f"{100 * sum(b['share_of_all_dup'] for b in band[:4]):.1f}% of the doubled length lies within 32 voxels"
        in t
    )
    assert (
        f"Beyond 32 voxels the share is {z['where']['patched']['far_from_faces']['dup_share']}"
        in t
    )
    inner = [b["dup_share_in_bin"] for b in band[:3]]
    assert (
        f"{100 * min(inner):.0f}–{100 * max(inner):.0f}% of the length is doubled" in t
    )
    w = z["why_kept"]["patched"]
    assert f"{w['pairs']} pairs share at least 4 voxels" in t
    verdicts = w["strict_duplicate_verdict"]
    bbox = verdicts["short's bbox not inside long's"]
    assert (
        f"fails {verdicts['median > 0.20']} pairs" in t
        and f"the bounding box fails {bbox}" in t
    )
    assert (
        f"classifies {w['compare_kind']['duplicate']} of the pairs as duplicates and {w['compare_kind']['overlap']}"
        in t
    )
    k = z["what"]["patched"]
    assert (
        f"{100 * k['share_running_along_the_face']:.0f}% of them run along the face"
        in t
    )
    assert (
        f"a median {k['nearest_other_distance_p10_25_50_75_90'][2]:.2f} voxel away" in t
    )


def test_the_runner_parses_and_writes_the_record_once():
    runner = xd.ROOT / "repro/fibers/run_afv_generator_cross_block_duplicates.sh"
    subprocess.run(["bash", "-n", str(runner)], check=True)
    text = runner.read_text()
    assert (
        "reports/afv_generator_cross_block_duplicates.json" in text
        and "--patched-catalog" in text
    )
