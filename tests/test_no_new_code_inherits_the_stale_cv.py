"""A stale constant must not spread any further than it already has.

`OUTER_CV = 0.0421` was measured once, at df=3, on villa-spiral `6847063f`. It
then propagated by copy-paste into five analysis scripts, including one written
for CURRENT-code arms -- and that last copy is what made
`reports/decoupling_does_not_cleanly_reproduce.md` publish a bound three times
too loose. Nobody re-derived it; each script inherited it from the previous one.

That is the failure mode this guards. The existing five keep the constant so they
still reproduce the MDE their registrations promised, but each must SAY it is
superseded, and no sixth file may pick it up.

`scripts/measure_noise_floor.py` is the intended source for new work: it
recomputes the CV per tier from the fits themselves.
"""

import ast
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"

# The five that predate the measurement. Frozen: this list must never grow.
_LEGACY = {
    "analyse_gap_ink_arm.py",
    "analyse_patch_bootstrap.py",
    "analyse_stripmatch.py",
    "analyse_same_winding.py",
    "analyse_same_winding_current.py",
}
_MARKER = "SUPERSEDED CONSTANT"
# The file that documents the constant is allowed to name it.
_DOCUMENTING = {"measure_noise_floor.py"}


def _files_assigning(value: float) -> set[str]:
    """Files that ASSIGN this constant, not ones that merely mention it.

    A regex over the source also matches docstrings, and several scripts name
    0.0421 precisely to say they are NOT using it -- `analyse_anchor_ablation.py`
    explains that it takes the current tier's value instead, and
    `analyse_gap_contrast_exploratory.py` quotes it inside a results table. Those
    mentions are the documentation working, so the check has to be about binding
    the value, which is an AST question.
    """
    hits = set()
    for p in _SCRIPTS.glob("*.py"):
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                if node.value.value == value:
                    hits.add(p.name)
            # default arguments, e.g. `def mde(..., cv: float = OUTER_CV)`
            if isinstance(node, ast.arguments):
                for d in node.defaults:
                    if isinstance(d, ast.Constant) and d.value == value:
                        hits.add(p.name)
    return hits


def test_the_stale_cv_appears_only_where_it_is_allowed_to():
    allowed = _LEGACY | _DOCUMENTING
    found = _files_assigning(0.0421)
    new = found - allowed
    assert not new, (
        f"{sorted(new)} inherited OUTER_CV = 0.0421. It is a df=3 estimate from the "
        "SUPERSEDED tree. Take the CV for your tier from measure_noise_floor.py."
    )


@pytest.mark.parametrize("name", sorted(_LEGACY))
def test_every_legacy_copy_declares_itself_superseded(name):
    t = (_SCRIPTS / name).read_text()
    assert _MARKER in t, f"{name} carries 0.0421 without saying it is superseded"
    assert "measure_noise_floor" in t or "noise_floor_by_tier" in t, (
        f"{name} must point at where the right value comes from"
    )


def test_the_legacy_list_is_frozen():
    """If a new script legitimately needs the old constant -- to reproduce a
    published number -- adding it here should be a deliberate act with a reason,
    not a silent edit."""
    assert len(_LEGACY) == 5


def test_the_current_code_script_names_the_error_it_caused():
    """analyse_same_winding_current.py is the copy that did real damage: a pinned
    constant used on current-code arms. Its marker must say so, because the
    generic warning would not stop the same mistake."""
    t = (_SCRIPTS / "analyse_same_winding_current.py").read_text()
    assert "CURRENT-code study" in t
    assert "0.0125" in t


def test_new_analysis_scripts_use_the_measured_tier_value():
    """The anchor ablation is the first study registered after the measurement;
    it must not carry the old number."""
    assert "analyse_anchor_ablation.py" not in _files_assigning(0.0421)
    assert "analyse_anchor_ablation.py" in _files_assigning(0.0125)


def test_the_measurement_script_is_not_itself_hardcoding_a_cv_for_analysis():
    """measure_noise_floor.py may name 0.0421 to say what it replaces, but must
    compute its own figures."""
    t = (_SCRIPTS / "measure_noise_floor.py").read_text()
    assert "def pooled_cv" in t
    assert "PUBLISHED_PINNED_CV" in t, "the old value must be labelled, not used bare"


def test_a_mention_in_prose_is_not_treated_as_inheritance():
    """The guard must not fire on scripts that name the old value to disown it,
    or this test becomes something people route around."""
    assert "analyse_gap_contrast_exploratory.py" not in _files_assigning(0.0421)
