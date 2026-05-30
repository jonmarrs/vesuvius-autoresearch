import unittest

import numpy as np
import torch

from scripts.active_learning_sampler import (
    ActiveLearningSampler,
    calculate_entropy,
    identify_uncertain_patches,
)


class MockModel(torch.nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x, return_qc=False):
        # Return mock logits [B, 1, H, W]
        logits = torch.zeros(x.shape[0], 1, x.shape[3], x.shape[4])
        # High uncertainty in the middle (logits close to 0 -> prob close to 0.5)
        logits[:, :, 16:48, 16:48] = 0.01
        # Low uncertainty elsewhere
        logits[:, :, :16, :] = 10.0

        if return_qc:
            # Low confidence (high uncertainty) mock QC [B, 1]
            qc = torch.zeros(x.shape[0], 1)
            return logits, qc
        return logits


class TestActiveLearning(unittest.TestCase):
    def test_calculate_entropy(self):
        # p=0.5 -> max entropy
        p_max = torch.tensor([0.5])
        ent_max = calculate_entropy(p_max)

        # p=1.0 or 0.0 -> min entropy
        p_min = torch.tensor([0.0, 1.0])
        ent_min = calculate_entropy(p_min)

        self.assertGreater(ent_max.item(), ent_min[0].item())
        self.assertAlmostEqual(ent_min[0].item(), 0.0, places=5)

    def test_identify_uncertain_patches(self):
        probs = np.zeros((64, 64), dtype=np.float32)
        probs[16:48, 16:48] = 0.5  # High uncertainty region

        mask = identify_uncertain_patches(probs, threshold=0.5)

        self.assertEqual(mask.shape, (64, 64))
        self.assertEqual(mask[32, 32], 1.0)
        self.assertEqual(mask[0, 0], 0.0)

    def test_sampler_logic(self):
        model = MockModel()
        sampler = ActiveLearningSampler(model, device="cpu")

        # Create a mock dataloader
        class MockDataloader:
            def __init__(self):
                self.batch_size = 1

            def __iter__(self):
                # x: [B, 1, Z, H, W], labels, coords: [B, 3]
                for i in range(5):
                    yield (
                        torch.randn(1, 1, 8, 64, 64),
                        torch.zeros(1, 64, 64),
                        torch.tensor([[i, 0, 0]]),
                    )

        coords, scores = sampler.sample_uncertain_regions(MockDataloader(), n_samples=2)

        self.assertEqual(len(coords), 2)
        self.assertEqual(len(scores), 2)
        # Scores should be descending
        self.assertGreaterEqual(scores[0], scores[1])


if __name__ == "__main__":
    unittest.main()
