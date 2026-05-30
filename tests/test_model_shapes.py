import unittest

import torch

from vesuvius_model import InkDetectorOptimized, VesuviusConfig, VesuviusTimeSformer


class TestModelArchitectures(unittest.TestCase):
    def setUp(self):
        self.config = VesuviusConfig(
            patch_size=64,
            num_layers=16,
            batch_size=1,
            base_feat=32,
            num_blocks=2,
            num_heads=4,
            dropout=0.0,
        )

    def test_timesformer_output_shape(self):
        model = VesuviusTimeSformer(self.config)
        # Input: [B, C, Z, H, W]
        x = torch.randn(1, 1, 16, 64, 64)
        output = model(x)

        # Output should be [B, 1, H, W] for ink
        self.assertEqual(output.shape, (1, 1, 64, 64))

    def test_timesformer_multi_task(self):
        model = VesuviusTimeSformer(self.config)
        x = torch.randn(1, 1, 16, 64, 64)
        ink, fiber, qc = model(x, return_fiber=True, return_qc=True)

        self.assertEqual(ink.shape, (1, 1, 64, 64))
        self.assertEqual(fiber.shape, (1, 1, 16, 64, 64))
        self.assertEqual(qc.shape, (1, 1))

    def test_ink_detector_optimized_shapes(self):
        model = InkDetectorOptimized(self.config)
        x = torch.randn(1, 1, 16, 64, 64)
        ink = model(x)

        self.assertEqual(ink.shape, (1, 1, 64, 64))

    def test_ink_detector_optimized_multi_task(self):
        model = InkDetectorOptimized(self.config)
        x = torch.randn(1, 1, 16, 64, 64)
        # return_fiber, return_qc, return_proj, return_st
        ink, fiber, qc, proj, st = model(
            x, return_fiber=True, return_qc=True, return_proj=True, return_st=True
        )

        self.assertEqual(ink.shape, (1, 1, 64, 64))
        self.assertEqual(fiber.shape, (1, 1, 16, 64, 64))
        self.assertEqual(qc.shape, (1, 1))
        self.assertEqual(proj.shape, (1, 256))
        self.assertEqual(st.shape, (1, 6, 16, 64, 64))


if __name__ == "__main__":
    unittest.main()
