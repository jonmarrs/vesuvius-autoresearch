"""Finding 132: Studio with the winner's command, not running the windows whose crop holds no CT.

Registration: docs/preregistration/2026-11-20_studio_skip_empty_windows.md.

    run      --code DIR --input PLANES.npy --output MAP.npy --checkpoint W [--batch-size 32] [--stride 64
             --blend hann] [--skip-empty]
    compare  OUT.json --pair NAME OURS.npy REFERENCE.npy PLANES.npy ... --seconds-json FILE

`predict` is the loop of the winner's inference.py (Studio's code, MIT; DIR/inference.py, which the caller
checksums), using that file's own crop, hann96 and load_model, with one change. With skip_empty, a window whose
128-pixel crop (the 96-pixel window and its 16 pixels of context each side) has no pixel with CT is not run.

Such a window writes only to its central 96 pixels, which then have no CT either. The winner's loop sets every
pixel without CT to 0 at the end. So no pixel with CT can change, except by the GPU's rounding when a batch holds
other windows than before.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from contextlib import nullcontext
from itertools import islice
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import studio_reproduce as f123  # noqa: E402

# A map counts as the same map if it is this close to the reference over the pixels with CT. Finding 123's own run
# of the winner's command against the winner's published map, which differ by bf16 rounding, gave r 1.0, p99
# 0.000645 and 0.999892 on the same side of 0.5.
R_SAME, P99_SAME, SIDE_SAME = 0.9999, 0.002, 0.9995
FASTER = 0.8  # the skipping run takes at most this share of the full run's time on each band winding


def has_ct(ii: np.ndarray, h: int, w: int, y: int, x: int) -> bool:
    """Whether the crop of the window at (y, x), rows y - 16 to y + 111 and columns x - 16 to x + 111 clipped to
    the image, holds a pixel with CT; ii is the integral image of the CT mask, one row and column larger."""
    y0, y1 = max(0, y - 16), min(h, y + 112)
    x0, x1 = max(0, x - 16), min(w, x + 112)
    return bool(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0] > 0)


def integral(volume: np.ndarray) -> np.ndarray:
    occupied = (np.asarray(volume) != 0).any(0)
    ii = np.zeros((occupied.shape[0] + 1, occupied.shape[1] + 1), np.int64)
    ii[1:, 1:] = occupied.cumsum(0, dtype=np.int64).cumsum(1, dtype=np.int64)
    return ii


def predict(inf, model, volume, output, device="cuda", batch_size=1, amp="bf16", stride=96, blend="none",
            skip_empty=False) -> dict:  # fmt: skip
    """The winner's inference.predict, line for line, with the skip; returns the windows counted and run."""
    import torch

    with torch.inference_mode():
        if volume.ndim != 3 or volume.shape[0] != 16 or volume.dtype != np.uint8:
            raise ValueError(
                "Expected uint8 [16,H,W], in the verified model depth order"
            )
        h, w = volume.shape[-2:]
        if min(h, w) < 1 or batch_size < 1:
            raise ValueError("Image dimensions and batch size must be positive")
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        result = np.lib.format.open_memmap(
            output, mode="w+", dtype=np.float32, shape=(h, w)
        )
        if blend == "hann":
            weight = np.zeros((h, w), np.float32)
            kernel = inf.hann96()
            result[:] = 0
        starts_y = sorted(
            set(
                list(range(0, h, stride))
                + ([max(h - 96, 0)] if blend == "hann" else [])
            )
        )
        starts_x = sorted(
            set(
                list(range(0, w, stride))
                + ([max(w - 96, 0)] if blend == "hann" else [])
            )
        )
        every = [(y, x) for y in starts_y for x in starts_x]
        if skip_empty:
            ii = integral(volume)
            every_run = [(y, x) for y, x in every if has_ct(ii, h, w, y, x)]
        else:
            every_run = every
        coords = iter(every_run)
        while batch := list(islice(coords, batch_size)):
            raw = np.stack([inf.crop(volume, y - 16, x - 16) for y, x in batch])
            x = torch.from_numpy(raw[:, None]).to(device=device, dtype=torch.float32)
            x.clamp_(0, 200).div_(255)
            context = (
                torch.autocast("cuda", dtype=torch.bfloat16)
                if str(device).startswith("cuda") and amp == "bf16"
                else nullcontext()
            )
            with context:
                logits = model(x)
            probability = logits[:, 0, 16:112, 16:112].float().sigmoid().cpu().numpy()
            for (y, x), p in zip(batch, probability, strict=True):
                hh, ww = min(96, h - y), min(96, w - x)
                if blend == "hann":
                    result[y : y + hh, x : x + ww] += p[:hh, :ww] * kernel[:hh, :ww]
                    weight[y : y + hh, x : x + ww] += kernel[:hh, :ww]
                else:
                    result[y : y + hh, x : x + ww] = p[:hh, :ww]
        if blend == "hann":
            result[:] = np.where(
                weight > 0, result / np.maximum(weight, 1e-12), 0
            ).astype(np.float32)
        result[(np.asarray(volume) == 0).all(0)] = (
            0  # no CT data: outside the rendered surface
        )
        result.flush()
    return {"windows": len(every), "run": len(every_run)}


