"""Contracts for generic tensor voting and the retired title-search simulation."""

import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest
import torch
from torch import nn

from scripts.swarm_voter import SwarmVoter

REPO = Path(__file__).resolve().parents[1]


class Constant(nn.Module):
    def __init__(self, value, dtype=None):
        super().__init__()
        self.value = value
        self.dtype = dtype

    def forward(self, x, **kwargs):
        return torch.full_like(x, self.value, dtype=self.dtype or x.dtype)


class Heads(Constant):
    def __init__(self, value, count):
        super().__init__(value)
        self.count = count

    def forward(self, x, **kwargs):
        value = super().forward(x, **kwargs)
        return tuple(value + index for index in range(self.count))


class Forbidden(nn.Module):
    def forward(self, x, **kwargs):
        raise AssertionError("zero-weight member must not run")


def test_positive_weights_are_relative_and_normalized():
    voter = SwarmVoter([Constant(1), Constant(3)], weights=[1, 3])
    assert torch.equal(voter(torch.zeros(2)), torch.full((2,), 2.5))


@pytest.mark.parametrize(
    "weights", [[], [1], [0, 0], [-1, 2], [float("nan"), 1], [float("inf"), 1]]
)
def test_invalid_weight_vectors_fail_at_construction(weights):
    with pytest.raises(ValueError, match="weight"):
        SwarmVoter([Constant(1), Constant(3)], weights=weights)


def test_empty_ensemble_has_explicit_error():
    with pytest.raises(ValueError, match="model|member"):
        SwarmVoter([])


def test_caller_weight_list_cannot_corrupt_registered_voting():
    weights = [0.25, 0.75]
    voter = SwarmVoter([Constant(1), Constant(3)], weights=weights)
    weights.append(100)
    assert torch.equal(voter(torch.zeros(2)), torch.full((2,), 2.5))


def test_zero_weight_member_is_disabled():
    voter = SwarmVoter([Constant(7), Forbidden()], weights=[1, 0])
    assert torch.equal(voter(torch.zeros(2)), torch.full((2,), 7.0))


def test_extra_tuple_heads_are_not_silently_discarded():
    voter = SwarmVoter([Heads(1, 2), Heads(3, 3)])
    with pytest.raises(ValueError, match="tuple|head|structure"):
        voter(torch.zeros(2))


def test_nonfinite_member_output_fails():
    voter = SwarmVoter([Constant(1), Constant(float("nan"))])
    with pytest.raises(ValueError, match="finite"):
        voter(torch.zeros(2))


def test_integer_member_output_is_not_silently_truncated():
    voter = SwarmVoter([Constant(1, torch.int64), Constant(3, torch.int64)])
    with pytest.raises(ValueError, match="float|dtype"):
        voter(torch.zeros(2))


def test_half_precision_mean_accumulates_without_overflow():
    limit = torch.finfo(torch.float16).max
    voter = SwarmVoter([Constant(limit) for _ in range(3)])
    result = voter(torch.zeros(2, dtype=torch.float16))
    assert torch.isfinite(result).all()
    assert torch.equal(result, torch.full_like(result, limit))


