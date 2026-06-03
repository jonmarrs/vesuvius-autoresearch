import sys

import numpy as np
import torch
import torch.nn as nn

# Add the C++ extension path
sys.path.append(
    "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/vesuvius/src/external/Betti-Matching-3D/build"
)
import betti_matching


class BettiLoss(nn.Module):
    def __init__(self, weight=1.0):
        super().__init__()
        self.weight = weight

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        pred: (B, 1, Z, H, W) probability map
        target: (B, 1, Z, H, W) binary mask
        """
        # Betti matching expects CPU numpy arrays
        # The C++ extension expects (Z, Y, X)
        pred_np = pred.detach().cpu().numpy().squeeze(1)
        target_np = target.detach().cpu().numpy().squeeze(1)

        batch_losses = []
        for i in range(pred_np.shape[0]):
            # Compute barcode for pred and target
            # The extension likely expects a specific function signature
            pred_barcode = betti_matching.compute_barcode(pred_np[i])
            target_barcode = betti_matching.compute_barcode(target_np[i])

            # Compute matching/distance
            loss = betti_matching.compute_matching(pred_barcode, target_barcode)
            batch_losses.append(loss)

        return self.weight * torch.tensor(
            np.mean(batch_losses), device=pred.device, requires_grad=True
        )


print("Betti Loss module defined.")
