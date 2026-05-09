import torch
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class AuxiliaryConfig:
    enabled: bool = False
    task_types: List[str] = field(default_factory=lambda: ["surface_normals", "structure_tensor"])
    weights: Dict[str, float] = field(default_factory=lambda: {"surface_normals": 0.05, "structure_tensor": 0.05})

class AuxiliaryManager:
    def __init__(self, aux_config: AuxiliaryConfig):
        self.aux_config = aux_config
        self._missing_warning_emitted = False

    def get_target_specs(self) -> Dict[str, Any]:
        """Maps our config to villa's expected target spec format."""
        if not self.aux_config.enabled:
            return {}
            
        specs = {}
        for task in self.aux_config.task_types:
            spec = {
                "task_type": task,
                "weight": self.aux_config.weights.get(task, 0.01),
                "source_target": "ink_2d"
            }
            specs[f"aux_{task}"] = spec
        return specs

    def compute_losses(self, outputs: Dict[str, torch.Tensor], targets: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Computes combined auxiliary loss."""
        if not self.aux_config.enabled:
            # Safely return 0.0 on the correct device if possible
            device = next(iter(outputs.values())).device if outputs else torch.device("cpu")
            return torch.tensor(0.0, device=device)
            
        device = next(iter(outputs.values())).device if outputs else torch.device("cpu")
        total_aux_loss = torch.tensor(0.0, device=device)
        matched_tasks = 0
        for task in self.aux_config.task_types:
            name = f"aux_{task}"
            if name in outputs and name in targets:
                matched_tasks += 1
                pred = outputs[name]
                target = targets[name]
                weight = self.aux_config.weights.get(task, 0.01)
                
                if task == "surface_normals":
                    loss = F.mse_loss(pred, target)
                else:
                    loss = F.mse_loss(pred, target)
                    
                total_aux_loss += weight * loss

        if matched_tasks == 0 and not self._missing_warning_emitted:
            print(
                "Warning: auxiliary tasks are enabled, but no matching auxiliary "
                f"outputs/targets were provided for {self.aux_config.task_types}; "
                "auxiliary loss is zero."
            )
            self._missing_warning_emitted = True
                
        return total_aux_loss
