"""
Villa-integrated inference utilities.

Provides:
- GaussianBlender: positive finite 2D Gaussian weights for regional soft-tiling
- VillaTTAWrapper: experimental scalar-field adapter to pinned Villa TTA
"""

import math
from numbers import Integral, Real

import torch
import torch.nn as nn

from vesuvius_autoresearch.core.villa_modules import load_villa_leaf

# Villa's TTA is a leaf module (it imports only torch), so it is loaded from the
# pinned file itself. Prepending villa/vesuvius/src to sys.path instead made the
# result depend on import order: after an earlier `import vesuvius` it returned the
# older installed snapshot, and before one it replaced `vesuvius` process-wide.
_VILLA_TTA = "vesuvius/src/vesuvius/models/run/tta.py"


def _load_villa_tta():
    """Load the optional upstream implementation only when TTA is requested."""
    return load_villa_leaf(_VILLA_TTA).infer_with_tta


# ---------------------------------------------------------------------------
# GaussianBlender
# ---------------------------------------------------------------------------


class GaussianBlender:
    """Generates a 2D Gaussian weight window for soft-tiling.

    Weights are float32, strictly positive and normalized so the peak is one.
    Invalid or unrepresentable windows are rejected before caching. The default
    regional blending recipe is preserved.

    Parameters
    ----------
    patch_size : int
        Spatial size of the square patch (H == W == patch_size).
    sigma : float, optional
        Standard deviation expressed as a *fraction* of ``patch_size``.
        Default ``0.125`` (i.e. sigma = patch_size / 8).
    """

    def __init__(self, patch_size: int, sigma: float = 0.125):
        if (
            isinstance(patch_size, bool)
            or not isinstance(patch_size, Integral)
            or patch_size < 1
        ):
            raise ValueError("patch_size must be a positive integer")
        if (
            isinstance(sigma, bool)
            or not isinstance(sigma, Real)
            or not math.isfinite(sigma)
            or sigma <= 0
        ):
            raise ValueError("sigma must be finite and positive")
        self.patch_size = patch_size
        self.sigma_px = sigma * patch_size
        if not math.isfinite(self.sigma_px) or self.sigma_px <= 0:
            raise ValueError("sigma * patch_size must be finite and positive")
        self._cache: dict[torch.device, torch.Tensor] = {}

    # -- public API ----------------------------------------------------------

    def get_weight_window(self, device: torch.device) -> torch.Tensor:
        """Return the 2D Gaussian window tensor on *device* (cached)."""
        device = torch.device(device)
        if device.type == "cuda" and device.index is None:
            device = torch.device("cuda", torch.cuda.current_device())
        elif device.type == "cpu":
            device = torch.device("cpu")
        if device not in self._cache:
            self._cache[device] = self._build_window(device)
        return self._cache[device]

    # -- internals -----------------------------------------------------------

    def _build_window(self, device: torch.device) -> torch.Tensor:
        """Create a (patch_size, patch_size) Gaussian weight tensor."""
        coords = torch.arange(self.patch_size, dtype=torch.float32, device=device)
        center = (self.patch_size - 1) / 2.0
        gauss_1d = torch.exp(-0.5 * ((coords - center) / self.sigma_px) ** 2)
        window = gauss_1d.unsqueeze(1) * gauss_1d.unsqueeze(0)
        peak = window.max()
        if not torch.isfinite(window).all() or peak <= 0:
            raise ValueError(
                "sigma cannot produce a finite positive float32 Gaussian window; choose a larger sigma"
            )
        # Normalize so peak == 1 (like the Hanning window)
        window /= peak
        if not torch.isfinite(window).all() or not (window > 0).all():
            raise ValueError(
                "sigma underflows the float32 Gaussian window; choose a larger sigma"
            )
        return window


# ---------------------------------------------------------------------------
# VillaTTAWrapper
# ---------------------------------------------------------------------------


def _default_multi_task_concat(output):
    """Concatenate three matching scalar-field heads; return one unsplit tensor.

    Regional ink/fiber/QC outputs have different ranks and use the separate
    in-plane multi-task predictor. No broadcasting or task conversion is inferred.
    """
    if not isinstance(output, (tuple, list)) or len(output) != 3:
        raise ValueError(
            "default TTA concatenation needs three spatial tensor heads; provide a custom concatenator for other containers"
        )
    if not all(isinstance(head, torch.Tensor) for head in output):
        raise TypeError("TTA heads must be tensors")
    first = output[0]
    if first.ndim not in (4, 5) or any(
        head.ndim != first.ndim
        or head.shape[0] != first.shape[0]
        or head.shape[2:] != first.shape[2:]
        for head in output
    ):
        raise ValueError(
            "TTA heads must share batch and spatial tensor ranks/grids; mixed ink/fiber/global-QC outputs need the regional in-plane inference path"
        )
    return torch.cat(output, dim=1)


