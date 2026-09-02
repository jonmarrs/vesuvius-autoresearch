"""Tests for repro/spiral_render/serial_folds.patch.

The patch exists because the stock get_ink_metrics.py OOMs on an outer-winding
strip: three fold subprocesses each hold the whole 352M-px strip's logits and the
OOM killer takes one out with rc=-9. It is carried as a patch rather than a fork
so villa stays the source of truth, which means it rots silently the moment the
villa pin moves. That is what these pin.

The other thing worth pinning is that the patch is OPT-IN. Every measurement in
this work that predates it ran the stock path, so if applying the patch changed
the default path, previously reported numbers and future ones would come from
different code without anyone noticing.
"""

import os
import shutil
import subprocess
import tempfile

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATCH = os.path.join(_REPO, "repro", "spiral_render", "serial_folds.patch")
_VILLA = os.path.join(_REPO, "villa", "spiral-fitting", "get_ink_metrics.py")

requires_villa = pytest.mark.skipif(
    not os.path.exists(_VILLA),
    reason="villa submodule not checked out",
)


def _apply(strip=1):
    """Apply the patch to a throwaway copy of villa's file; return the result."""
    work = tempfile.mkdtemp()
    target_dir = os.path.join(work, "spiral-fitting")
    os.makedirs(target_dir)
    target = os.path.join(target_dir, "get_ink_metrics.py")
    shutil.copyfile(_VILLA, target)
    proc = subprocess.run(
        ["patch", f"-p{strip}", "--batch", "-i", _PATCH],
        cwd=work,
        capture_output=True,
        text=True,
    )
    return proc, target


def test_the_patch_file_is_present():
    """Without this the rest skip for the wrong reason."""
    assert os.path.exists(_PATCH), _PATCH


@requires_villa
def test_it_applies_cleanly_to_the_pinned_villa_file():
    """The whole point. A villa pin bump that touches this file must fail here
    rather than in the middle of a nine-hour measurement."""
    proc, _ = _apply()
    assert proc.returncode == 0, f"patch failed:\n{proc.stdout}\n{proc.stderr}"
    assert "FAILED" not in proc.stdout, proc.stdout
    assert "Hunk" not in proc.stderr or proc.returncode == 0


@requires_villa
def test_the_patched_file_still_compiles():
    """A patch can apply cleanly and still land syntactically broken python."""
    _, target = _apply()
    with open(target) as f:
        src = f.read()
    compile(src, target, "exec")


@requires_villa
def test_the_default_path_is_preserved_verbatim():
    """The stock ensemble line must survive the patch, so a run without the env
    var is the same computation every earlier measurement used."""
    _, target = _apply()
    with open(target) as f:
        patched = f.read()
    assert "avg = np.mean(probs, axis=0)" in patched


@requires_villa
@pytest.mark.parametrize(
    "env_value,expected", [(None, False), ("", False), ("0", False), ("1", True)]
)
def test_the_gate_reads_the_environment_and_defaults_off(env_value, expected):
    """The gate line is executed as the patched file defines it, under a cleaned
    environment, rather than asserted as a string. Only the literal "1" arms it."""
    _, target = _apply()
    with open(target) as f:
        gate_lines = [
            ln for ln in f.read().splitlines() if ln.startswith("SERIAL_FOLDS =")
        ]
    assert len(gate_lines) == 1, gate_lines

    clean = dict(os.environ)
    clean.pop("INK_METRIC_SERIAL_FOLDS", None)
    if env_value is not None:
        clean["INK_METRIC_SERIAL_FOLDS"] = env_value
    namespace = {"os": type("os_stub", (), {"environ": clean})}
    exec(gate_lines[0], namespace)
    assert namespace["SERIAL_FOLDS"] is expected


@requires_villa
def test_the_patch_adds_nothing_that_runs_with_the_gate_off():
    """Structural proof that the default path is untouched. Every added line must
    be one of: the gate definition, the `if SERIAL_FOLDS:`/`else:` scaffolding, a
    line indented inside the guarded branch, a comment -- or a line that already
    appears verbatim in the ORIGINAL file, which is the else-branch restoring it.

    Without the last clause this would pass vacuously, because the else branch
    re-adds the stock two lines as `+` lines."""
    with open(_VILLA) as f:
        original_lines = {ln.strip() for ln in f.read().splitlines() if ln.strip()}
    with open(_PATCH) as f:
        hunks = f.read().splitlines()

    added = [ln[1:] for ln in hunks if ln.startswith("+") and not ln.startswith("+++")]
    assert added, "patch adds nothing"

    gate_indent = None
    unguarded = []
    for line in added:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if stripped.startswith("SERIAL_FOLDS ="):
            continue
        if stripped == "if SERIAL_FOLDS:":
            gate_indent = indent
            continue
        if gate_indent is not None and indent > gate_indent:
            continue  # inside the guarded branch
        if stripped == "else:" and gate_indent is not None and indent == gate_indent:
            continue
        if stripped in original_lines:
            continue  # else-branch restoring stock code
        gate_indent = None
        unguarded.append(line)
    assert not unguarded, f"added lines that run with the gate off: {unguarded}"
