import torch
from vesuvius_model import InkDetectorOptimized, VesuviusConfig
from train import ExperimentConfig
import json

with open('config_temp.json', 'r') as f:
    config_dict = json.load(f)

v_config = VesuviusConfig(
    patch_size=config_dict['patch_size'],
    num_layers=config_dict['num_layers'],
    batch_size=config_dict['batch_size'],
    base_feat=config_dict['base_feat'],
    num_blocks=config_dict['num_blocks'],
    num_heads=config_dict['num_heads'],
    dropout=config_dict['dropout'],
    architecture=config_dict['architecture']
)

model = InkDetectorOptimized(v_config)
x = torch.randn((8, 1, 32, 64, 64))
out = model(x)
print(f"Output type: {type(out)}")
if isinstance(out, tuple):
    print(f"Tuple length: {len(out)}")
    for i, o in enumerate(out):
        print(f"Element {i} shape: {o.shape}")
else:
    print(f"Output shape: {out.shape}")