class VillaTTAWrapper(nn.Module):
    """Experimental TTA for scalar response fields with preserved batch/rank.

    The wrapper intercepts ``__call__`` (i.e. ``forward``), runs
    :func:`infer_with_tta` from Villa's TTA module, and returns the
    TTA-averaged tensor. Channels are independent scalar fields, not directional
    vectors/tensors requiring component reorientation. Callers own eval/gradient
    mode. Current autoresearch multi-task inference uses core.inference instead.

    Parameters
    ----------
    model : nn.Module
        The model returning a spatial tensor, or task outputs with a concatenator.
    tta_type : str, optional
        ``'mirroring'`` (default) for flip-based TTA, ``'rotation'`` for
        axis-transpose TTA (not arbitrary angular rotations).
    use_batched : bool, optional
        If ``True`` (default), mirroring first tries one forward with stacked
        views, using more VRAM. Falls back to sequential on OOM. Throughput
        depends on the model and device and is not established by this adapter.
    is_multi_task : bool, optional
        Set to ``True`` to concatenate task outputs before deaugmentation. The
        default requires three matching spatial heads, unlike ink/fiber/global-QC.
    concat_multi_task_outputs : callable or None
        Custom function to concatenate multi-task outputs into a single
        spatial tensor. Defaults to :func:`_default_multi_task_concat`. The result
        stays concatenated; this wrapper does not split it back into heads.
    """

    def __init__(
        self,
        model: nn.Module,
        tta_type: str = "mirroring",
        *,
        use_batched: bool = True,
        is_multi_task: bool = False,
        concat_multi_task_outputs=None,
    ):
        super().__init__()
        if not callable(model):
            raise TypeError("TTA model must be callable")
        if tta_type not in ("mirroring", "rotation"):
            raise ValueError(f"unsupported tta_type: {tta_type!r}")
        if type(use_batched) is not bool or type(is_multi_task) is not bool:
            raise ValueError("use_batched and is_multi_task must be booleans")
        if concat_multi_task_outputs is not None and not callable(
            concat_multi_task_outputs
        ):
            raise TypeError("concat_multi_task_outputs must be callable")
        self.model = model
        self.tta_type = tta_type
        self.use_batched = use_batched
        self.is_multi_task = is_multi_task
        self.concat_multi_task_outputs = (
            concat_multi_task_outputs
            if concat_multi_task_outputs is not None
            else _default_multi_task_concat
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Run the wrapped model with TTA.

        Parameters
        ----------
        x : torch.Tensor
            Input tensor – 5-D ``[B, C, Z, H, W]`` for 3-D models or
            4-D ``[B, C, H, W]`` for 2-D models.

        Returns
        -------
        torch.Tensor
            TTA-averaged tensor with the input batch size and spatial rank.
            Batched mirroring requires the input spatial grid. Sequential paths
            can retain a coarser scalar grid that aligns after deaugmentation.
        """
        if not isinstance(x, torch.Tensor):
            raise TypeError("TTA input must be a tensor")
        if x.ndim not in (4, 5) or min(x.shape) < 1:
            raise ValueError("TTA needs a nonempty [B,C,H,W] or [B,C,D,H,W] input")

        def model_view(view):
            # Keep per-view geometry with the raw output. Villa still chooses
            # when concatenation happens, preserving sequential callback order.
            return view.shape, self.model(view)

        def checked_output(result):
            shape, output = result
            if self.is_multi_task:
                output = self.concat_multi_task_outputs(output)
            if not isinstance(output, torch.Tensor):
                raise TypeError("TTA model/concatenator must return a spatial tensor")
            if (
                output.ndim != len(shape)
                or output.shape[0] != shape[0]
                or min(output.shape) < 1
            ):
                raise ValueError(
                    "TTA output must preserve the view's batch size and spatial rank"
                )
            # Batched Villa mirroring reshapes using input dimensions. Equal
            # element counts alone can silently reinterpret a different grid.
            if shape[0] != x.shape[0] and output.shape[2:] != shape[2:]:
                raise ValueError(
                    "batched TTA output must use the input spatial grid; use_batched=False supports coarser scalar fields"
                )
            return output

        return _load_villa_tta()(
            model_view,
            x,
            self.tta_type,
            is_multi_task=True,
            concat_multi_task_outputs=checked_output,
            use_batched=self.use_batched,
        )
