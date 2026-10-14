"""A dataset for tests/test_loader_workers.py, importable by spawned workers."""

import numpy as np
import torch

from vesuvius_autoresearch.core.vesuvius_loader import _warn_limited


class IndexSeeded(torch.utils.data.Dataset):
    """Each item drawn from its own index, as the labeled datasets draw theirs;
    every third index counts a degraded-input warning."""

    def __init__(self, size=40):
        self.size = size

    def __len__(self):
        return self.size

    def __getitem__(self, idx):
        rng = np.random.RandomState(idx)
        x = torch.from_numpy(rng.rand(2, 4, 4).astype(np.float32))
        if idx % 3 == 0:
            _warn_limited("test_fallback", f"item {idx} fell back")
        return x, torch.tensor(idx), torch.zeros(1)
