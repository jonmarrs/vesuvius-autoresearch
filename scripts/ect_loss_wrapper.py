import os
import sys

import torch
import torch.nn as nn

# Add villa to path to import ECT loss
sys.path.append(os.path.abspath("villa/vesuvius/src"))
from vesuvius.models.training.loss.ect_loss import ECTLoss


class ECTLossWrapper(nn.Module):
    def __init__(self, weight=0.05, num_directions=16):
        super().__init__()
        self.weight = weight
        # ECT loss can be computationally expensive, 16 directions is a good balance
        self.loss_fn = ECTLoss(num_directions=num_directions)

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        pred: (B, 1, Z, H, W)
        target: (B, 1, Z, H, W)
        """
        # ECT expects [B, 1, D, H, W]
        if pred.dim() == 4:
            pred = pred.unsqueeze(1)
        if target.dim() == 4:
            target = target.unsqueeze(1)

        return self.loss_fn(pred, target)


print("ECT Loss wrapper defined.")
