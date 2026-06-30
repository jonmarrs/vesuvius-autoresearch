"""Tiled full-segment inference: slide a 64px window, upsample each 4x4 logit grid 16x,
and average overlapping predictions with uniform weighting. Uniform (not Gaussian) blending
matches the proven train_ours.py validation accumulation and scores higher here
(held-out AUC 0.709 vs 0.700 Gaussian on the reference checkpoint). Patches are batched
through the model so a full segment scores in minutes rather than ~40 min."""
import numpy as np
import torch
import torch.nn.functional as F

from .data import read_image_mask
from .model import DetectorModel


def infer(cfg, checkpoint_path, fragment_id, model=None, batch_size=64):
    cfg.validate_window()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if model is None:
        # weights_only=False: our checkpoint embeds the LR scheduler (CosineAnnealingLR),
        # which PyTorch 2.6's weights_only=True default rejects. We trust our own ckpt.
        model = DetectorModel.load_from_checkpoint(
            checkpoint_path, cfg=cfg, pred_shape=(1, 1), weights_only=False)
    model = model.to(device).eval()
    images, label, frag_mask = read_image_mask(cfg, fragment_id)
    orig_h, orig_w = label.shape  # label is unpadded; frag_mask is padded to tile_size
    H, W = frag_mask.shape
    pred = np.zeros((H, W), np.float32)
    count = np.zeros((H, W), np.float32)
    sz = cfg.size
    ys = range(0, H - sz + 1, cfg.stride)
    xs = range(0, W - sz + 1, cfg.stride)

    buf_patches, buf_coords = [], []

    def _flush():
        if not buf_patches:
            return
        batch = torch.from_numpy(np.stack(buf_patches))[:, None].to(device)  # (b,1,C,sz,sz)
        logits = model(batch)  # (b,1,4,4) TimeSformer or (b,1,sz,sz) full-res
        ups = F.interpolate(logits, size=(sz, sz), mode="bilinear", align_corners=False)
        probs = torch.sigmoid(ups)[:, 0].cpu().numpy()  # (b,sz,sz)
        for (yy, xx), prob in zip(buf_coords, probs):
            pred[yy:yy + sz, xx:xx + sz] += prob  # uniform weight (1.0 per overlap)
            count[yy:yy + sz, xx:xx + sz] += 1.0
        buf_patches.clear()
        buf_coords.clear()

    with torch.no_grad():
        for y in ys:
            for x in xs:
                if np.any(frag_mask[y:y + sz, x:x + sz] == 0):
                    continue
                # Match training/valid A.Normalize(mean=0,std=1) => divide by 255.
                # Without this the model sees ~255x its trained input scale and the
                # held-out detector collapses to ~chance.
                patch = images[y:y + sz, x:x + sz, :].astype(np.float32) / 255.0
                buf_patches.append(patch.transpose(2, 0, 1))  # (C,sz,sz)
                buf_coords.append((y, x))
                if len(buf_patches) >= batch_size:
                    _flush()
        _flush()
    out = np.divide(pred, count, out=np.zeros_like(pred), where=count != 0)
    # Crop the padding back off so the prob map matches the fragment label shape.
    out = out[:orig_h, :orig_w]
    return np.clip(out, 0.0, 1.0)
