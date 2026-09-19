"""The coverage auditor exists because two corrections in one day shared a cause:
data on disk exceeding what the analysis used, with nothing failing.

These tests pin the behaviour that makes it worth reading -- especially that it
does NOT cry wolf. Its first version reported 18 phantoms, all false positives,
and a guard with that rate is one people learn to ignore.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_arm_coverage import (  # noqa: E402
    arm_tags_in_code,
    arms_on_disk,
    audit,
    tag_of,
)


def _scored(root: Path, name: str) -> None:
    d = root / name / "ink_metric"
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(json.dumps({"summary": {"total_fg_pixels": 1}}))


def test_arms_on_disk_finds_only_scored_dirs(tmp_path):
    _scored(tmp_path, "outer_curbase_s1")
    (tmp_path / "outer_unscored_s1").mkdir()  # no ink_metric -> not an arm
    assert arms_on_disk(str(tmp_path)) == ["outer_curbase_s1"]


def test_tag_of_strips_the_directory_convention():
    assert tag_of("outer_curbase_s1") == "curbase_s1"
    assert tag_of("dup_armREPEAT") == "dup_armREPEAT"


def test_an_unreferenced_arm_is_an_orphan(tmp_path):
    _scored(tmp_path, "outer_ghostarm_s1")
    r = audit(str(tmp_path))
    assert [o["tag"] for o in r["orphans"]] == ["ghostarm_s1"]


def test_real_one_offs_are_never_orphans(tmp_path):
    """These three exist and ARE discussed in reports, so they land in `used`.
    The property that matters either way is that none is called an orphan."""
    for n in ("dup_armREPEAT", "probe_innerprob", "outer_curbase_s1rr"):
        _scored(tmp_path, n)
    r = audit(str(tmp_path))
    assert r["orphans"] == [], "a documented one-off was reported as an orphan"
    assert {o["tag"] for o in r["used"]} == {
        "dup_armREPEAT",
        "probe_innerprob",
        "curbase_s1rr",
    }


def test_an_unreferenced_one_off_family_member_is_excused_not_orphaned(tmp_path):
    """The EXPECTED_ONE_OFF branch proper: a `dup_`/`probe_` arm that no report
    happens to mention is still excused by its family, with the reason attached."""
    _scored(tmp_path, "dup_armNEVERMENTIONED")
    r = audit(str(tmp_path))
    assert r["orphans"] == []
    assert len(r["expected_one_off"]) == 1
    assert r["expected_one_off"][0]["note"], "an excused arm must carry its reason"


# --- the false-positive regression, which is the point of the AST rewrite -----


def test_a_tag_mentioned_only_in_a_COMMENT_is_not_a_phantom():
    """`anchor10cov_s1` appears in the real tree only inside comments explaining
    why it deliberately does not exist. Grepping flagged it; parsing must not."""
    src = '# renaming it to "anchor10cov_s1" would mean passing a pilot path\nX = 1\n'
    assert arm_tags_in_code(src) == set()


def test_a_tag_mentioned_only_in_a_DOCSTRING_is_not_a_phantom():
    src = '"""We do not have curbase_s42 and never will."""\nY = 2\n'
    assert arm_tags_in_code(src) == set()


def test_group_labels_and_prefixes_are_not_arm_tags():
    """All of these were false positives in the grep version."""
    src = 'A = ("curbase_", "nosame_", "curbase_d8c5f488a", "baselines", "boot090")\n'
    assert arm_tags_in_code(src) == set()


def test_a_real_tag_in_a_tuple_IS_found():
    src = 'ARMS = ("curbase_s4", "anchor10cov_pilot", "nosame_s1")\n'
    assert arm_tags_in_code(src) == {"curbase_s4", "anchor10cov_pilot", "nosame_s1"}


def test_syntax_error_does_not_crash_the_audit():
    assert arm_tags_in_code("def broken(:\n") == set()


# --- against the real tree ----------------------------------------------------


def test_the_real_repo_has_no_phantoms_and_no_orphans():
    """Regression: reverting to a grep-based scan reproduces 18 phantoms, and
    dropping curbase_s4..s9 from a group would reintroduce orphans."""
    so = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
    if not so.exists():
        pytest.skip("spiral_out not present on this machine")
    r = audit(str(so))
    # NOT asserting a fixed arm count: a legitimate new fit would block commits,
    # and the properties below are what actually matter.
    assert r["phantoms"] == [], (
        f"a script names arms that are not on disk: {r['phantoms']} -- an "
        f"analysis is running on fewer fits than its author believes"
    )
    assert r["orphans"] == [], (
        f"scored but used by nothing: {[o['tag'] for o in r['orphans']]} -- "
        f"either wire them into an analysis or document them in EXPECTED_ONE_OFF"
    )
    assert r["on_disk"] >= 56, "arms disappeared from spiral_out"
