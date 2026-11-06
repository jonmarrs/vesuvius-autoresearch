"""docs/VILLA_DRAFT_volume_splice.md: every figure from the polyline check's record and finding 105's, and the parts
that are the owner's left to the owner."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import neural_tracer_link_splice as ls  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/VILLA_DRAFT_volume_splice.md"
POLY = ROOT / "reports/evidence/neural_tracer_splice_polylines_2026-11-06.json"
F105 = ROOT / "reports/neural_tracer_link_splice.json"


def flat() -> str:
    return " ".join(DRAFT.read_text().split())


def test_the_table_is_the_polyline_record():
    d = json.loads(POLY.read_text())["per_cube"]
    text = DRAFT.read_text()
    for c in ls.HELD_OUT:
        r = d[c]
        a, b = r["tol2"], r["tol4"]
        row = (f"| {c} | {r['splices']:,} | {b['base']['erl_merge_penalized']:.2f} → {b['poly']['erl_merge_penalized']:.2f} | "
               f"{a['base']['erl_merge_penalized']:.2f} → {a['poly']['erl_merge_penalized']:.2f} | "
               f"{a['base']['merges']:,} → {a['poly']['merges']:,} | {a['base']['coverage']:.3f} → {a['poly']['coverage']:.3f} |")  # fmt: skip
        assert row in text, row


def test_the_summary_figures():
    s = json.loads(POLY.read_text())["summary"]["held_out"]
    v = json.loads(F105.read_text())["verdict"]
    t = flat()
    assert f"The median is +{round(100 * s['tol4']['median_gain_poly'])}% at tolerance 4, but only " \
           f"+{100 * s['tol2']['median_gain_poly']:.1f}% at tolerance 2" in t  # fmt: skip
    assert (
        s["tol2"]["cubes_gaining"] == s["tol4"]["cubes_gaining"] == 10
        and "rises on every cube at both" in t
    )
    m = s["tol2"]["merges"]
    assert f"{m['base']:,} → {m['poly']:,} summed at tolerance 2" in t
    assert (
        f"{100 * v['wrong_share_tol2']:.1f}% of the splices whose pieces both touch"
        in t
    )
    r = json.loads(POLY.read_text())["per_cube"]["s3_02994_02494_01994_512"]
    assert (
        f"{r['splices']} splices turn {r['pieces']:,} pieces into {r['fibers']:,} fibers"
        in t
    )


def test_the_owners_parts_are_left_to_the_owner_and_nothing_is_signed():
    text = DRAFT.read_text()
    assert text.startswith("# Draft:") and "**NOT POSTED.**" in text
    assert "- [ ] I personally verified" in text and "- [x]" not in text.lower()
    assert "[The owner's own words:" in text
    internal, postable = text.split("\n---\n", 1)
    assert "No AI-authorship markers" in internal
    assert not re.search(r"claude|generated with|co-authored|anthropic", postable, re.I)


def test_the_files_it_points_to_exist():
    for rel in re.findall(r"`((?:scripts|docs|reports)/[^`]+)`", DRAFT.read_text()):
        assert (ROOT / rel).exists(), rel
