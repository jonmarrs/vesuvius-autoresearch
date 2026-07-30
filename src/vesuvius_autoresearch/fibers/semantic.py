"""Inference for villa's published semantic fiber models (e.g. `fiber_hz_vt`).

Why this exists: the conservative tracer needs a fiber probability field, and
classical Hessian vesselness is not good enough on real scroll CT. Measured on a
hand-traced 7.91 um cube, max-normalized vesselness separates fibers from
background by a mean ratio of only ~2.2, and a tracer driven by it scores
precision 0.026 against a 0.0126 base rate (see
`reports/fiber_tracer_first_result.md`). villa trained a learned model for
exactly this reason, so we consume theirs rather than competing with it.

The network is built **directly from `plans.json`** rather than through
`nnUNetPredictor.initialize_from_trained_model_folder`. Three reasons:

1. The checkpoint's trainer is `nnUNetTrainerMedialSurfaceRecall`, a villa custom
   class that is not in the installed `nnunetv2`, so the standard loader cannot
   resolve it.
2. `nnUNetPredictor` wants `nnUNet_results` / `nnUNet_preprocessed` environment
   variables set, which is unwanted global state for a library function.
3. The published plans are `nnUNetResEncUNetPlans_48G`, sized for a 48 GB GPU
   (patch 256x256x224). Building the model here lets us control tiling and
   precision to fit a 24 GB card.

Everything that affects the numbers is taken from the shipped configs: the
architecture and its kwargs, the patch size, and `ZScoreNormalization`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FIBER_HZ_VT_REPO = "scrollprize/fiber_hz_vt"
# From the shipped dataset.json.
LABELS = {0: "background", 1: "vt-fiber", 2: "hz-fiber", 3: "intersection"}


def _import_by_path(dotted: str):
    mod, _, name = dotted.rpartition(".")
    import importlib

    return getattr(importlib.import_module(mod), name)


@dataclass
class SemanticModel:
    """A loaded nnUNet-style semantic fiber model plus its inference config."""

    network: object
    patch_size: tuple[int, int, int]
    num_classes: int
    device: str
    mirror_axes: tuple[int, ...] = ()

    @property
    def label_names(self) -> dict[int, str]:
        return dict(LABELS)


def load_model(
    model_dir,
    fold: str = "fold_0",
    checkpoint: str = "checkpoint_final.pth",
    configuration: str = "3d_fullres",
    device: str = "cuda",
) -> SemanticModel:
    """Build the architecture from plans.json and load the published weights.

    `model_dir` must contain `plans.json`, `dataset.json` and
    `<fold>/<checkpoint>`, i.e. the Hugging Face repo contents with the
    checkpoint moved into a fold subdirectory.
    """
    import torch

    model_dir = Path(model_dir)
    plans = json.loads((model_dir / "plans.json").read_text())
    dataset = json.loads((model_dir / "dataset.json").read_text())
    cfg = plans["configurations"][configuration]
    arch = cfg["architecture"]

    kwargs = dict(arch["arch_kwargs"])
    for key in arch.get("_kw_requires_import", []):
        val = kwargs.get(key)
        kwargs[key] = _import_by_path(val) if isinstance(val, str) else val

    num_classes = len(dataset["labels"])
    n_channels = len(dataset["channel_names"])
    net_cls = _import_by_path(arch["network_class_name"])
    network = net_cls(
        input_channels=n_channels,
        num_classes=num_classes,
        deep_supervision=False,
        **kwargs,
    )

    ck = torch.load(
        model_dir / fold / checkpoint, map_location="cpu", weights_only=False
    )
    weights = ck["network_weights"]
    # The checkpoint was saved with deep supervision on, so it carries extra
    # decoder.seg_layers.{1..n}. Those heads are unused at inference; dropping
    # them is expected, but anything ELSE missing is a real mismatch and must
    # not be silently tolerated.
    missing, unexpected = network.load_state_dict(weights, strict=False)
    unexpected = [k for k in unexpected if not k.startswith("decoder.seg_layers.")]
    if missing or unexpected:
        raise RuntimeError(
            f"checkpoint does not match the architecture from plans.json: "
            f"missing={list(missing)[:5]} unexpected={unexpected[:5]}"
        )

    network = network.to(device).eval()
    return SemanticModel(
        network=network,
        patch_size=tuple(cfg["patch_size"]),
        num_classes=num_classes,
        device=device,
        mirror_axes=tuple(ck.get("inference_allowed_mirroring_axes") or ()),
    )


def zscore(volume: np.ndarray) -> np.ndarray:
    """nnUNet `ZScoreNormalization` with `use_mask_for_norm=False`: per-image."""
    v = np.asarray(volume, dtype=np.float32)
    std = float(v.std())
    return (v - float(v.mean())) / (std if std > 0 else 1.0)


def _gaussian_weight(shape, sigma_scale: float = 0.125) -> np.ndarray:
    """nnUNet's per-tile Gaussian importance map: centre voxels dominate.

    Without it, tile seams appear as visible discontinuities in the probability
    field, which a tracer then reads as a fiber ending.
    """
    from scipy.ndimage import gaussian_filter

    tmp = np.zeros(shape, dtype=np.float32)
    center = tuple(s // 2 for s in shape)
    tmp[center] = 1.0
    sig = [s * sigma_scale for s in shape]
    g = gaussian_filter(tmp, sig, mode="constant", cval=0.0)
    g = g / g.max()
    return np.maximum(g, g.max() * 1e-3).astype(np.float32)


def _tile_starts(size: int, patch: int, step: float) -> list[int]:
    if patch >= size:
        return [0]
    stride = max(1, int(round(patch * step)))
    starts = list(range(0, size - patch + 1, stride))
    if starts[-1] != size - patch:
        starts.append(size - patch)
    return starts


def predict_volume(
    model: SemanticModel,
    volume: np.ndarray,
    tile_step: float = 0.5,
    patch_size: tuple[int, int, int] | None = None,
    use_mirroring: bool = False,
    amp: bool = True,
    verbose: bool = False,
) -> np.ndarray:
    """Sliding-window softmax probabilities, shape (num_classes, Z, Y, X).

    Args:
        patch_size: override the plans' patch size. The published plans use
            256x256x224, which does not fit a 24 GB card comfortably; a smaller
            patch trades a little accuracy near tile edges for feasibility.
        use_mirroring: test-time augmentation over `model.mirror_axes`. Costs
            2**len(axes) forward passes; off by default.
        amp: autocast to fp16 on CUDA.

    Accumulation is done on CPU in float32 so memory scales with the volume, not
    the GPU, and the volume is normalized once as a whole (nnUNet normalizes
    per-image, not per-tile; normalizing per-tile would make each tile's
    statistics differ and introduce seams).
    """
    import torch

    patch = tuple(patch_size or model.patch_size)
    vol = zscore(volume)
    shape = vol.shape
    pad = [max(0, patch[a] - shape[a]) for a in range(3)]
    if any(pad):
        vol = np.pad(
            vol,
            [(0, pad[0]), (0, pad[1]), (0, pad[2])],
            mode="constant",
            constant_values=0.0,
        )
    padded = vol.shape

    starts = [_tile_starts(padded[a], patch[a], tile_step) for a in range(3)]
    gw = _gaussian_weight(patch)
    gw_t = torch.from_numpy(gw)

    acc = torch.zeros((model.num_classes, *padded), dtype=torch.float32)
    wsum = torch.zeros(padded, dtype=torch.float32)

    n_tiles = len(starts[0]) * len(starts[1]) * len(starts[2])
    if verbose:
        print(f"  volume {shape} -> padded {padded}, patch {patch}, {n_tiles} tiles")

    dev = model.device
    with torch.no_grad():
        for z0 in starts[0]:
            for y0 in starts[1]:
                for x0 in starts[2]:
                    tile = vol[
                        z0 : z0 + patch[0], y0 : y0 + patch[1], x0 : x0 + patch[2]
                    ]
                    t = torch.from_numpy(tile)[None, None].to(dev)
                    with torch.autocast("cuda", enabled=amp and dev.startswith("cuda")):
                        logits = model.network(t)
                        if use_mirroring and model.mirror_axes:
                            for ax in _mirror_combinations(model.mirror_axes):
                                flipped = torch.flip(t, [a + 2 for a in ax])
                                out = model.network(flipped)
                                logits = logits + torch.flip(out, [a + 2 for a in ax])
                            logits = logits / (
                                1 + len(_mirror_combinations(model.mirror_axes))
                            )
                    prob = torch.softmax(logits.float(), dim=1)[0].cpu()
                    acc[
                        :,
                        z0 : z0 + patch[0],
                        y0 : y0 + patch[1],
                        x0 : x0 + patch[2],
                    ] += prob * gw_t
                    wsum[
                        z0 : z0 + patch[0],
                        y0 : y0 + patch[1],
                        x0 : x0 + patch[2],
                    ] += gw_t

    acc = acc / torch.clamp(wsum, min=1e-8)[None]
    out = acc[:, : shape[0], : shape[1], : shape[2]].numpy()
    return out


def _mirror_combinations(axes: tuple[int, ...]) -> list[tuple[int, ...]]:
    from itertools import combinations

    combos: list[tuple[int, ...]] = []
    for r in range(1, len(axes) + 1):
        combos.extend(combinations(axes, r))
    return combos


def fiber_probability(prob: np.ndarray) -> np.ndarray:
    """Collapse the 4 classes into a single "is fiber" probability.

    vt-fiber, hz-fiber and intersection are all fiber; only background is not.
    Using 1 - P(background) rather than summing the three keeps the result exactly
    in [0, 1] regardless of softmax round-off.
    """
    return 1.0 - prob[0]
