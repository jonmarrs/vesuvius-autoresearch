"""Validated weighted means of compatible model tensors; no accuracy guarantee."""

from __future__ import annotations

import math
from numbers import Real

import torch
from torch import nn

MAX_MEMBERS = 64
FLOAT_DTYPES = {torch.float16, torch.bfloat16, torch.float32, torch.float64}


def normalized_weights(values, count):
    """Fixed relative weights, rescaled before summation to avoid overflow."""
    if not isinstance(values, (list, tuple)) or len(values) != count:
        raise ValueError("weights must contain one real number per model")
    numbers = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("weights must be finite nonnegative real numbers")
        try:
            number = float(value)
        except (ValueError, OverflowError) as exc:
            raise ValueError("weights must be finite nonnegative real numbers") from exc
        if not math.isfinite(number) or value < 0:
            raise ValueError("weights must be finite nonnegative real numbers")
        if value != 0 and number == 0:
            raise ValueError("nonzero weights must remain representable as float64")
        numbers.append(number)
    scale = max(numbers)
    if scale == 0:
        raise ValueError("at least one weight must be positive")
    scaled = [number / scale for number in numbers]
    total = math.fsum(scaled)
    result = tuple(number / total for number in scaled)
    if any(
        value > 0 and coefficient == 0
        for value, coefficient in zip(numbers, result, strict=True)
    ):
        raise ValueError("positive weight ratios must remain representable")
    return result


def validate_head(value, member, head):
    label = f"model {member} head {head}"
    if not isinstance(value, torch.Tensor):
        raise ValueError(f"{label} must be a floating tensor")
    if (
        value.dtype not in FLOAT_DTYPES
        or value.layout != torch.strided
        or value.device.type == "meta"
        or value.numel() == 0
    ):
        raise ValueError(f"{label} must be a nonempty dense real floating tensor")
    if not torch.isfinite(value).all().item():
        raise ValueError(f"{label} must contain only finite values")


class SwarmVoter(nn.Module):
    """A normalized weighted mean of raw, compatible tensors or flat tuples.

    Models, preprocessing, coordinate frame and head meaning must already match.
    No sigmoid, probability calibration, TTA or evaluation-mode switch is implied.
    Zero-weight members are disabled. Gradients flow through active members.
    """

    def __init__(self, models: list[nn.Module], weights: list[float] | None = None):
        super().__init__()
        if (
            not isinstance(models, (list, tuple, nn.ModuleList))
            or not 1 <= len(models) <= MAX_MEMBERS
            or any(not isinstance(model, nn.Module) for model in models)
        ):
            raise ValueError(f"models must contain 1..{MAX_MEMBERS} nn.Module members")
        coefficients = normalized_weights(
            [1.0] * len(models) if weights is None else weights, len(models)
        )
        self.models = nn.ModuleList(models)
        self.register_buffer(
            "weights_tensor", torch.tensor(coefficients, dtype=torch.float64)
        )

    @property
    def weights(self):
        """Immutable effective normalized weights from the registered buffer."""
        return self._coefficients()

    def _coefficients(self):
        weights = self.weights_tensor
        if (
            not 1 <= len(self.models) <= MAX_MEMBERS
            or not isinstance(weights, torch.Tensor)
            or weights.ndim != 1
            or weights.numel() != len(self.models)
            or weights.dtype not in FLOAT_DTYPES
            or weights.layout != torch.strided
            or weights.device.type == "meta"
            or weights.requires_grad
        ):
            raise ValueError("weight buffer must match the fixed model members")
        # The buffer is the sole state source, including after load_state_dict
        # or module dtype/device conversion. Validate before running any model.
        return normalized_weights(weights.detach().cpu().tolist(), len(self.models))

    def forward(self, x: torch.Tensor, **kwargs):
        coefficients = self._coefficients()
        totals = None
        references = None
        tuple_output = None
        for member, (model, coefficient) in enumerate(
            zip(self.models, coefficients, strict=True)
        ):
            if coefficient == 0:
                continue
            output = model(x, **kwargs)
            if isinstance(output, torch.Tensor):
                heads, is_tuple = (output,), False
            elif type(output) is tuple and output:
                heads, is_tuple = output, True
            else:
                raise ValueError(
                    f"model {member} must return a tensor or nonempty flat tuple"
                )
            if totals is not None and (
                is_tuple != tuple_output or len(heads) != len(totals)
            ):
                raise ValueError(f"model {member} output structure/head count differs")
            for head, value in enumerate(heads):
                validate_head(value, member, head)
            metadata = [(value.shape, value.dtype, value.device) for value in heads]
            if references is None:
                references, tuple_output = metadata, is_tuple
                totals = [
                    value.to(
                        torch.float32
                        if value.dtype in {torch.float16, torch.bfloat16}
                        else value.dtype
                    )
                    * coefficient
                    for value in heads
                ]
            else:
                if metadata != references:
                    raise ValueError(
                        f"model {member} head shape, dtype or device differs"
                    )
                totals = [
                    total + value.to(total.dtype) * coefficient
                    for total, value in zip(totals, heads, strict=True)
                ]
        # At least one coefficient is positive by construction/forward validation.
        result = tuple(
            total.to(dtype=reference[1])
            for total, reference in zip(totals, references, strict=True)
        )
        for head, value in enumerate(result):
            validate_head(value, "averaged output", head)
        return result if tuple_output else result[0]
