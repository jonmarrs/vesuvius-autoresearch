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
        # Return mock logits [B, 1, H, W]. Scaled by the input so that different
        # samples get different uncertainty scores: an earlier mock ignored `x`
        # entirely, which made every score identical and left the "scores are
        # descending" and "coords match the argmax" assertions unfalsifiable.
        scale = 1.0 + float(x.mean())
        logits = torch.zeros(x.shape[0], 1, x.shape[3], x.shape[4])
        # High uncertainty in the middle (logits close to 0 -> prob close to 0.5)
        logits[:, :, 16:48, 16:48] = 0.01 * scale
        # Low uncertainty elsewhere
        logits[:, :, :16, :] = 10.0 * scale

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

        class MockDataset:
            """The sampler recovers positions from `dataset.valid_coords`, so the
            mock needs one. The previous mock had no `.dataset` at all and the
            test failed with AttributeError before reaching any assertion."""

            def __init__(self):
                self.valid_coords = np.array([[i * 64, 0] for i in range(5)])

            def __len__(self):
                return len(self.valid_coords)

        class MockDataloader:
            def __init__(self):
                self.batch_size = 1
                self.dataset = MockDataset()

            def __len__(self):
                return len(self.dataset)

            def __iter__(self):
                # (volume, label, fiber target). The third element is the FIBER
                # target, not coordinates -- VesuviusLabeledDataset.__getitem__
                # returns (patch_vol, patch_label, patch_fiber). The old mock
                # yielded coordinates there, which described a dataset that does
                # not exist and would have hidden a real misuse of that slot.
                # Deterministic and distinct per sample: MockModel scales its
                # logits by the input mean, so sample i gets logits further
                # from zero as i grows, hence LOWER entropy and a lower
                # uncertainty score. Sample 0 is therefore the most uncertain
                # and sample 1 the second, which is what makes the coordinate
                # assertion below falsifiable by an off-by-one.
                for i in range(len(self.dataset)):
                    yield (
                        torch.full((1, 1, 8, 64, 64), float(i)),
                        torch.zeros(1, 64, 64),
                        torch.zeros(1, 64, 64),
                    )

        loader = MockDataloader()
        coords, scores = sampler.sample_uncertain_regions(loader, n_samples=2)

        self.assertEqual(len(coords), 2)
        self.assertEqual(len(scores), 2)
        # Scores should be descending
        self.assertGreater(scores[0], scores[1])

        # The coordinates must be the ones belonging to the two highest-scoring
        # samples, in order. Asserting only that each coord is SOME member of
        # valid_coords is a tautology -- production builds them by indexing that
        # array, so any off-by-one survives it, which is exactly the misindexing
        # this test exists to catch.
        np.testing.assert_array_equal(coords[0], loader.dataset.valid_coords[0])
        np.testing.assert_array_equal(coords[1], loader.dataset.valid_coords[1])

    def test_sampler_refuses_a_shuffled_loader(self):
        """The index arithmetic assumes dataset order. Under shuffling it still
        yields in-range indices, so a wrong answer would look like a right one."""
        model = MockModel()
        sampler = ActiveLearningSampler(model, device="cpu")

        dataset = torch.utils.data.TensorDataset(
            torch.randn(4, 1, 8, 64, 64), torch.zeros(4, 64, 64), torch.zeros(4, 64, 64)
        )
        loader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=True)
        with self.assertRaises(ValueError):
            sampler.sample_uncertain_regions(loader, n_samples=2)


if __name__ == "__main__":
    unittest.main()
