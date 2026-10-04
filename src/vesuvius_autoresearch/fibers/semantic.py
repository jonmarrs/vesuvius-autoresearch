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
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FIBER_HZ_VT_REPO = "scrollprize/fiber_hz_vt"
# From the shipped dataset.json.
LABELS = {0: "background", 1: "vt-fiber", 2: "hz-fiber", 3: "intersection"}


def _patch(shape):
    if (
        not isinstance(shape, (tuple, list))
        or len(shape) != 3
        or any(
            isinstance(s, (bool, np.bool_))
            or not isinstance(s, (int, np.integer))
            or s <= 0
            for s in shape
        )
    ):
        raise ValueError("patch must contain three positive integer dimensions")
    return tuple(int(s) for s in shape)


def _axes(axes):
    if (
        not isinstance(axes, (list, tuple))
        or any(
            isinstance(a, (bool, np.bool_))
            or not isinstance(a, (int, np.integer))
            or a not in (0, 1, 2)
            for a in axes
        )
        or len(set(axes)) != len(axes)
    ):
        raise ValueError("mirror axes must be distinct integer axes in (0, 1, 2)")
    return tuple(int(a) for a in axes)


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
    patch_divisibility: tuple[int, int, int] = (1, 1, 1)
    labels: dict[int, str] | None = None

    @property
    def label_names(self) -> dict[int, str]:
        if self.labels is not None:
            return dict(self.labels)
        return (
            dict(LABELS)
            if self.num_classes == 4
            else {
                i: "background" if i == 0 else f"class_{i}"
                for i in range(self.num_classes)
            }
        )


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
    patch = _patch(cfg["patch_size"])
    if len(dataset["channel_names"]) != 1:
        raise ValueError("semantic fiber inference supports one CT input channel")
    if cfg.get("normalization_schemes") != ["ZScoreNormalization"] or cfg.get(
        "use_mask_for_norm"
    ) != [False]:
        raise ValueError(
            "semantic fiber inference requires unmasked ZScoreNormalization"
        )
    labels = dataset["labels"]
    ids = list(labels.values())
    if (
        any(isinstance(i, bool) or not isinstance(i, int) for i in ids)
        or sorted(ids) != list(range(len(ids)))
        or labels.get("background") != 0
        or len(ids) < 2
    ):
        raise ValueError(
            "semantic labels must be contiguous integer classes with background=0"
        )

    kwargs = dict(arch["arch_kwargs"])
    strides = kwargs.get("strides", [(1, 1, 1)])
    if not isinstance(strides, (list, tuple)) or not strides:
        raise ValueError("network strides must be a nonempty sequence of 3D strides")
    divisibility = tuple(int(v) for v in np.prod([_patch(s) for s in strides], axis=0))
    if any(p % d for p, d in zip(patch, divisibility, strict=True)):
        raise ValueError(
            f"plans patch must be divisible by network strides {divisibility}"
        )
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
    unexpected = [
        k
        for k in unexpected
        if not re.fullmatch(r"decoder\.seg_layers\.[1-9]\d*\.(weight|bias)", k)
    ]
    if missing or unexpected:
        raise RuntimeError(
            f"checkpoint does not match the architecture from plans.json: "
            f"missing={list(missing)[:5]} unexpected={unexpected[:5]}"
        )

    network = network.to(device).eval()
    return SemanticModel(
        network=network,
        patch_size=patch,
        num_classes=num_classes,
        device=device,
        mirror_axes=_axes(ck.get("inference_allowed_mirroring_axes") or ()),
        patch_divisibility=divisibility,
        labels={value: name for name, value in labels.items()},
    )


def zscore(volume: np.ndarray) -> np.ndarray:
    """nnUNet `ZScoreNormalization` with `use_mask_for_norm=False`: per-image."""
    v = np.asarray(volume)
    if (
        v.ndim != 3
        or any(s == 0 for s in v.shape)
        or v.dtype.kind not in "uif"
        or not np.isfinite(v).all()
    ):
        raise ValueError("volume must be a nonempty finite real CT array (Z, Y, X)")
    v = v.astype(np.float32)
    if not np.isfinite(v).all():
        raise ValueError("volume values exceed float32 range")
    # Keep the published float32 normalization recipe and its memory budget.
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        std, mean = float(v.std()), float(v.mean())
        out = (v - mean) / (std if std > 0 else 1.0)
    if not math.isfinite(std) or not math.isfinite(mean) or not np.isfinite(out).all():
        raise ValueError("volume normalization produced nonfinite statistics or values")
    return out


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

    if (
        isinstance(tile_step, (bool, np.bool_))
        or not isinstance(tile_step, (int, float, np.integer, np.floating))
        or not math.isfinite(tile_step)
        or not 0 < tile_step <= 1
    ):
        raise ValueError("tile_step must be finite in (0, 1]")
    patch = _patch(model.patch_size if patch_size is None else patch_size)
    divisibility = _patch(model.patch_divisibility)
    if any(p % d for p, d in zip(patch, divisibility, strict=True)):
        raise ValueError(f"patch must be divisible by network strides {divisibility}")
    mirror_axes = _axes(model.mirror_axes)
    if (
        isinstance(model.num_classes, bool)
        or not isinstance(model.num_classes, int)
        or model.num_classes < 2
    ):
        raise ValueError("num_classes must be an integer >= 2")
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

    dev = str(model.device)
    mirror_views = _mirror_combinations(mirror_axes) if use_mirroring else []

    def checked_logits(t):
        out = model.network(t)
        if (
            not isinstance(out, torch.Tensor)
            or tuple(out.shape) != (1, model.num_classes, *patch)
            or not bool(torch.isfinite(out).all())
        ):
            raise ValueError(
                f"semantic logits must be finite with shape {(1, model.num_classes, *patch)}"
            )
        return out.float()

    with torch.no_grad():
        for z0 in starts[0]:
            for y0 in starts[1]:
                for x0 in starts[2]:
                    tile = vol[
                        z0 : z0 + patch[0], y0 : y0 + patch[1], x0 : x0 + patch[2]
                    ]
                    t = torch.from_numpy(tile)[None, None].to(dev)
                    with torch.autocast("cuda", enabled=amp and dev.startswith("cuda")):
                        logits = checked_logits(t)
                        for ax in mirror_views:
                            flipped = torch.flip(t, [a + 2 for a in ax])
                            logits = logits + torch.flip(
                                checked_logits(flipped), [a + 2 for a in ax]
                            )
                        logits = logits / (1 + len(mirror_views))
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

    if not bool((wsum > 0).all()):
        raise ValueError("semantic tiling left uncovered voxels")
    acc = acc / wsum[None]
    out = acc[:, : shape[0], : shape[1], : shape[2]].numpy()
    if not np.isfinite(out).all():
        raise ValueError("semantic probabilities must be finite")
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
    prob = np.asarray(prob)
    if (
        prob.ndim != 4
        or prob.shape[0] < 2
        or any(s == 0 for s in prob.shape[1:])
        or not np.isfinite(prob).all()
        or np.any((prob < 0) | (prob > 1))
        or not np.allclose(prob.sum(axis=0), 1.0, atol=1e-5, rtol=1e-5)
    ):
        raise ValueError(
            "probabilities must be finite normalized classes with shape (C, Z, Y, X)"
        )
    return 1.0 - prob[0]
