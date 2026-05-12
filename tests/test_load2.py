import torch
chk = torch.load("checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth", map_location='cpu', weights_only=False)
state = chk.get('model', chk)
print("Keys in state:", list(state.keys())[:10])
