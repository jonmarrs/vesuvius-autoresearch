"""Does an ink model's CALIBRATION survive crossing to another scroll? Its ranking does.

This reproduces the headline of `reports/ink_calibration_does_not_transfer.md`.

THE POINT. Four of the six released `PHerc.1667-iteration-*` checkpoints read
held-out Scroll 1 ink at AUC 0.68 to 0.72, so their RANKING transfers. But the
same model fires on a median 18.7% of its home scroll and 72.5% of Scroll 1, a
3.9x shift with non-overlapping ranges. Ranking and calibration are different
properties and only the first survives the crossing.

WHY IT MATTERS. villa's open-problems doc asks whether we can tell "no ink" from
"no ink recovered yet". That is a THRESHOLD question, and the threshold is
exactly what fails to cross scrolls: a fixed 0.5 cut calls most of a new segment
ink even while the ordering stays informative.

VALIDATION BUILT IN. The home-scroll rate is checked against the number the model
card itself publishes: iteration-5's held-out preview fires on 26.3%. If this
script's home-scroll median lands far from that, the pipeline is wrong and the
Scroll 1 comparison means nothing. That check is what distinguishes this from
three earlier attempts that were void.

PREPROCESSING. `clip(x, 0, 200) / 255`, the Quick-start convention. The card
documents three mutually inconsistent conventions and only this one reproduces
published output; see `reports/ink_ablation_scale_bug.md`.

MUST RUN IN THE ISOLATED VENV, transformers pinned to 4.57.6. See
repro/ink_ablation/README.md.

Run:
    <ink_ablation>/.venv/bin/python scripts/measure_calibration_transfer.py --models <dir>
"""

import argparse

import numpy as np
import torch

HOME = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1667/segments/"
    "20260108140509-w011_20260108140509268_flatboi/surface-volumes/"
    "2.399um-0.22m-78keV-volume-20251217075048.zarr"
)
AWAY = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/"
    "20231210121321/surface-volumes/2.4um-0.22m-78keV-volume-20260411134726.zarr"
)
PUBLISHED_HELDOUT_RATE = 0.2627  # iteration-5's own preview_l_5.png
DEPTH, TILE, SIZE = 62, 256, 1024


def prep(t):
    return np.clip(t.astype(np.float32), 0.0, 200.0) / 255.0


def rates(model, url, fracs, dev):
    import fsspec
    import zarr

    a = zarr.open(fsspec.get_mapper(url), mode="r")["0"]
    lo = a.shape[0] // 2 - DEPTH // 2
    H, W = a.shape[1], a.shape[2]
    out = []
    for fy in fracs[0]:
        for fx in fracs[1]:
            y, x = int(H * fy), int(W * fx)
            if y + SIZE > H or x + SIZE > W:
                continue
            blk = np.asarray(a[lo : lo + DEPTH, y : y + SIZE, x : x + SIZE])
            ps = []
            with torch.no_grad():
                for yy in range(0, SIZE, TILE):
                    for xx in range(0, SIZE, TILE):
                        t = prep(blk[:, yy : yy + TILE, xx : xx + TILE])
                        o = model(torch.from_numpy(t)[None, None].to(dev))
                        o = o.logits if hasattr(o, "logits") else o
                        ps.append(
                            torch.sigmoid(torch.as_tensor(o))
                            .float()
                            .cpu()
                            .numpy()
                            .ravel()
                        )
            out.append((y, x, float((np.concatenate(ps) > 0.5).mean())))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--member", default="it5")
    args = ap.parse_args()

    from transformers import AutoModel

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = (
        AutoModel.from_pretrained(
            f"{args.models}/{args.member}", trust_remote_code=True
        )
        .eval()
        .to(dev)
    )
    fracs = ((0.3, 0.45, 0.6), (0.35, 0.55))

    print(f"{args.member}: fraction of pixels above 0.5, {SIZE}x{SIZE} regions\n")
    med = {}
    for label, url in (("home (PHerc1667)", HOME), ("held out (Scroll1)", AWAY)):
        rs = rates(m, url, fracs, dev)
        for y, x, r in rs:
            print(f"  {label:<20} y={y:6d} x={x:6d}   {r:.4f}")
        med[label] = float(np.median([r for _, _, r in rs]))
        print(f"  {'-> median':<20}{med[label]:>26.4f}\n")

    home, away = med["home (PHerc1667)"], med["held out (Scroll1)"]
    print(f"published held-out reference (model card): {PUBLISHED_HELDOUT_RATE:.4f}")
    ok = abs(home - PUBLISHED_HELDOUT_RATE) < 0.15
    print(
        f"home-scroll median vs that reference: {'consistent' if ok else 'INCONSISTENT'}"
    )
    if not ok:
        print(
            "  The pipeline does not reproduce the published home-scroll rate, so the"
        )
        print("  cross-scroll comparison below is not trustworthy. Fix that first.")
        return
    print(f"\ncalibration shift home -> held out: {away / max(home, 1e-9):.2f}x")
    print(
        "Ranking is a different property and does survive: the same members read Scroll 1"
    )
    print("ink at AUC 0.68 to 0.72. See reports/ink_calibration_does_not_transfer.md")


if __name__ == "__main__":
    main()
