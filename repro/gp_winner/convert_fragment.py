# repro/gp_winner/convert_fragment.py
"""Convert our uint16 ZSTD-compressed fragment layers into 8-bit, cv2-readable layers
in the winner's train_scrolls/<id>/ layout. uint16->uint8 via //256 (documented global
scale); the winner loader's clip(0,200) applies downstream. PIL reads the ZSTD source
(OpenCV cannot)."""
import argparse
import os
import shutil

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def convert_layer_u16_to_u8(arr):
    """uint16 -> uint8 by a global //256 scale (high byte)."""
    return (arr.astype(np.uint32) // 256).astype(np.uint8)


def convert_fragment(frag_id, src_root, dst_root, z_start=17, z_end=43):
    """Read src_root/<frag>/surface_volume/{i:02}.tif (uint16, PIL) for i in [z_start,z_end),
    write dst_root/<frag>/layers/{i:02}.tif as 8-bit cv2-readable, and copy the label+mask
    as <frag>_inklabels.png / <frag>_mask.png. Returns {str(i): {u16_max, u8_max, u8_mean}}."""
    src = os.path.join(src_root, frag_id)
    dst = os.path.join(dst_root, frag_id)
    os.makedirs(os.path.join(dst, "layers"), exist_ok=True)
    stats = {}
    for i in range(z_start, z_end):
        p = os.path.join(src, "surface_volume", f"{i:02d}.tif")
        a = np.array(Image.open(p))
        u8 = convert_layer_u16_to_u8(a)
        cv2.imwrite(os.path.join(dst, "layers", f"{i:02d}.tif"), u8)
        stats[str(i)] = {
            "u16_max": int(a.max()),
            "u8_max": int(u8.max()),
            "u8_mean": round(float(u8.mean()), 2),
        }
    shutil.copy(
        os.path.join(src, "inklabels.png"), os.path.join(dst, f"{frag_id}_inklabels.png")
    )
    shutil.copy(os.path.join(src, "mask.png"), os.path.join(dst, f"{frag_id}_mask.png"))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frag", required=True)
    ap.add_argument("--src-root", default="local_data")
    ap.add_argument("--dst-root", default="villa/ink-detection/train_scrolls")
    args = ap.parse_args()
    stats = convert_fragment(args.frag, args.src_root, args.dst_root)
    lo = min(s["u8_mean"] for s in stats.values())
    hi = max(s["u8_mean"] for s in stats.values())
    print(f"{args.frag}: converted {len(stats)} layers; u8_mean range [{lo}, {hi}]")
    for i, s in stats.items():
        print(f"  layer {i}: {s}")


if __name__ == "__main__":
    main()
