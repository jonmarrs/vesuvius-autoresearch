"""docs/VILLA_DRAFT_afv_generator_seam_trim.md: every figure from finding 106's record and the amended patch, and the
parts that are the owner's left to the owner."""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/VILLA_DRAFT_afv_generator_seam_trim.md"
RECORD = ROOT / "reports/afv_generator_block_seams.json"
PATCH = ROOT / "repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch"
EVIDENCE = ROOT / "reports/evidence/afv_generator_seam_diag_2026-11-07.json"
REGISTRATION = ROOT / "docs/preregistration/2026-11-06_afv_generator_block_seams.md"


def flat() -> str:
    return " ".join(DRAFT.read_text().split())


def rows() -> list[dict]:
    d = json.loads(RECORD.read_text())
    return [d["cubes"][c]["rows"] for c in bs.HELD_OUT]


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%"


def test_the_measurement_is_finding_106s_record():
    d, R, t = json.loads(RECORD.read_text()), rows(), flat()
    assert d["verdict"]["decision"] == "SUPPORTED" and "`SUPPORTED`" in t
    for tol in ("tol4", "tol2"):
        g = [bs.gain(r, "real", tol) for r in R]
        assert (
            f"{pct(statistics.median(g))} ({pct(min(g))} to {pct(max(g))}), up on {sum(x > 0 for x in g)} of 8"
            in t
        )
    m = [sum(r[f"real/{v}"]["tol2"]["merges"] for r in R) for v in ("main", "patched")]
    assert f"| merges, τ = 2, summed | {m[0]} | {m[1]} |" in t
    assert f"by a median {100 * statistics.median(bs.gain(r, 'real', 'tol4') for r in R):.1f}% at tolerance 4, with " \
           f"{100 * (1 - m[1] / m[0]):.1f}% fewer merges at tolerance 2" in t  # fmt: skip
    dup = [
        statistics.median(r[f"real/{v}"]["duplicated_share"] for r in R)
        for v in ("main", "patched")
    ]
    assert (
        f"| written length beside a same-family copy, median | {dup[0]:.3f} | {dup[1]:.3f} |"
        in t
    )
    assert f"a median {dup[0]:.3f} of the written length" in t
    assert f"at most {max(r['one/main']['duplicated_share'] for r in R):.4f}" in t
    w = {
        k: sum(r[k]["written"] for r in R)
        for k in ("one/main", "real/main", "real/patched")
    }
    assert (
        f"| fibers written (one block: {w['one/main']:,}) | {w['real/main']:,} | {w['real/patched']:,} |"
        in t
    )
    for v in ("main", "patched"):
        q = [
            r[f"real/{v}"]["tol4"]["erl_merge_penalized"]
            / r["one/main"]["tol4"]["erl_merge_penalized"]
            for r in R
        ]
        assert f"{min(q):.3f} to {max(q):.3f}" in t, v
    for r in json.loads(RECORD.read_text())["cubes"].values():
        s = r["settings"]
        assert (
            s["threshold"],
            s["max_join_angle"],
            s["min_length"],
            s["mirror"],
            s["extend"],
        ) == (60.0, 45.0, 100.0, False, False)


def test_what_it_costs_is_the_diagnosis():
    R, t = rows(), flat()
    e = json.loads(EVIDENCE.read_text())["totals"]["real"]
    x = {
        v: {
            k: sum(r[f"real/{v}"]["crossings"][k] for r in R)
            for k in ("whole", "broken", "lost")
        }
        for v in ("main", "patched")
    }
    n = sum(x["main"].values())
    assert (
        f"Of {n:,} places where a hand-traced fiber crosses a block face, {x['patched']['lost']} are lost with the "
        f"trim against {x['main']['lost']} on main. Whole ones rise from {x['main']['whole']} to "
        f"{x['patched']['whole']}, and broken ones fall from {x['main']['broken']} to {x['patched']['broken']}."
    ) in t
    worse = sum(e["worse"].values())
    join, neither = (
        e["worse_by_join"]["chained only in main"],
        e["worse_by_join"]["chained in neither"],
    )
    assert (
        f"Of the {worse} crossings worse with the trim, {join} are joins main made" in t
    )
    r = e["reasons_chained_only_in_main"]
    named = {"the overlap is shorter than 24 voxels": "the trimmed overlap is shorter than `MIN_OVERLAP`",
             "one copy lies along the other, but the catalogue keeps both": "fails the strict duplicate test, so both stay unlinked",
             "an overlap candidate made ambiguous by another at the same end": "makes the candidate ambiguous"}  # fmt: skip
    assert set(sorted(r, key=r.get, reverse=True)[:3]) == set(named)
    assert (
        max(r[k] for k in named) - min(r[k] for k in named) <= 2
        and "Three reasons come up most often, in about equal measure" in t
    )
    assert all(f"{v} ({r[k]})" in t for k, v in named.items())
    assert f"In {neither}, the copies were never chained" in t
    # Crossings the trim worsens can be chained only with it too: the count is of the better ones.
    better = sum(e["better"].values())
    assert (f"The changes run both ways: of the {better} crossings better with the trim, "
            f"{e['better_by_join']['chained only with the trim']} are chained only with it.") in t  # fmt: skip


