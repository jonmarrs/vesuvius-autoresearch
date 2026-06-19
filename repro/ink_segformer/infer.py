# repro/ink_segformer/infer.py
import os
import sys

import numpy as np
import torch

_R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _R)

from PIL import Image

from repro.ink_segformer.dataset import compute_tile_origins, read_middle_layers


def predict_fragment(model, frag_dir, cfg, device, tta=True):
    """Sliding-window inference over a full fragment with overlap-averaging and
    flip/rot90 TTA. Returns a float32 probability map [H, W]."""
    vol = read_middle_layers(frag_dir, cfg.z_start, cfg.z_count)  # [D,H,W]
    mask = np.array(Image.open(os.path.join(frag_dir, "mask.png")).convert("L")) > 127
    H, W = mask.shape
    acc = np.zeros((H, W), np.float32)
    cnt = np.zeros((H, W), np.float32)
    t = cfg.tile
    model.eval()
    for y, x in compute_tile_origins(mask, t, cfg.stride, min_papyrus=0.0):
        chunk = (
            torch.from_numpy(vol[:, y : y + t, x : x + t])
            .unsqueeze(0)
            .unsqueeze(0)
            .float()
            .to(device)
        )
        views = [chunk]
        if tta:
            views += [torch.rot90(chunk, k, dims=(-2, -1)) for k in (1, 2, 3)]
            views.append(torch.flip(chunk, dims=(-1,)))
        preds = []
        with torch.no_grad():
            for i, v in enumerate(views):
                p = torch.sigmoid(model(v))
                if tta and 1 <= i <= 3:
                    p = torch.rot90(p, -i, dims=(-2, -1))
                elif tta and i == 4:
                    p = torch.flip(p, dims=(-1,))
                preds.append(p)
        p = torch.stack(preds).mean(0)[0, 0].cpu().numpy()
        acc[y : y + t, x : x + t] += p
        cnt[y : y + t, x : x + t] += 1.0
    prob = np.divide(acc, cnt, out=np.zeros_like(acc), where=cnt > 0)
    return prob * mask
