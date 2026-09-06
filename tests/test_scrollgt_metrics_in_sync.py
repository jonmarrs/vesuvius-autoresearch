"""Tripwire: ScrollGT's metrics.py is a verbatim copy of the detector's.

ScrollGT is published separately (github.com/jonmarrs/scrollgt) and its
`src/scrollgt/metrics.py` carries the note "copied verbatim from
vesuvius-autoresearch ... Keep the two files in sync; the contract is the
product." Nothing enforced that.

It matters because the two are a scoring contract, not merely shared utility
code: the published calibration and negative results were produced with this
metric, and a change here that does not reach there (or vice versa) means a
public benchmark silently scores differently from the numbers it cites. That
failure is invisible — both files keep working.

The comparison deliberately ignores the module docstring, because ScrollGT's
legitimately differs (it adds the provenance note above). Everything else must
match exactly.

ScrollGT lives in a sibling repo that is absent on most machines, so this skips
rather than fails when it is not checked out.
"""

import ast
import os
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_DETECTOR = _REPO / "src" / "vesuvius_autoresearch" / "detector" / "metrics.py"
_DEFAULT_SCROLLGT = _REPO.parent / "scrollgt"
_SCROLLGT = Path(os.environ.get("SCROLLGT_REPO", _DEFAULT_SCROLLGT))
_SCROLLGT_METRICS = _SCROLLGT / "src" / "scrollgt" / "metrics.py"

requires_scrollgt = pytest.mark.skipif(
    not _SCROLLGT_METRICS.is_file(),
    reason=f"scrollgt checkout not present at {_SCROLLGT}",
)


def _code_without_module_docstring(path: Path) -> str:
    """Source of every top-level statement except a leading module docstring."""
    tree = ast.parse(path.read_text())
    body = tree.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return ast.unparse(ast.Module(body=body, type_ignores=[]))


def test_the_detector_metrics_module_exists():
    assert _DETECTOR.is_file(), f"detector metrics missing at {_DETECTOR}"


@requires_scrollgt
def test_scrollgt_metrics_match_the_detector_exactly():
    ours = _code_without_module_docstring(_DETECTOR)
    theirs = _code_without_module_docstring(_SCROLLGT_METRICS)
    assert ours == theirs, (
        "scrollgt/src/scrollgt/metrics.py has DRIFTED from "
        "src/vesuvius_autoresearch/detector/metrics.py.\n"
        "These are a scoring contract, not shared utility code: the published "
        "benchmark cites numbers produced by this metric, so drift means it "
        "silently scores differently from its own documentation.\n"
        "Re-copy the file (keeping ScrollGT's provenance docstring) and re-run "
        "the benchmark's published scores, or update both together deliberately."
    )


@requires_scrollgt
def test_both_expose_the_same_public_surface():
    """A rename would slip past a body-only comparison of the wrong shape."""

    def names(p):
        return sorted(
            n.name
            for n in ast.parse(p.read_text()).body
            if isinstance(n, ast.FunctionDef)
        )

    assert names(_DETECTOR) == names(_SCROLLGT_METRICS)


@requires_scrollgt
def test_the_docstring_is_allowed_to_differ():
    """Pins the one intended difference, so a future 'fix' does not delete
    ScrollGT's provenance note to make the files byte-identical."""
    theirs = ast.get_docstring(ast.parse(_SCROLLGT_METRICS.read_text())) or ""
    assert "copied verbatim from vesuvius-autoresearch" in theirs
    assert _DETECTOR.read_bytes() != _SCROLLGT_METRICS.read_bytes()
