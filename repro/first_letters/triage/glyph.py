"""Window triage of a band read's Studio maps with the PHerc. 306B team's glyph CNN and row score.

The PHerc. 306B First Letters team (Liam Warner and Nicola Bodill) found their line by scoring every window of a
band read: "the glyph CNN ranked a window on winding 74 first of 72 candidates". Their code is MIT and their weights
are CC BY-NC 4.0 (github.com/SirProdigle/pherc0306b-first-letters at COMMIT). This module re-implements, from that
commit, the inference path of `discovery/fl/scripts/glyph_win.py` (`x_glyph/common.py` a_from_z and
onsheet_windows, `x_glyph/evaluate.py` win_stack and the five-fold test-time augmentation, `x_glyph/train.py`
GlyphNet) and the row score of `discovery/fl/scripts/spectral_rows.py`. Nothing from their repository is imported or
run. The weights `discovery/x_glyph/models/gA.pt` are fetched at COMMIT, checked against WEIGHTS_SHA, and loaded
with `torch.load(weights_only=True)`.

Per winding, as glyph_win.py: windows WIN render pixels wide at a STEP stride, full height, skipped when less than
MIN_ON of the window is on the sheet. The map is z-scored over the sheet and drawn as their review overlay (a 1/3
area resample, a = clip((z - 0.9) / 1.8, 0, 1), resampled to 50 um). A window's glyph score is the largest CNN
logit over its 128-pixel (6.4 mm) sub-windows at a 16-pixel stride with at least 70% on the sheet. The row score is
spectral_rows.score of the window's z map (described: the team found it misses text with two rows).

What is ours: the map is a Studio probability, not their models' z map; the sheet is the render's surface layer
above zero (their window_score.py's `ct > 0`), not their quality tiles; and a last window ends at each winding's
end, which theirs leaves unscored.

    score  OUT.json MAPS RENDERS LIST --weights gA.pt --um UM   every window of every listed winding

Studio's maps and the weights stay on this machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = "SirProdigle/pherc0306b-first-letters"
COMMIT = "feabff6c54f95bd8e52a90e0a7a76881ee67d4cc"
WEIGHTS_PATH = "discovery/x_glyph/models/gA.pt"
WEIGHTS_SHA = "36ae0d6d9fdaac9d8681af75ec9be17e9317f7f77aa9422ea8ff8d09dd6f19ad"
UM50 = 50.0  # their common grid, um per pixel
# sub-windows: 6.4 mm, stride 0.8 mm, at least 70% on the sheet
GWIN, GSTEP, ONSHEET = 128, 16, 0.7
WIN, STEP = 2600, 1300  # tri_rank windows in render pixels
MIN_ON = 0.3  # glyph_win.py skips a window with less of it on the sheet
DOWN = 3  # a_from_z's area resample before the overlay


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def glyph_net(cin: int = 2, w: int = 24):
    """train.py's GlyphNet."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    def blk(i, o):
        return nn.Sequential(
            nn.Conv2d(i, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
            nn.Conv2d(o, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
        )  # fmt: skip

    class GlyphNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.b1, self.b2, self.b3, self.b4 = (
                blk(cin, w),
                blk(w, 2 * w),
                blk(2 * w, 4 * w),
                blk(4 * w, 8 * w),
            )
            self.head = nn.Sequential(
                nn.Linear(16 * w, 64),
                nn.ReLU(inplace=True),
                nn.Dropout(0.2),
                nn.Linear(64, 1),
            )

        def forward(self, a, m):
            x = torch.cat([a, m], 1)
            x = F.max_pool2d(self.b1(x), 2)
            x = F.max_pool2d(self.b2(x), 2)
            x = F.max_pool2d(self.b3(x), 2)
            x = self.b4(x)
            x = torch.cat([x.mean((2, 3)), x.amax((2, 3))], 1)
            return self.head(x).squeeze(1)

    return GlyphNet()


def load_model(path: Path, check: bool = True, device: str = "cpu"):
    import torch

    if check and sha256(path) != WEIGHTS_SHA:
        raise SystemExit(f"{path} is not gA.pt at {COMMIT}")
    ck = torch.load(path, map_location="cpu", weights_only=True)
    net = glyph_net(**ck.get("arch", {}))
    net.load_state_dict(ck["state"])
    return net.eval().to(device)


def starts(width: int) -> list[int]:
    """glyph_win.py's window starts, and one more at the winding's end when the last window stops short of it (ours:
    theirs never scores the last up to STEP - 1 pixels of a winding)."""
    xs = list(range(0, max(1, width - WIN + 1), STEP))
    if width > WIN and xs[-1] + WIN < width:
        xs.append(width - WIN)
    return xs


def resample(a: np.ndarray, um: float) -> np.ndarray:
    import cv2

    f = um / UM50
    h, w = a.shape
    size = (max(1, int(round(w * f))), max(1, int(round(h * f))))
    return cv2.resize(a.astype(np.float32), size, interpolation=cv2.INTER_AREA)


def zscore(prob: np.ndarray, sheet: np.ndarray) -> np.ndarray:
    v = prob[sheet]
    if v.size < 100:
        return np.zeros(prob.shape, np.float32)
    return np.where(sheet, (prob - v.mean()) / (v.std() + 1e-6), 0).astype(np.float32)


def overlay(
    z: np.ndarray, sheet: np.ndarray, um: float
) -> tuple[np.ndarray, np.ndarray]:
    """common.a_from_z: (a, mask) on the 50 um grid."""
    import cv2

    h, w = z.shape
    z3 = cv2.resize(
        np.where(sheet, z, 0).astype(np.float32),
        (w // DOWN, h // DOWN),
        interpolation=cv2.INTER_AREA,
    )
    v3 = cv2.resize(
        sheet.astype(np.float32), (w // DOWN, h // DOWN), interpolation=cv2.INTER_AREA
    )
    a = resample(np.clip((z3 - 0.9) / 1.8, 0, 1) * (v3 > 0.5), um * DOWN)
    m = resample(v3, um * DOWN) > 0.6
    a[~m] = 0
    return a.astype(np.float32), m


def sub_windows(mask: np.ndarray) -> list[tuple[int, int]]:
    """common.onsheet_windows(it, 128, 16, 0.7), with common.windows' last row and column."""
    import cv2

    h, w = mask.shape
    ys = list(range(0, max(1, h - GWIN + 1), GSTEP))
    xs = list(range(0, max(1, w - GWIN + 1), GSTEP))
    if ys and ys[-1] != h - GWIN and h > GWIN:
        ys.append(h - GWIN)
    if xs and xs[-1] != w - GWIN and w > GWIN:
        xs.append(w - GWIN)
    ii = cv2.integral(mask.astype(np.uint8))
    out = []
    for y in ys:
        for x in xs:
            if y + GWIN > h or x + GWIN > w:
                continue
            s = ii[y + GWIN, x + GWIN] - ii[y, x + GWIN] - ii[y + GWIN, x] + ii[y, x]
            if s >= ONSHEET * GWIN * GWIN:
                out.append((y, x))
    return out


def logits(
    net, a: np.ndarray, m: np.ndarray, ws: list[tuple[int, int]], bs: int = 256
) -> np.ndarray:
    """evaluate.score_windows with tta: the mean over the identity, three quarter turns and a left-right flip, in
    float16 autocast on a GPU (theirs) and float32 on the CPU."""
    import contextlib

    import torch

    dev = next(net.parameters()).device
    cast = (
        torch.autocast("cuda", dtype=torch.float16)
        if dev.type == "cuda"
        else contextlib.nullcontext()
    )
    out = []
    with torch.no_grad(), cast:
        for i in range(0, len(ws), bs):
            A = torch.from_numpy(
                np.stack([a[y : y + GWIN, x : x + GWIN] for y, x in ws[i : i + bs]])[
                    :, None
                ]
            ).to(dev)
            M = torch.from_numpy(
                np.stack(
                    [m[y : y + GWIN, x : x + GWIN] for y, x in ws[i : i + bs]]
                ).astype(np.float32)[:, None]
            ).to(dev)
            s = net(A, M)
            for k in (1, 2, 3):
                s = s + net(torch.rot90(A, k, (2, 3)), torch.rot90(M, k, (2, 3)))
            s = s + net(A.flip(3), M.flip(3))
            out.append((s / 5).float().cpu().numpy())
    return np.concatenate(out) if out else np.zeros(0, np.float32)


def row_score(
    z: np.ndarray, um: float, n_null: int = 12, seed: int = 0
) -> float | None:
    """spectral_rows.score of a window's z map (pitch 3.5 to 7 mm, 2.5 mm tile shuffles as the null)."""
    import cv2

    ds, px_mm = 4, 1000 / um
    zz = cv2.resize(
        z.astype(np.float32),
        (z.shape[1] // ds, z.shape[0] // ds),
        interpolation=cv2.INTER_AREA,
    )
    v = (
        cv2.resize(
            (z != 0).astype(np.float32),
            (zz.shape[1], zz.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
        > 0.99
    )
    zz = np.clip(zz, -1, 4)
    zz[~v] = 0
    if v.mean() < 0.15:
        return 0.0
    zz[v] -= zz[v].mean()
    taper = cv2.GaussianBlur(
        cv2.erode(v.astype(np.float32), np.ones((9, 9), np.uint8)), (0, 0), 6
    )
    zz = zz * taper

    def stat(img):
        h, w = img.shape
        win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
        F = np.abs(np.fft.fftshift(np.fft.fft2(img * win * v))) ** 2
        yy, xx = np.mgrid[:h, :w]
        fy, fx = (yy - h // 2) / h, (xx - w // 2) / w
        r = np.hypot(fy, fx) * (px_mm / ds)
        ang = (np.degrees(np.arctan2(fy, fx)) + 180) % 180
        band = (r >= 1 / 7.0) & (r <= 1 / 3.5)
        ab = (ang // 5).astype(int)
        pw = np.array(
            [
                F[band & (ab == k)].mean() if (band & (ab == k)).any() else 0
                for k in range(36)
            ]
        )
        return float((pw / (np.median(pw) + 1e-9)).max())

    t = int(2.5 * px_mm / ds)
    pos = [(i, j) for i in range(0, v.shape[0] - t + 1, t) for j in range(0, v.shape[1] - t + 1, t)
           if v[i : i + t, j : j + t].mean() >= 0.6]  # fmt: skip
    if len(pos) < 8:
        return None
    obs = stat(zz)
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_null):
        shuffled = zz.copy()
        src = [zz[i : i + t, j : j + t].copy() for i, j in pos]
        for (i, j), k in zip(pos, rng.permutation(len(pos)), strict=True):
            shuffled[i : i + t, j : j + t] = src[k]
        null.append(stat(shuffled * v))
    return float((obs - np.mean(null)) / (np.std(null) + 1e-6))


def sheet_of(render: Path, shape: tuple[int, int]) -> np.ndarray:
    """The render's surface layer above zero (window_score.py's ct > 0): the middle layer of the stored stack."""
    import zarr

    level = zarr.open(str(render), mode="r")["0"]
    if level.shape[1:] != shape:
        raise SystemExit(f"{render} is {level.shape[1:]}, the map is {shape}")
    return np.asarray(level[level.shape[0] // 2]) > 0


def winding_windows(
    net, prob: np.ndarray, sheet: np.ndarray, um: float, rows: bool = True
) -> list[dict]:
    """Every tri_rank window of one winding: x0, its share on the sheet, glyph score and row score."""
    z = zscore(prob, sheet)
    a, m = overlay(z, sheet, um)
    f = um / UM50
    out = []
    for x0 in starts(prob.shape[1]):
        on = float(sheet[:, x0 : x0 + WIN].mean())
        if on < MIN_ON:
            continue
        x50 = int(round(x0 * f))
        w50 = int(round(min(WIN, prob.shape[1] - x0) * f))
        ws = sub_windows(m[:, x50 : x50 + w50])
        g = (
            logits(net, a[:, x50 : x50 + w50], m[:, x50 : x50 + w50], ws)
            if ws
            else np.zeros(0)
        )
        out.append({
            "x0": x0,
            "on_sheet": round(on, 4),
            "glyph": round(float(g.max()), 3) if g.size else None,
            "rows": (lambda s: None if s is None else round(s, 3))(row_score(z[:, x0 : x0 + WIN], um)) if rows else None,
        })  # fmt: skip
    return out


def rank(windows: list[dict], key: str) -> list[dict]:
    """Windows with a score, best first; ties by winding and x0."""
    scored = [w for w in windows if w.get(key) is not None]
    return sorted(scored, key=lambda w: (-w[key], int(w["winding"][1:]), w["x0"]))


def score_cmd(args: argparse.Namespace) -> dict:
    import torch

    torch.set_num_threads(args.threads)
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    if device == "cuda":
        torch.cuda.set_per_process_memory_fraction(
            0.06
        )  # glyph_win.py's cap (about 1.4 GB)
    net = load_model(args.weights, device=device)
    windings = [w for w in Path(args.list).read_text().split() if w]
    record = {"weights": {"repo": REPO, "commit": COMMIT, "path": WEIGHTS_PATH, "sha256": WEIGHTS_SHA},
              "device": device, "um": args.um, "win": WIN, "step": STEP, "windings": {}, "missing": []}  # fmt: skip
    for w in windings:
        path, render = (
            Path(args.maps) / f"{w}.npy",
            Path(args.renders) / f"{w}_{args.slices}.zarr",
        )
        if not path.exists() or not render.exists():
            record["missing"].append(w)
            continue
        prob = np.load(path, allow_pickle=False).astype(np.float32)
        sheet = sheet_of(render, prob.shape) & np.isfinite(prob)
        record["windings"][w] = winding_windows(
            net, np.nan_to_num(prob), sheet, args.um, rows=not args.no_rows
        )
        print(
            w,
            max(
                (x["glyph"] for x in record["windings"][w] if x["glyph"] is not None),
                default=None,
            ),
            flush=True,
        )
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("out", type=Path)
    s.add_argument("maps")
    s.add_argument("renders")
    s.add_argument("list")
    s.add_argument("--weights", type=Path, required=True)
    s.add_argument("--um", type=float, required=True)
    s.add_argument("--slices", type=int, default=18)
    s.add_argument("--threads", type=int, default=2)
    s.add_argument("--no-rows", action="store_true")
    s.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default=None,
        help="default: cuda when there is one",
    )
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    record = score_cmd(args)
    args.out.write_text(json.dumps(record, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
