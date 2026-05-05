import torch
import torch.nn as nn

from predict import load_compatible_state_dict


def test_load_compatible_state_dict_skips_mismatched_tensors():
    model = nn.Linear(2, 1)
    state = {
        "weight": torch.ones((1, 2)),
        "bias": torch.ones(3),
        "extra.weight": torch.ones(1),
    }

    skipped = load_compatible_state_dict(model, state)

    assert skipped == ["bias", "extra.weight"]
    torch.testing.assert_close(model.weight, torch.ones((1, 2)))
