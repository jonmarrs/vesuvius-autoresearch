import torch
from villa.vesuvius.src.vesuvius.models.build.primus_wrapper import PrimusNetwork
import os
os.environ['PYTHONPATH'] = "villa/vesuvius/src"

model = PrimusNetwork(
    input_channels=1,
    config_name='S',
    patch_embed_size=(8, 8, 8),
    input_shape=(16, 64, 64),
    targets={'ink': {'out_channels': 1}},
    decoder_depth=2,
    decoder_num_heads=12
)

chk = torch.load("checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth", map_location='cpu', weights_only=False)
state = chk.get('model_state_dict', chk)
print("Keys in state:", list(state.keys())[:5])

# The checkpoint was trained with DDP or LeJEPA. 
# In LeJEPA, the model has 'encoder', 'projector', 'predictor', etc.
# We only want the encoder. Let's see if the keys match.
res = model.shared_encoder.load_state_dict({k.replace('encoder.', ''): v for k, v in state.items() if k.startswith('encoder.')}, strict=False)
print("Load result:", res)
