import unittest

import torch

from scripts.betti_loss_module import BettiLoss


class TestBettiLoss(unittest.TestCase):
    def test_betti_loss_interface(self):
        loss_fn = BettiLoss(weight=1.0)

        # BettiLoss expects (B, 1, Z, H, W)
        pred = torch.sigmoid(torch.randn(1, 1, 8, 16, 16))
        target = (torch.randn(1, 1, 8, 16, 16) > 0).float()

        loss = loss_fn(pred, target)

        self.assertIsInstance(loss, torch.Tensor)
        self.assertEqual(loss.item(), 0.0)  # Currently mocked to 0.0
        self.assertTrue(loss.requires_grad)
        self.assertEqual(loss.shape, torch.Size([]))


if __name__ == "__main__":
    unittest.main()