def run(args: argparse.Namespace) -> dict:
    import torch

    sys.path.insert(0, str(args.code))
    inf = importlib.import_module("inference")
    if Path(inf.__file__).resolve() != (args.code / "inference.py").resolve():
        raise SystemExit(f"imported {inf.__file__}, not {args.code / 'inference.py'}")
    if args.output.exists():
        raise SystemExit(f"{args.output} exists")
    if args.blend == "none" and args.stride != 96:
        raise SystemExit("--stride other than 96 needs --blend hann")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is unavailable")
    volume = np.load(args.input, mmap_mode="r", allow_pickle=False)
    model = inf.load_model(args.checkpoint, "cuda")
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    counts = predict(inf, model, volume, args.output, "cuda", args.batch_size, "bf16", args.stride, args.blend,
                     args.skip_empty)  # fmt: skip
    torch.cuda.synchronize()
    return {
        **counts,
        "seconds": round(time.perf_counter() - t0, 1),
        "skip_empty": args.skip_empty,
    }


def same(numbers: dict) -> bool:
    return (
        numbers["r"] >= R_SAME
        and numbers["abs_difference"]["p99"] <= P99_SAME
        and numbers["share_same_side_of_half"] >= SIDE_SAME
    )


def verdict(steps_ok: bool, pairs: dict, ratios: list[float]) -> str:
    """pairs: NAME -> numbers; full_* pairs check the copied loop, skip_* pairs the skip; ratios: skip / full time
    on each band winding."""
    if (
        not steps_ok
        or not pairs
        or not all(same(v) for k, v in pairs.items() if k.startswith("full_"))
    ):
        return "DOES_NOT_RUN"
    if not all(same(v) for k, v in pairs.items() if k.startswith("skip_")):
        return "SKIP_DIFFERS"
    if not ratios or max(ratios) > FASTER:
        return "SKIP_NOT_FASTER"
    return "SKIP_ADOPTED"


def compare_pair(ours: Path, reference: Path, planes: Path) -> dict:
    a = np.load(ours, mmap_mode="r", allow_pickle=False)
    b = np.load(reference, mmap_mode="r", allow_pickle=False)
    ct = (np.load(planes, mmap_mode="r", allow_pickle=False) != 0).any(0)
    numbers = f123.compare(np.asarray(a), np.asarray(b), ct)
    numbers["exact_over_the_ct"] = bool(
        np.array_equal(np.asarray(a)[ct], np.asarray(b)[ct])
    )
    return numbers


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--code", required=True, type=Path)
    r.add_argument("--input", required=True, type=Path)
    r.add_argument("--output", required=True, type=Path)
    r.add_argument("--checkpoint", required=True, type=Path)
    r.add_argument("--batch-size", type=int, default=32)
    r.add_argument("--stride", type=int, default=96)
    r.add_argument("--blend", default="none", choices=["none", "hann"])
    r.add_argument("--skip-empty", action="store_true")
    c = sub.add_parser("compare")
    c.add_argument("out", type=Path)
    c.add_argument(
        "--pair",
        nargs=4,
        action="append",
        required=True,
        metavar=("NAME", "OURS", "REFERENCE", "PLANES"),
    )
    c.add_argument(
        "--seconds-json",
        type=Path,
        required=True,
        help="{NAME: run record} for every run",
    )
    c.add_argument(
        "--band-windings",
        nargs="+",
        required=True,
        help="inputs whose skip must be faster",
    )
    c.add_argument("--steps-ok", choices=["yes", "no"], required=True)
    args = ap.parse_args(argv)
    if args.command == "run":
        print(json.dumps(run(args)))
        return 0
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    runs = json.loads(args.seconds_json.read_text())
    pairs = {
        name: compare_pair(Path(o), Path(ref), Path(p)) for name, o, ref, p in args.pair
    }
    ratios = {
        w: round(runs[f"skip_{w}"]["seconds"] / runs[f"full_{w}"]["seconds"], 4)
        for w in args.band_windings
    }
    result = {
        "finding": 132,
        "lines": {
            "r": R_SAME,
            "p99": P99_SAME,
            "same_side": SIDE_SAME,
            "faster": FASTER,
        },
        "runs": runs,
        "pairs": pairs,
        "time_ratio_skip_over_full": ratios,
        "verdict": verdict(args.steps_ok == "yes", pairs, list(ratios.values())),
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
