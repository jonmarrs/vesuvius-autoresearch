"""docs/VILLA_DRAFT_volume_seed_heading.md's 2026-11-05 rebase onto villa main eab6108b9: the patch is the two measured
patches' change, its tests differ from theirs only where main's signatures moved, and the stubbed test record says what
the draft says it does."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/VILLA_DRAFT_volume_seed_heading.md"
NEW = ROOT / "repro/fibers/villa_volume_seed_heading_eab6108b9.patch"
HEADING = ROOT / "repro/fibers/villa_volume_seed_heading.patch"
RESUME = ROOT / "repro/fibers/villa_volume_seed_resume.patch"
RECORD = ROOT / "reports/evidence/villa_volume_seed_heading_tests_eab6108b9_stubbed.txt"
RUNNER = ROOT / "repro/fibers/run_villa_seed_heading_tests_stubbed.sh"
VILLA_MAIN = "eab6108b948d5cb622b25ac87c9b32d5664a1504"
TESTS = "vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/"
VOLUME = "vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume.py"


def files(patch: Path) -> dict[str, list[str]]:
    """Each file's changed lines ('+…'/'-…', in order), from a git diff."""
    out: dict[str, list[str]] = {}
    name = None
    for line in patch.read_text().splitlines():
        if line.startswith("diff --git "):
            name = line.split(" b/", 1)[1]
            out[name] = []
        elif name and line[:1] in "+-" and not line.startswith(("+++", "---")):
            out[name].append(line)
    return out


def section(text: str, title: str) -> list[str]:
    lines, keep = [], False
    for line in text.splitlines():
        if line.startswith("== "):
            keep = line == f"== {title}"
        elif keep:
            lines.append(line)
    return lines


def draft() -> str:
    return " ".join(DRAFT.read_text().split())


def test_volume_py_changes_exactly_as_the_two_measured_patches():
    new, heading, resume = files(NEW), files(HEADING), files(RESUME)
    assert sorted(new[VOLUME]) == sorted(heading[VOLUME] + resume[VOLUME])
    assert "-    if abs(h @ direction) < np.cos(np.radians(35)):" in new[VOLUME]


def test_the_tests_differ_only_where_mains_signatures_moved():
    new, heading, resume = files(NEW), files(HEADING), files(RESUME)
    h = TESTS + "test_volume_seed_heading.py"
    r = TESTS + "test_volume_seed_resume.py"
    assert set(new) == {VOLUME, h, r}
    swaps_h = {
        "lambda vol, xyz, family: axis": "lambda ct, spec, xyz, family: axis",
        "def unclear(vol, xyz, family):": "def unclear(ct, spec, xyz, family):",
    }
    swaps_r = {
        "SimpleNamespace(grid_scale=2, ct_zarr='fixed-ct')": "SimpleNamespace(grid_scale=2, input_scale=1, ct_zarr='fixed-ct')",
        "monkeypatch.setattr(volume.zarr, 'open',": "monkeypatch.setattr(volume, 'open_zarr',",
    }
    for name, old, swaps in ((h, heading, swaps_h), (r, resume, swaps_r)):
        expected = []
        for line in old[name]:
            for a, b in swaps.items():
                line = line.replace(a, b)
            expected.append(line)
        assert new[name] == expected, name
        assert new[name] != old[name], name


def test_the_draft_states_the_patch_size_and_base():
    added = sum(len([x for x in v if x.startswith("+")]) for v in files(NEW).values())
    removed = sum(len([x for x in v if x.startswith("-")]) for v in files(NEW).values())
    assert f"(+{added}/−{removed};" in draft()
    assert (added, removed) == (72, 5)
    assert f"villa main `{VILLA_MAIN[:9]}`" in draft()
    assert "`repro/fibers/villa_volume_seed_heading_eab6108b9.patch`" in draft()


def test_the_record_is_of_this_patch_at_villa_main():
    text = RECORD.read_text()
    assert f"villa {VILLA_MAIN} (" in text
    assert f"patch sha256 {hashlib.sha256(NEW.read_bytes()).hexdigest()}" in text
    assert "STUBBED" in text.splitlines()[0]
    assert (
        RUNNER.name in text and RECORD.relative_to(ROOT).as_posix() in DRAFT.read_text()
    )


def test_the_new_tests_fail_as_at_39a8cf3a_without_the_patch_and_pass_with_it():
    text = RECORD.read_text()
    before, after = (
        section(text, "before: the new tests"),
        section(text, "after: the new tests"),
    )
    failed = sorted(re.sub(r".*::", "", x) for x in before if x.startswith("FAILED"))
    heading = [
        f"test_seed_heading_is_the_ct_axis_signed_along_the_presence_direction[{d}]"
        for d in (36, 60, 89, 91, 120)
    ]
    resume = [
        f"test_resume_requires_the_same_seed_selection[{c}]"
        for c in ("None-False", "ct_axis_35deg_v1-False")
    ]
    assert failed == sorted(heading + resume)
    assert any(x.startswith("7 failed, 5 passed") for x in before)
    assert [x for x in after if not x.startswith("12 passed")] == []
    assert len(after) == 1
    t = draft()
    assert (
        "7 of the 12 new cases fail: the same five headings (36°, 60°, 89°, 91° and 120°)"
        in t
    )
    assert "With it, all 12 pass." in t


def test_villas_other_volume_tests_are_the_same_on_both_sides():
    text = RECORD.read_text()
    before = section(text, "before: villa's other volume tests")
    after = section(text, "after: villa's other volume tests")
    strip = [re.sub(r" in [0-9.]+s$", "", x) for x in before]
    assert strip == [re.sub(r" in [0-9.]+s$", "", x) for x in after]
    counts = next(x for x in before if "passed" in x)
    failed, passed = (
        int(n) for n in re.match(r"(\d+) failed, (\d+) passed", counts).groups()
    )
    assert failed == len([x for x in before if x.startswith("FAILED")])
    assert failed > passed  # "most of their cases fail on both sides"
    assert "same outcomes on both sides, failure for failure" in draft()