def test_title_search_cannot_report_simulated_absence(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/search_first_title.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0
    assert "Scan complete" not in result.stdout
    assert "Found 0" not in result.stdout
    assert "not implemented" in result.stderr.lower()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("models", [None, [], (), [object()], "models"])
def test_invalid_model_members_fail_early(models):
    with pytest.raises(ValueError, match="model|member"):
        SwarmVoter(models)


def test_model_count_is_bounded_before_invocation():
    from scripts.swarm_voter import MAX_MEMBERS

    with pytest.raises(ValueError, match="model|member"):
        SwarmVoter([Forbidden() for _ in range(MAX_MEMBERS + 1)])


@pytest.mark.parametrize(
    "weights",
    [
        [True, 1],
        ["1", 1],
        [1 + 2j, 1],
        [10**5000, 1],
        [object(), 1],
        [torch.tensor(1), 1],
    ],
    ids=["bool", "string", "complex", "overflowing-int", "object", "tensor-scalar"],
)
def test_weight_types_are_explicit(weights):
    with pytest.raises(ValueError, match="weight"):
        SwarmVoter([Constant(1), Constant(3)], weights=weights)


def test_large_relative_weights_normalize_without_sum_overflow():
    voter = SwarmVoter([Constant(1), Constant(3)], weights=[1e308, 1e308])
    assert voter.weights == (0.5, 0.5)
    assert torch.equal(voter(torch.zeros(2)), torch.full((2,), 2.0))


def test_unrepresentable_positive_weight_is_not_silently_disabled():
    with pytest.raises(ValueError, match="representable"):
        SwarmVoter([Constant(1), Constant(3)], weights=[1e308, 1e-308])


@pytest.mark.parametrize("weight", [Fraction(1, 10**5000), Fraction(-1, 10**5000)])
def test_underflow_real_weight_is_not_silently_reinterpreted(weight):
    with pytest.raises(ValueError, match="weight|representable"):
        SwarmVoter([Constant(1), Constant(3)], weights=[weight, 1])


@pytest.mark.parametrize(
    "dtype", [torch.float16, torch.bfloat16, torch.float32, torch.float64]
)
def test_tensor_mean_preserves_supported_dtype_and_device(dtype):
    value = torch.zeros((2, 3), dtype=dtype)
    voter = SwarmVoter([Constant(-4), Constant(8)], weights=[1, 2])
    output = voter(value)
    assert output.dtype == dtype
    assert output.device == value.device
    assert output.shape == value.shape
    assert torch.equal(output, torch.full_like(value, 4))


class ShapedHeads(nn.Module):
    def __init__(self, value):
        super().__init__()
        self.value = nn.Parameter(torch.tensor(float(value)))

    def forward(self, x, **kwargs):
        return x + self.value, (x + self.value).mean().reshape(1)


def test_different_head_shapes_are_valid_when_members_match():
    x = torch.zeros((2, 3))
    voter = SwarmVoter([ShapedHeads(1), ShapedHeads(3)], weights=[1, 3])
    ink, scalar = voter(x)
    assert ink.shape == x.shape
    assert scalar.shape == (1,)
    assert torch.equal(ink, torch.full_like(x, 2.5))
    assert torch.equal(scalar, torch.tensor([2.5]))


def test_gradients_flow_with_normalized_coefficients():
    models = [ShapedHeads(1), ShapedHeads(3), ShapedHeads(100)]
    voter = SwarmVoter(models, weights=[1, 3, 0])
    ink, scalar = voter(torch.zeros((2, 3)))
    (ink.mean() + scalar.sum()).backward()
    assert models[0].value.grad.item() == pytest.approx(0.5)
    assert models[1].value.grad.item() == pytest.approx(1.5)
    assert models[2].value.grad is None


def test_state_dict_reload_is_the_single_weight_source():
    original = SwarmVoter([Constant(1), Constant(3)], weights=[3, 1])
    restored = SwarmVoter([Constant(1), Constant(3)], weights=[1, 1])
    restored.load_state_dict(original.state_dict())
    assert restored.weights == (0.75, 0.25)
    assert torch.equal(restored(torch.zeros(2)), torch.full((2,), 1.5))


def test_legacy_unnormalized_weight_buffer_is_interpreted_as_relative():
    voter = SwarmVoter([Constant(1), Constant(3)])
    state = voter.state_dict()
    state["weights_tensor"] = torch.tensor([1.0, 3.0])
    voter.load_state_dict(state)
    assert voter.weights == (0.25, 0.75)
    assert torch.equal(voter(torch.zeros(2)), torch.full((2,), 2.5))


@pytest.mark.parametrize(
    "buffer",
    [
        torch.tensor([float("nan"), 1]),
        torch.tensor([float("inf"), 1]),
        torch.tensor([-1.0, 2]),
        torch.tensor([0.0, 0]),
        torch.tensor([1.0]),
        torch.tensor([[1.0, 3]]),
        torch.tensor([1, 3]),
        torch.tensor([1.0, 3], requires_grad=True),
        torch.ones(2, device="meta"),
        torch.ones(2).to_sparse(),
    ],
    ids=[
        "nan",
        "inf",
        "negative",
        "zero",
        "length",
        "rank",
        "int",
        "trainable",
        "meta",
        "sparse",
    ],
)
def test_invalid_persisted_weights_fail_before_invocation(buffer):
    voter = SwarmVoter([Forbidden(), Forbidden()])
    voter.weights_tensor = buffer
    with pytest.raises(ValueError, match="weight"):
        voter(torch.zeros(2))


def test_mutating_model_count_is_rejected_before_invocation():
    voter = SwarmVoter([Forbidden()])
    voter.models.append(Forbidden())
    with pytest.raises(ValueError, match="weight|model"):
        voter(torch.zeros(2))


def test_module_conversion_and_mode_do_not_create_stale_weights():
    models = [ShapedHeads(1), ShapedHeads(3)]
    voter = SwarmVoter(models, weights=[1, 3]).half().eval()
    assert voter.weights == (0.25, 0.75)
    assert not voter.training and all(not model.training for model in models)
    ink, scalar = voter(torch.zeros((2, 3), dtype=torch.float16))
    assert ink.dtype == scalar.dtype == torch.float16
    assert torch.equal(ink, torch.full_like(ink, 2.5))
    voter.train()
    assert voter.training and all(model.training for model in models)


class Output(nn.Module):
    def __init__(self, output):
        super().__init__()
        self.output = output

    def forward(self, x, **kwargs):
        return self.output


@pytest.mark.parametrize(
    "output",
    [
        None,
        [],
        {},
        (),
        (torch.ones(2), None),
        (torch.ones(2), (torch.ones(2),)),
        torch.empty(0),
        torch.ones(2, dtype=torch.bool),
        torch.ones(2, dtype=torch.complex64),
        torch.ones(2, device="meta"),
        torch.ones(2).to_sparse(),
        torch.tensor([float("inf")]),
        torch.tensor([float("-inf")]),
    ],
    ids=[
        "none",
        "list",
        "dict",
        "empty-tuple",
        "none-head",
        "nested",
        "empty-tensor",
        "bool",
        "complex",
        "meta",
        "sparse",
        "inf",
        "negative-inf",
    ],
)
def test_invalid_active_output_has_explicit_error(output):
    with pytest.raises(ValueError, match="model|finite|tensor|tuple"):
        SwarmVoter([Output(output)])(torch.zeros(2))


@pytest.mark.parametrize(
    "other",
    [torch.ones(3), torch.ones(2, dtype=torch.float64), (torch.ones(2),)],
    ids=["shape", "dtype", "structure"],
)
def test_active_members_must_match_head_metadata(other):
    voter = SwarmVoter([Output(torch.ones(2)), Output(other)])
    with pytest.raises(ValueError, match="shape|dtype|structure"):
        voter(torch.zeros(2))


def test_zero_weight_first_member_does_not_define_output_structure():
    voter = SwarmVoter([Forbidden(), Heads(4, 2)], weights=[0, 1])
    first, second = voter(torch.zeros(2))
    assert torch.equal(first, torch.full((2,), 4.0))
    assert torch.equal(second, torch.full((2,), 5.0))


class WithKwargs(nn.Module):
    def __init__(self):
        super().__init__()
        self.seen = []

    def forward(self, x, *, offset):
        self.seen.append(offset)
        return x + offset


def test_kwargs_forwarded_once_and_inputs_remain_unchanged():
    members = [WithKwargs(), WithKwargs()]
    voter = SwarmVoter(members)
    x = torch.zeros(2, requires_grad=True)
    out = voter(x, offset=4)
    assert torch.equal(out, torch.full((2,), 4.0))
    assert torch.equal(x, torch.zeros(2))
    assert [model.seen for model in members] == [[4], [4]]
    out.sum().backward()
    assert torch.equal(x.grad, torch.ones(2))


def test_member_errors_propagate_without_replacing_output():
    with pytest.raises(AssertionError, match="must not run"):
        SwarmVoter([Forbidden()])(torch.zeros(2))


def test_retired_title_launcher_fails_even_with_existing_scroll_data(tmp_path):
    for scroll in (1, 2, 3):
        (tmp_path / "local_data" / f"Scroll{scroll}" / "div_100").mkdir(parents=True)
    prior = tmp_path / "predictions" / "keep.txt"
    prior.parent.mkdir()
    prior.write_text("prior artifact")
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/search_first_title.py"),
            "--scrolls",
            "1",
            "2",
            "3",
            "--batch_size",
            "16",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "not implemented" in result.stderr.lower()
    assert prior.read_text() == "prior artifact"
    assert (
        sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
        == before
    )


def test_retired_title_help_describes_scope_without_execution(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/search_first_title.py"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "no title detection is implemented" in result.stdout
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_cuda_voting_and_incompatible_output_devices():
    x = torch.zeros(2, device="cuda")
    voter = SwarmVoter([Constant(1), Constant(3)], weights=[1, 3]).cuda()
    assert voter(x).device == x.device
    assert torch.equal(voter(x), torch.full_like(x, 2.5))
    incompatible = SwarmVoter(
        [Output(torch.ones(2)), Output(torch.ones(2, device="cuda"))]
    )
    with pytest.raises(ValueError, match="device"):
        incompatible(torch.zeros(2))
