"""The scoring contract must stay identical across the two repos that publish it.

ScrollGT's `src/scrollgt/metrics.py` is a verbatim copy of this repo's
`detector/metrics.py`, and ScrollGT's README advertises that they are kept in sync,
calling the contract "the product". Nothing enforced it: the two could drift silently and
published baselines would stop being comparable to new scores without anyone noticing.

That is the same shape as the other defects found in 2026-08 (see
reports/detector/registration_offset_2026-08-07.md): a property everyone believed, measured
once, never re-checked. This test re-checks it.

Skips when the sibling checkout is absent, so ScrollGT's own CI is unaffected.
"""

import ast
import os
import textwrap

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
CANONICAL = os.path.join(
    HERE, "..", "src", "vesuvius_autoresearch", "detector", "metrics.py"
)
COPY = os.environ.get(
    "SCROLLGT_METRICS",
    os.path.join(HERE, "..", "..", "scrollgt", "src", "scrollgt", "metrics.py"),
)


def _normalise(path):
    """Module source with docstrings, comments and blank lines removed.

    Docstrings are excluded deliberately: the copy carries an extra provenance note, which
    is a legitimate difference. Everything that affects a NUMBER must match.
    """
    tree = ast.parse(open(path).read())
    for node in ast.walk(tree):
        if (
            isinstance(
                node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            )
            and ast.get_docstring(node) is not None
        ):
            node.body = node.body[1:]
    return ast.unparse(tree)


requires_copy = pytest.mark.skipif(
    not os.path.exists(COPY),
    reason="scrollgt checkout not found; set SCROLLGT_METRICS to enable",
)


@requires_copy
def test_scoring_contract_is_identical_in_both_repos():
    canonical, copy = _normalise(CANONICAL), _normalise(COPY)
    if canonical != copy:
        import difflib

        diff = "\n".join(
            difflib.unified_diff(
                canonical.splitlines(),
                copy.splitlines(),
                fromfile="vesuvius-autoresearch detector/metrics.py",
                tofile="scrollgt metrics.py",
                lineterm="",
            )
        )
        pytest.fail(
            "The scoring contract has DRIFTED between the two repos. Published ScrollGT "
            "baselines and any new score are no longer comparable until this is resolved. "
            "Sync the files (autoresearch is the source of truth), then re-run.\n\n"
            + diff
        )


@requires_copy
def test_both_expose_the_same_public_surface():
    """A renamed or added metric is drift even if the maths is untouched."""

    def public_defs(path):
        tree = ast.parse(open(path).read())
        return sorted(
            n.name
            for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")
        )

    assert public_defs(CANONICAL) == public_defs(COPY)


def test_the_canonical_file_is_where_this_test_thinks_it_is():
    """Guard against the skip silently hiding a moved source of truth."""
    assert os.path.exists(CANONICAL), (
        f"canonical metrics.py not found at {CANONICAL}; this test would pass vacuously"
    )
