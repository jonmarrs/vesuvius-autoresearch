import torch
from vesuvius_model import VesuviusTimeSformer, VesuviusConfig

config = VesuviusConfig(
    patch_size=64,
    num_layers=26,
    batch_size=4,
    base_feat=64,
    num_blocks=8,
    num_heads=6,
    dropout=0.1,
    in_channels=1
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = VesuviusTimeSformer(config).to(device)
x = torch.randn(4, 1, 26, 64, 64).to(device)
out = model(x)
print("Output shape:", out.shape)
