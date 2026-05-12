import torch
import torch.nn as nn

from scripts.swarm_voter import SwarmVoter


class TupleModel(nn.Module):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def forward(self, x, **kwargs):
        out = torch.ones_like(x[:, :, 0]) * self.value
        return out, out + 1


def test_swarm_voter_matches_output_device_and_dtype_for_tuple_outputs():
    x = torch.zeros((1, 1, 2, 4, 4), dtype=torch.float16)
    voter = SwarmVoter([TupleModel(1.0), TupleModel(3.0)], weights=[0.25, 0.75])

    out_a, out_b = voter(x)

    assert out_a.dtype == x.dtype
    assert out_b.dtype == x.dtype
    assert out_a.device == x.device
    assert torch.allclose(out_a.float(), torch.full_like(out_a.float(), 2.5))
    assert torch.allclose(out_b.float(), torch.full_like(out_b.float(), 3.5))
