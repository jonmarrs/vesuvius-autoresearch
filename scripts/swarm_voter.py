import torch
import torch.nn as nn
from typing import List

class SwarmVoter(nn.Module):
    def __init__(self, models: List[nn.Module], weights: List[float] = None):
        super().__init__()
        self.models = nn.ModuleList(models)
        self.weights = weights if weights else [1.0 / len(models)] * len(models)
        self.register_buffer("weights_tensor", torch.tensor(self.weights))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        outputs = []
        for model in self.models:
            # Assumes models return logits
            outputs.append(model(x))
            
        # Weighted averaging of logits
        stacked_outputs = torch.stack(outputs, dim=0)
        weights = self.weights_tensor.view(-1, 1, 1, 1, 1)
        weighted_avg = torch.sum(stacked_outputs * weights, dim=0)
        
        return weighted_avg

print("SwarmVoter ensemble class defined.")