def test_the_bent_end_figures_are_the_registration_s_screen():
    """The registration's in-sample screen measured the bent ends (its scratch was not committed); the draft quotes it."""
    reg, t = " ".join(REGISTRATION.read_text().split()), flat()
    for draft, registered in (
        ("a median 1.6 voxels from the spline fitted to the same field in one block, and 0.33 voxels at 2–4 voxels",
         "a median 1.6 voxels from the one-block spline of the same field, 0.33 at 2–4 voxels"),
        ("True overlaps (median 0.15–0.27 voxels apart) then measure 15.3–19.5° at their ends, and the overlap test "
         "allows 15°", "15° endpoint test for overlaps (true overlaps of median 0.15–0.27 voxels measured 15.3–19.5°"),
        ("fail the strict duplicate test (0.65 voxel)", "fail its strict duplicate test (at most 0.65 voxel)"),
    ):  # fmt: skip
        assert draft in t and registered in reg, draft


def test_what_ran_names_villa_main_only_for_the_modules_the_gate_compared():
    """The run imported the #1934 head's package; identity() compared only bs.IDENTICAL with villa main, per cube."""
    d, t = json.loads(RECORD.read_text()), flat()
    assert all(r["identity_problems"] == [] for r in d["cubes"].values())
    ran = t.split("**What ran:**", 1)[1].split("**Limits:**", 1)[0]
    used = re.findall(r"`(\w+)\.(\w+)`", ran.split(")", 1)[0])
    assert {a for a, _ in used} == {"predict", "splines", "extend", "cleanup"}
    unchecked = sorted(
        {
            a
            for a, b in used
            if f"{a}.py" not in bs.IDENTICAL and f"{a}/{b}.py" not in bs.IDENTICAL
        }
    )
    extend = [Path(m).stem for m in bs.IDENTICAL if m.startswith("extend/")]
    main = {r["settings"]["villa_main"][:9] for r in d["cubes"].values()}
    assert (
        "predict.py" in bs.IDENTICAL
        and unchecked == ["cleanup", "splines"]
        and len(main) == 1
    )
    assert (f"its `predict` and `extend` modules ({', '.join(f'`{m}`' for m in extend)}) were checked byte-identical "
            f"to villa main `{main.pop()}`'s. Its `cleanup` and `splines` modules were not compared with main's") in ran  # fmt: skip


def test_the_change_is_the_amended_patch():
    t = flat()
    counts: dict[str, list[int]] = {}
    name = None
    for line in PATCH.read_text().splitlines():
        if line.startswith("diff --git"):
            name = line.rsplit("/", 1)[1]
            counts[name] = [0, 0]
        elif line.startswith("+") and not line.startswith("+++"):
            counts[name][0] += 1
        elif line.startswith("-") and not line.startswith("---"):
            counts[name][1] += 1
    assert counts["stitch.py"] == [40, 0] and "`extend/stitch.py` +40" in t
    assert f"`cli.py` +{counts['cli.py'][0]}/−{counts['cli.py'][1]}" in t
    code = counts["stitch.py"][0] + counts["cli.py"][0]
    assert (
        f"the patch is {code} lines of code and comments in two files, plus {counts['test_stitch.py'][0]} lines"
        in t
    )
    assert "CUT_END = 16." in PATCH.read_text() and "`CUT_END = 16`" in t


def test_the_owners_parts_are_left_to_the_owner_and_nothing_is_signed():
    text = DRAFT.read_text()
    assert text.startswith("# Draft:") and "**NOT POSTED.**" in text
    assert "- [ ] I personally verified" in text and "- [x]" not in text.lower()
    assert "[The owner's own words:" in text
    internal, postable = text.split("\n---\n", 1)
    assert "No AI-authorship markers" in internal
    assert not re.search(r"claude|generated with|co-authored|anthropic", postable, re.I)
    assert "{{" not in text


def test_the_files_it_points_to_exist():
    for rel in re.findall(
        r"`((?:scripts|docs|reports|repro)/[^`]+)`", DRAFT.read_text()
    ):
        assert (ROOT / rel).exists(), rel
