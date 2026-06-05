"""
Villa-integrated inference utilities.

Provides:
- GaussianBlender: 2D Gaussian weight window for soft-tiling (smoother than Hanning)
- VillaTTAWrapper: Wraps any model to apply Villa's test-time augmentation
"""

import os
import sys

import torch
import torch.nn as nn

# ---------------------------------------------------------------------------
# sys.path manipulation so we can import Villa's TTA from the submodule tree
# without requiring it to be installed as a package.
# ---------------------------------------------------------------------------
_VILLA_VESUVIUS_SRC = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        os.pardir,
        "villa",
        "vesuvius",
        "src",
    )
)
if _VILLA_VESUVIUS_SRC not in sys.path:
    sys.path.insert(0, _VILLA_VESUVIUS_SRC)

from vesuvius.models.run.tta import infer_with_tta  # noqa: E402

# ---------------------------------------------------------------------------
# GaussianBlender
# ---------------------------------------------------------------------------


class GaussianBlender:
    """Generates a 2D Gaussian weight window for soft-tiling.

    Compared to the Hanning window traditionally used in predict.py, a
    Gaussian window decays more smoothly toward the edges, which reduces
    tile-boundary artifacts especially at higher overlap ratios.

    Parameters
    ----------
    patch_size : int
        Spatial size of the square patch (H == W == patch_size).
    sigma : float, optional
        Standard deviation expressed as a *fraction* of ``patch_size``.
        Default ``0.125`` (i.e. sigma = patch_size / 8).
    """

    def __init__(self, patch_size: int, sigma: float = 0.125):
        self.patch_size = patch_size
        self.sigma_px = sigma * patch_size
        self._cache: dict[torch.device, torch.Tensor] = {}

    # -- public API ----------------------------------------------------------

    def get_weight_window(self, device: torch.device) -> torch.Tensor:
        """Return the 2D Gaussian window tensor on *device* (cached)."""
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
        # Normalize so peak == 1 (like the Hanning window)
        window /= window.max()
        return window


# ---------------------------------------------------------------------------
# VillaTTAWrapper
# ---------------------------------------------------------------------------


def _default_multi_task_concat(output):
    """Default concat function for (ink, fiber, qc) multi-task tuple output.

    The Villa TTA infrastructure needs a single tensor per forward pass for
    the batched path.  This function stacks the three heads along the channel
    dimension so they can be averaged together and then split back apart.

    Expected input: tuple of (ink, fiber, qc) tensors.
    Expected output: single tensor with channels concatenated.
    """
    ink, fiber, qc = output
    return torch.cat([ink, fiber, qc], dim=1)


class VillaTTAWrapper(nn.Module):
    """Wraps any model to apply Villa test-time augmentation during inference.

    The wrapper intercepts ``__call__`` (i.e. ``forward``), runs
    :func:`infer_with_tta` from Villa's TTA module, and returns the
    TTA-averaged result.

    Parameters
    ----------
    model : nn.Module
        The base model (or SwarmVoter ensemble) to wrap.
    tta_type : str, optional
        ``'mirroring'`` (default) for flip-based TTA, ``'rotation'`` for
        axis-transpose TTA.
    use_batched : bool, optional
        If ``True`` (default), the batched TTA path is tried first (faster
        but uses more VRAM).  Falls back to sequential on OOM.
    is_multi_task : bool, optional
        Set to ``True`` when the model returns a tuple of task outputs
        (ink, fiber, qc) rather than a single tensor.
    concat_multi_task_outputs : callable or None
        Custom function to concatenate multi-task outputs into a single
        tensor.  Defaults to :func:`_default_multi_task_concat`.
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
            TTA-averaged output tensor.
        """
        return infer_with_tta(
            self.model,
            x,
            self.tta_type,
            is_multi_task=self.is_multi_task,
            concat_multi_task_outputs=self.concat_multi_task_outputs,
            use_batched=self.use_batched,
        )
