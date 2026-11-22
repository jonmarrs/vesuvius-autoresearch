"""Compare a rebuilt submission image with the published one, on the data panel only.

Usage: compare_image.py PUBLISHED.png PUBLISHED.json OURS.png OURS.json OUT.json

The panel is CT grey (R = G = B) dimmed, with ink drawn as a yellow tint (255, 235, 120), so R - B is
zero on bare CT and grows with the ink opacity. The CT layer is bit-identical between the two images
(checked separately), so every difference in the panel comes from the ink maps or their stretch.
"""

import json
import sys

import cv2
import numpy as np

TINT_SHOWN = (
    8  # R - B above this = ink visibly drawn (of a maximum of 135 at full opacity)
)


def panel(png_path: str, sidecar: dict) -> np.ndarray:
    image = cv2.imread(png_path, cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f"cannot read {png_path}")
    box = sidecar["outputs"]["image"]["data_panel"]
    crop = image[
        box["y"] : box["y"] + box["height"], box["x"] : box["x"] + box["width"]
    ]
    if crop.shape[:2] != (box["height"], box["width"]):
        raise SystemExit(f"panel of {png_path} is {crop.shape}, sidecar says {box}")
    return crop


def tint(crop: np.ndarray) -> np.ndarray:
    return np.clip(
        crop[..., 2].astype(np.int16) - crop[..., 0].astype(np.int16), 0, None
    )


def iou(a: np.ndarray, b: np.ndarray) -> float | None:
    union = int((a | b).sum())
    return round(float((a & b).sum()) / union, 4) if union else None


def pearson(a: np.ndarray, b: np.ndarray) -> float | None:
    a = a.astype(np.float64).ravel()
    b = b.astype(np.float64).ravel()
    if a.std() == 0 or b.std() == 0:
        return None
    return round(float(np.corrcoef(a, b)[0, 1]), 5)


def main() -> int:
    pub_png, pub_json, our_png, our_json, out_path = sys.argv[1:6]
    pub_side = json.load(open(pub_json))
    our_side = json.load(open(our_json))
    pub = panel(pub_png, pub_side)
    our = panel(our_png, our_side)
    if pub.shape != our.shape:
        raise SystemExit(f"panel shapes differ: {pub.shape} vs {our.shape}")

    diff = np.abs(pub.astype(np.int16) - our.astype(np.int16))
    tp, to = tint(pub), tint(our)
    sp, so = tp > TINT_SHOWN, to > TINT_SHOWN
    result: dict = {
        "published": pub_png,
        "ours": our_png,
        "panel_hw": list(pub.shape[:2]),
        "pixels_identical_fraction": round(float((diff.max(axis=2) == 0).mean()), 5),
        "abs_diff": {
            "mean": round(float(diff.mean()), 4),
            "p99": float(np.percentile(diff.max(axis=2), 99)),
            "max": int(diff.max()),
            "fraction_over_8": round(float((diff.max(axis=2) > 8).mean()), 5),
        },
        "ink_tint_pearson_r": pearson(tp, to),
        "ink_tint_pearson_r_where_either_shown": pearson(tp[sp | so], to[sp | so]),
        "ink_shown_fraction": {
            "published": round(float(sp.mean()), 4),
            "ours": round(float(so.mean()), 4),
        },
        "ink_shown_iou": iou(sp, so),
        "sidecar_ink_above_threshold_fraction": {
            "published": pub_side["checks"]["area_ink_above_threshold_fraction"],
            "ours": our_side["checks"]["area_ink_above_threshold_fraction"],
        },
        "normalisation": {
            name: {
                "published": {k: round(v[k], 5) for k in ("mean", "sd")},
                "ours": {
                    k: round(our_side["ink"]["normalisation"]["per_model"][name][k], 5)
                    for k in ("mean", "sd")
                },
            }
            for name, v in pub_side["ink"]["normalisation"]["per_model"].items()
        },
        "ensemble_stretch": {
            "published": pub_side["ink"]["normalisation"]["ensemble_stretch"],
            "ours": our_side["ink"]["normalisation"]["ensemble_stretch"],
        },
        "ct_stretch": {
            "published": pub_side["ct"]["stretch"],
            "ours": our_side["ct"]["stretch"],
        },
        "ink_map_sha256_match": {
            m["model"]: m["sha256"] == o["sha256"]
            for m, o in zip(
                pub_side["ink"]["maps"], our_side["ink"]["maps"], strict=True
            )
        },
    }
    # Control: the same comparison with our panel displaced, so a high r above cannot come from the
    # two images merely sharing papyrus-wide ink statistics.
    result["control_ours_shifted"] = {
        f"{shift}px": {
            "ink_tint_pearson_r": pearson(tp, np.roll(to, (shift, shift), axis=(0, 1))),
            "ink_shown_iou": iou(sp, np.roll(so, (shift, shift), axis=(0, 1))),
        }
        for shift in (16, 64, 256)
    }
    letters = []
    for letter in pub_side["letters"]["letters_area_px"]:
        x0, y0, x1, y1 = (int(round(v)) for v in letter["box"])
        a, b = sp[y0:y1, x0:x1], so[y0:y1, x0:x1]
        letters.append(
            {
                "id": letter["id"],
                "ink_shown_iou": iou(a, b),
                "ink_tint_pearson_r": pearson(tp[y0:y1, x0:x1], to[y0:y1, x0:x1]),
                "shown_fraction_published": round(float(a.mean()), 4),
                "shown_fraction_ours": round(float(b.mean()), 4),
            }
        )
    result["letter_boxes"] = letters
    with open(out_path, "w") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
