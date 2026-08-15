"""Retirement must be one definition, and the training path must honour it.

Two separate defects motivate this file.

The concept existed only in `scripts/probe_labeled_segment_availability.py`, while the
pipeline that actually gates training (`gt_prep_fragment`) knew nothing about it. So
`20230702185753_y4000_x2500` — retired non-scoring 2026-08-14 — cleared the 48 px placement
gate at 46.6 px and came back `passed: true`, which is why `gt_finetune_prep.json` had to
ship a "do not run this" warning instead of a working regenerate command.

And a constant duplicated across two files is the shape of the bug that started all of this:
a second hardcoded `LEVEL0_SHAPE` in `gt_register.py` displaced the training labels for a
week after the first copy was fixed. One definition, imported by both.
"""

import ast
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from repro.sota_data.retirement import RETIRED_NON_SCORING, is_retired  # noqa: E402

PROBE = REPO_ROOT / "scripts" / "probe_labeled_segment_availability.py"


def test_the_retired_segment_is_the_one_that_clears_the_gate_and_is_still_unusable():
    assert is_retired("20230702185753")
    assert not is_retired("20231210121321")  # the flagship, 32.0 px, genuinely usable
    assert not is_retired(
        "20231005123336"
    )  # excluded by the gate at 55.1 px, not retired


def test_probe_imports_the_shared_definition_rather_than_redefining_it():
    """A second copy is how the LEVEL0_SHAPE bug survived a week past its own fix."""
    tree = ast.parse(PROBE.read_text())
    literal_assignments = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == "RETIRED_NON_SCORING" for t in n.targets
        )
    ]
    assert not literal_assignments, (
        "probe defines its own RETIRED_NON_SCORING; import it from "
        "repro.sota_data.retirement so there is one definition"
    )

    import probe_labeled_segment_availability as probe

    assert probe.RETIRED_NON_SCORING is RETIRED_NON_SCORING


def test_gt_prep_fragment_drops_a_retired_segment_before_touching_any_data(tmp_path):
    """The check must come first, or it cannot be tested and does not protect the pipeline.

    No mesh, no label and no network are available here. If `gt_prep_fragment` returns a
    clean refusal anyway, the retirement check ran before `_fetch` — which is the point:
    a gate that only fires after an expensive fetch is a gate nobody runs.
    """
    from repro.sota_data.gt_register import gt_prep_fragment

    info = gt_prep_fragment("20230702185753", 4000, 2500, 4096, str(tmp_path))

    assert info["passed"] is False
    assert info["retired"] is True
    assert "retired" in info["retirement_note"].lower()
    assert "2026-08-14" in info["retirement_note"]
    # It must not have silently reported a placement measurement it never made.
    assert info.get("placement_offset_level2_px") is None


def test_a_non_retired_segment_is_not_short_circuited(tmp_path):
    """Guard the inverse: the early return must not swallow every segment.

    Without this, an early return that fired unconditionally would satisfy every other test
    here while silently disabling the gate for all segments.

    Uses an id that is neither retired nor present on disk, so it exercises the branch
    deterministically: a real segment would either hit cached data (making the assertion
    depend on what happens to be downloaded) or spend ~40s re-registering it.
    """
    import pytest

    from repro.sota_data.gt_register import gt_prep_fragment

    with pytest.raises(Exception) as exc:
        gt_prep_fragment("99999999999999", 4000, 2500, 4096, str(tmp_path))
    assert "retired" not in str(exc.value).lower()
