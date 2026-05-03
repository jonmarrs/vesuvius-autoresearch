
import torch
import numpy as np
from vesuvius_loader import VesuviusLabeledDataset
from vesuvius_model import InkDetectorOptimized, VesuviusConfig
from train import ExperimentConfig

def debug_prediction():
    # Load last model
    chk = torch.load('last_model.pt', map_location='cpu', weights_only=False)
    config_dict = chk['config']
    # Reconstruct ExperimentConfig and VesuviusConfig
    exp_config = ExperimentConfig(**config_dict)
    model_config = VesuviusConfig(
        patch_size=exp_config.patch_size,
        num_layers=exp_config.num_layers,
        base_feat=exp_config.base_feat,
        num_blocks=exp_config.num_blocks,
        num_heads=exp_config.num_heads,
        dropout=exp_config.dropout,
        architecture=exp_config.architecture
    )
    
    model = InkDetectorOptimized(model_config)
    model.load_state_dict(chk['model_state_dict'])
    model.eval()
    
    # Load val dataset with require_ink=True
    uri = 'local_data/PHercParis2Fr143/surface_volume.zarr'
    labels = 'local_data/PHercParis2Fr143/inklabels.png'
    mask = 'local_data/PHercParis2Fr143/mask.png'
    ds = VesuviusLabeledDataset(uri, labels, mask, patch_size=exp_config.patch_size, num_layers=exp_config.num_layers+8, require_ink=True)
    
    x_raw, target = ds[0]
    x = x_raw[:, 4:4+exp_config.num_layers].unsqueeze(0) # [1, 1, 16, H, W]
    
    with torch.no_grad():
        out = model(x)
        if isinstance(out, tuple): out = out[0]
        prob = torch.sigmoid(out)
    
    print(f"Prediction stats: max={prob.max():.6f}, min={prob.min():.6f}, mean={prob.mean():.6f}")
    print(f"Target stats: max={target.max():.4f}, mean={target.mean():.4f}, sum={target.sum():.4f}")
    
    dice = ((2.0 * torch.sum(target * prob)) / (torch.sum(target) + torch.sum(prob) + 1e-12)).item()
    print(f"Soft Dice: {dice:.6f}")
    
    thresholded = (prob > 0.5).float()
    hard_dice = ((2.0 * torch.sum(target * thresholded)) / (torch.sum(target) + torch.sum(thresholded) + 1e-12)).item()
    print(f"Hard Dice (0.5 threshold): {hard_dice:.6f}")

if __name__ == "__main__":
    debug_prediction()
