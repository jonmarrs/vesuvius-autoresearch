with open("train.py") as f:
    content = f.read()

# Replace TrainConfig
new_config = """@dataclass
class TrainConfig:
    # Full URI for Scroll 1 (PHerc0139) - Training
    uri: str = 's3://vesuvius-challenge-open-data/PHerc0139/volumes/20260102150214-2.399um-0.2m-78keV-masked.zarr/0/'
    # Full URI for Scroll 5 (PHerc0172) - Validation
    val_uri: str = 's3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/'

    batch_size: int = 2 # Minimum to avoid OOM
    patch_size: int = 64
    num_layers: int = 12

    lr: float = 3e-4
    time_budget: int = 300 # 5 minutes for rapid research iteration

# ---------------------------------------------------------------------------
# Training Loop
# ---------------------------------------------------------------------------

def compute_dice_loss(pred, target, smooth=1e-5):
    pred = torch.sigmoid(pred)
    intersection = (pred * target).sum(dim=(2, 3, 4))
    union = pred.sum(dim=(2, 3, 4)) + target.sum(dim=(2, 3, 4))
    dice = (2. * intersection + smooth) / (union + smooth)
    return 1.0 - dice.mean()"""

import re

content = re.sub(
    r"@dataclass\nclass TrainConfig:.*?(?=\ndef train\()",
    new_config + "\n",
    content,
    flags=re.DOTALL,
)

# Replace data loaders
new_loaders = """    print(f"Initializing Vesuvius Autoresearch Training on {t_config.uri}...")
    sys.stdout.flush()

    # Initialize Loader (Streams from AWS)
    dataset = VesuviusS3Dataset(uri=t_config.uri, patch_size=t_config.patch_size, num_layers=t_config.num_layers)
    data_iter = iter(dataset)

    print(f"Initializing Validation Loader on {t_config.val_uri}...")
    val_dataset = VesuviusS3Dataset(uri=t_config.val_uri, patch_size=t_config.patch_size, num_layers=t_config.num_layers)
    val_data_iter = iter(val_dataset)"""

content = re.sub(
    r'    print\(f"Initializing Vesuvius Autoresearch Training on.*?data_iter = iter\(dataset\)',
    new_loaders,
    content,
    flags=re.DOTALL,
)

# Replace evaluation
new_eval = """    # Final Summary
    # Quick Validation on a separate chunk (Scroll 5)
    print("Evaluating val_bpb (1 - Dice) on validation chunk (PHerc. 0172)...")
    sys.stdout.flush()
    val_losses = []
    with torch.no_grad():
        for _ in range(5):
            val_x = next(val_data_iter).to(device).unsqueeze(0)

            # Use synthetic target for simplicity in baseline evaluation
            val_target = torch.zeros_like(val_x)
            for b in range(val_x.shape[0]):
                if np.random.rand() > 0.3:
                    h0, w0 = np.random.randint(0, t_config.patch_size // 2), np.random.randint(0, t_config.patch_size // 2)
                    z0 = np.random.randint(2, t_config.num_layers - 4)
                    val_target[b, :, z0:z0+2, h0:h0+16, w0:w0+16] = 1.0
                    val_x[b] = val_x[b] + val_target[b] * 0.4

            val_out, _, _, _, _, _ = model(val_x, return_fiber=True)
            loss_dice = compute_dice_loss(val_out, val_target)
            val_losses.append(loss_dice.item())

    val_bpb = np.mean(val_losses)"""

content = re.sub(
    r"    # Final Summary.*?val_bpb = np\.mean\(val_losses\)",
    new_eval,
    content,
    flags=re.DOTALL,
)

with open("train.py", "w") as f:
    f.write(content)
