"""docs/VILLA_DRAFT_volume_seed_heading.md's 2026-11-05 rebase onto villa main eab6108b9: the patch is the two measured
patches' change, its tests differ from theirs only where main's signatures moved, and the stubbed test record says what
the draft says it does."""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/VILLA_DRAFT_volume_seed_heading.md"
NEW = ROOT / "repro/fibers/villa_volume_seed_heading_eab6108b9.patch"
HEADING = ROOT / "repro/fibers/villa_volume_seed_heading.patch"
RESUME = ROOT / "repro/fibers/villa_volume_seed_resume.patch"
RECORD = ROOT / "reports/evidence/villa_volume_seed_heading_tests_eab6108b9_stubbed.txt"
RUNNER = ROOT / "repro/fibers/run_villa_seed_heading_tests_stubbed.sh"
STUB = ROOT / "repro/fibers/stub_native_villa.py"
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


def hunks(patch: Path) -> list[tuple[str, int, int, int, int, list[str]]]:
    """(file, old start, old count, new start, new count, body) for each hunk, from a git diff."""
    out, name = [], None
    for line in patch.read_text().splitlines():
        if line.startswith("diff --git "):
            name = line.split(" b/", 1)[1]
        elif m := re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line):
            out.append((name, *(int(g or 1) for g in m.groups()), []))
        elif out and line[:1] in " +-" and not line.startswith(("+++", "---")):
            out[-1][-1].append(line)
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


def test_each_hunk_header_counts_its_body():
    """git apply refuses a hunk whose header miscounts its lines, so the patch would not apply on any villa."""
    shift: dict[str, int] = {}
    for name, old_start, old, new_start, new, body in hunks(NEW):
        assert old == sum(x[:1] in " -" for x in body), (name, old_start)
        assert new == sum(x[:1] in " +" for x in body), (name, old_start)
        start = old_start + shift.get(name, 0) if old else 1
        assert new_start == start, (name, old_start)
        shift[name] = shift.get(name, 0) + new - old


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


def test_the_stub_stands_in_for_the_two_native_modules_only():
    code = f"""
import importlib.util, json, sys
sys.path.insert(0, {str(STUB.parent)!r})
import stub_native_villa as stub
import vc_reader, vc_object_store
from vc_reader import AnyReader
from vc_object_store.any_module import AnyStore
assert vc_reader.STUBBED_NATIVE and vc_object_store.STUBBED_NATIVE
AnyStore("x").open()(1).read()
AnyReader.any_class_attribute()
assert importlib.util.find_spec("vc_reader_extra") is None
assert not hasattr(json, "STUBBED_NATIVE")
print(" ".join(stub.STUBBED))
"""
    run = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)  # fmt: skip
    assert run.returncode == 0, run.stderr
    reader, store = run.stdout.split()
    assert f"the native `{reader}` and `{store}` replaced by stand-ins" in draft()


def test_the_runner_archives_villa_main_and_applies_this_patch():
    text = RUNNER.read_text()
    assert text.splitlines()[1:].count("set -euo pipefail") == 1
    assert re.search(r'^REF="\$\{REF:-([0-9a-f]{40})\}"$', text, re.M)[1] == VILLA_MAIN
    assert f'PATCH="$REPO/{NEW.relative_to(ROOT).as_posix()}"' in text
    assert '(cd "$W/after" && git apply "$PATCH")' in text
    assert f"-p {STUB.stem} " in text and f"repro/fibers/{STUB.name}" in text
    other = re.search(r'^OTHER="([^"]*)"$', text, re.M)[1].split()
    assert len(other) == 3 and "Villa's three other volume test files" in draft()


@pytest.mark.parametrize(
    "pytest_says, code",
    [
        ("", 1),  # no pytest in that Python: nothing ran
        ("1 failed, 11 passed in 0.1s\nFAILED t.py::t - boom", 1),
        ("12 passed, 1 error in 0.1s\nERROR t.py::t - boom", 1),
        ("12 passed in 0.1s", 0),
    ],
)
def test_the_runner_fails_closed(tmp_path, pytest_says, code):
    """The runner always writes its record, and exits 0 only when every side ran and the patched new tests passed."""
    # villa main as far as the patch reads it: each hunk's preimage at its line
    villa = tmp_path / "villa"
    lines: list[str] = []
    for name, old_start, _, _, _, body in hunks(NEW):
        if name == VOLUME:
            lines += ["#"] * (old_start - 1 - len(lines))
            lines += [x[1:] for x in body if x[:1] in " -"]
    (villa / VOLUME).parent.mkdir(parents=True)
    (villa / VOLUME).write_text("\n".join(lines) + "\n")
    (villa / TESTS).mkdir(parents=True)  # the runner copies the new tests into it
    (villa / TESTS / "conftest.py").touch()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    git = ["git", "-C", str(villa), "-c", "user.name=t", "-c", "user.email=t", "-c", "commit.gpgsign=false"]  # fmt: skip
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "villa"]):
        subprocess.run([*git, *args], check=True, capture_output=True, env=env)
    py = tmp_path / "python"
    py.write_text(f"#!/bin/sh\n[ \"$1\" = -m ] && {{ printf '%s\\n' {shlex.quote(pytest_says)}; exit 1; }}\necho Python\n")  # fmt: skip
    py.chmod(0o755)
    out = tmp_path / "record.txt"
    env.update(VILLA=str(villa), REF="HEAD", PY=str(py), OUT=str(out), TMPDIR=str(tmp_path))  # fmt: skip
    run = subprocess.run(["bash", str(RUNNER)], capture_output=True, text=True, env=env)  # fmt: skip
    assert (run.returncode, out.exists()) == (code, True), run.stderr
