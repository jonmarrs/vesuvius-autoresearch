import torch
import torch.nn as nn
from typing import List

class SwarmVoter(nn.Module):
    def __init__(self, models: List[nn.Module], weights: List[float] = None):
        super().__init__()
        self.models = nn.ModuleList(models)
        self.weights = weights if weights else [1.0 / len(models)] * len(models)
        self.register_buffer("weights_tensor", torch.tensor(self.weights))

    def forward(self, x: torch.Tensor, **kwargs):
        outputs = []
        for model in self.models:
            outputs.append(model(x, **kwargs))
            
        if isinstance(outputs[0], tuple):
            averaged = []
            for item_idx in range(len(outputs[0])):
                stacked = torch.stack([out[item_idx] for out in outputs], dim=0)
                shape = [len(self.weights)] + [1] * (stacked.dim() - 1)
                weights = self.weights_tensor.to(device=stacked.device, dtype=stacked.dtype).view(*shape)
                averaged.append(torch.sum(stacked * weights, dim=0))
            return tuple(averaged)

        stacked_outputs = torch.stack(outputs, dim=0)
        shape = [len(self.weights)] + [1] * (stacked_outputs.dim() - 1)
        weights = self.weights_tensor.to(device=stacked_outputs.device, dtype=stacked_outputs.dtype).view(*shape)
        return torch.sum(stacked_outputs * weights, dim=0)
