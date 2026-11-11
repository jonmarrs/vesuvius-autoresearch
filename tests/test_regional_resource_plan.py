"""Byte arithmetic for the persistent regional blend buffers needs no ML stack."""

import json

import pytest

from vesuvius_autoresearch.core.regional_resources import (
    MAX_ACCUMULATOR_BYTES,
    plan_regional_accumulators,
)


def test_exact_budget_is_accepted_and_one_byte_less_is_refused():
    plan = plan_regional_accumulators(13, 11, 1716)
    assert plan["accumulator_bytes"] == 1716
    assert plan["max_accumulator_bytes"] == 1716
    assert plan["accumulator_arrays"] == 3
    assert plan["accumulator_dtype"] == "float32"
    assert not plan["whole_process_peak_estimated"]
    json.dumps(plan, allow_nan=False)
    with pytest.raises(ValueError, match="accumulator.*1716.*1715"):
        plan_regional_accumulators(13, 11, 1715)


@pytest.mark.parametrize("field", ["width", "height", "max_accumulator_bytes"])
@pytest.mark.parametrize("value", [0, -1, True, 1.5, float("inf"), None])
def test_invalid_shape_or_budget_is_rejected(field, value):
    kwargs = {"width": 8, "height": 8, "max_accumulator_bytes": 1000}
    kwargs[field] = value
    with pytest.raises(ValueError, match=field):
        plan_regional_accumulators(**kwargs)


def test_large_shape_uses_integer_arithmetic_without_allocation():
    with pytest.raises(ValueError, match="max_accumulator_bytes"):
        plan_regional_accumulators(10**100, 10**100)
    assert MAX_ACCUMULATOR_BYTES == 512 * 1024**2
