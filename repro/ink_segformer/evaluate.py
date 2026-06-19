# repro/ink_segformer/evaluate.py
import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

Image.MAX_IMAGE_PIXELS = None


def evaluate_fragment(prob, ink_png, mask_png):
    """Pixel AUC + best-Fβ(0.5) over masked pixels. Returns a dict."""
    ink = (np.array(Image.open(ink_png).convert("L")) > 127).astype(int)
    mask = np.array(Image.open(mask_png).convert("L")) > 127
    p, y = prob[mask].ravel(), ink[mask].ravel()
    auc = float(roc_auc_score(y, p)) if y.min() != y.max() else 0.5
    best_f, best_t = 0.0, 0.5
    for t in np.linspace(0.1, 0.9, 17):
        pred = (p > t).astype(int)
        tp = int((pred & y).sum())
        fp = int((pred & (1 - y)).sum())
        fn = int(((1 - pred) & y).sum())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        b2 = 0.25
        f = (1 + b2) * prec * rec / (b2 * prec + rec) if (b2 * prec + rec) else 0.0
        if f > best_f:
            best_f, best_t = f, float(t)
    return {"pixel_auc": auc, "fbeta0.5": best_f, "threshold": best_t}


def save_ink_png(prob, out_path, threshold=None):
    """Save the probability heatmap (and a thresholded version) as PNGs for visual
    legibility inspection."""
    Image.fromarray((np.clip(prob, 0, 1) * 255).astype(np.uint8)).save(out_path)
    if threshold is not None:
        Image.fromarray(((prob > threshold) * 255).astype(np.uint8)).save(
            out_path.replace(".png", f"_thr{threshold:.2f}.png")
        )
