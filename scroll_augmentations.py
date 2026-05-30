"""Standalone, GPU-native augmentations targeting Vesuvius Challenge scroll
CT artifacts. Designed for ScrollPrize/villa issue #201.

Each augmentation is a pure function on torch tensors — no train.py imports,
no config-object dependency — so this module can be ported into villa's
batchgeneratorsv2 Transform protocol with minimal restructuring.

Three augmentations from the issue's explicit ask:
  - scroll_decohesion: beam-scattering simulation. Two physically-motivated
    components: a z-shifted ghost copy ("smeared from previous layers") and
    symmetric z-blur (general beam spread).
  - scroll_warping: elastic-like deformation via Gaussian-smoothed random
    displacement field. Distinct from compression — converts a "straight"
    chunk into a deformed one without globally squeezing it.
  - scroll_squeeze: sinusoidal X-compression + small Y-undulation.
    Matches the issue's "compressed regions from normal data" example.

Two bonus augmentations (issue text: "Any additional augmentations that
may improve performance are welcome"):
  - scroll_z_dropout: random z-slice replacement with z-mean (simulates
    occasional bad slices)
  - scroll_intensity_drift: depth-dependent multiplicative intensity scaling
    (simulates X-ray dose / beam-hardening variation across z)

All augmentations operate on tensors of shape [B, C, Z, H, W] with labels
shaped [B, 1, H, W] (ink) and [B, 1, 1, H, W] (fiber). The squeeze and
warping augmentations also warp the labels so the ink/fiber stays in
sync with the deformed image.
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _warp_2d_tensor(t: torch.Tensor, grid2d: torch.Tensor) -> torch.Tensor:
    """Apply a 2D sampling grid to a label tensor. Handles both 4D
    [B, C, H, W] (ink) and 5D [B, C, 1, H, W] (fiber)."""
    if t.dim() == 5:
        squeezed = t.squeeze(2)
        warped = F.grid_sample(
            squeezed,
            grid2d,
            mode="bilinear",
            padding_mode="border",
            align_corners=True,
        )
        return warped.unsqueeze(2)
    return F.grid_sample(
        t,
        grid2d,
        mode="bilinear",
        padding_mode="border",
        align_corners=True,
    )


# ---------------------------------------------------------------------------
# Issue #201's three explicit asks: decohesion, warping, squeezing/pulling
# ---------------------------------------------------------------------------


def scroll_decohesion(
    x: torch.Tensor,
    alpha: float = 0.30,
    ghost_offset: int = 2,
    blur_kernel: int = 5,
) -> torch.Tensor:
    """Simulate beam scattering / smearing from previous z-layers.

    Two components blended into the original with weight `alpha`:
      1. **Z-ghost**: a z-shifted copy of the volume so each z-slice gets
         a contribution from `ghost_offset` slices earlier. Directly
         models the issue's "smeared from previous layers" description.
      2. **Z-blur**: symmetric averaging along z via a kernel of size
         `blur_kernel`. Models general beam spread / loss of contrast.

    Args:
        x: [B, C, Z, H, W] float tensor.
        alpha: blend weight for the scattered components, 0..1.
        ghost_offset: z-shift in voxels for the ghost copy.
        blur_kernel: kernel size for symmetric z-blur (odd, >=3).
    Returns:
        Same shape as x.
    """
    if x.shape[2] < max(3, ghost_offset + 1):
        return x

    ghost = torch.zeros_like(x)
    ghost[:, :, ghost_offset:] = x[:, :, :-ghost_offset]

    blurred = F.avg_pool3d(
        x,
        kernel_size=(blur_kernel, 1, 1),
        stride=1,
        padding=(blur_kernel // 2, 0, 0),
    )

    return (1.0 - alpha) * x + (alpha * 0.6) * blurred + (alpha * 0.4) * ghost


def scroll_warping(
    x: torch.Tensor,
    target_ink: torch.Tensor,
    target_fiber: torch.Tensor,
    max_displacement: float = 6.0,
    n_ctrl: int = 4,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Apply elastic-like deformation via a smooth random displacement field.

    The displacement field is generated at low resolution (`n_ctrl` x
    `n_ctrl` control points) with random Gaussian magnitudes and then
    bilinearly upsampled to the patch resolution — this produces smooth,
    locally-varying deformations matching natural papyrus warping.

    Distinct from `scroll_squeeze`: there's no global compression direction,
    just localized random deformation.

    Args:
        x: [B, C, Z, H, W].
        target_ink: [B, 1, H, W].
        target_fiber: [B, 1, 1, H, W].
        max_displacement: peak random displacement in voxels.
        n_ctrl: control-point grid resolution. Smaller = smoother / larger-scale.
    """
    B, C, Z, H, W = x.shape
    device, dtype = x.device, x.dtype

    raw_dy = (
        torch.randn((B, 1, n_ctrl, n_ctrl), device=device, dtype=dtype)
        * max_displacement
    )
    raw_dx = (
        torch.randn((B, 1, n_ctrl, n_ctrl), device=device, dtype=dtype)
        * max_displacement
    )

    dy = F.interpolate(
        raw_dy, size=(H, W), mode="bilinear", align_corners=True
    ).squeeze(1)
    dx = F.interpolate(
        raw_dx, size=(H, W), mode="bilinear", align_corners=True
    ).squeeze(1)

    dy_norm = dy * 2.0 / max(1, H - 1)
    dx_norm = dx * 2.0 / max(1, W - 1)

    yy, xx = torch.meshgrid(
        torch.linspace(-1.0, 1.0, H, device=device, dtype=dtype),
        torch.linspace(-1.0, 1.0, W, device=device, dtype=dtype),
        indexing="ij",
    )
    grid_x = xx.unsqueeze(0) + dx_norm
    grid_y = yy.unsqueeze(0) + dy_norm
    grid2d = torch.stack(
        [grid_x.clamp(-1.0, 1.0), grid_y.clamp(-1.0, 1.0)],
        dim=-1,
    )  # [B, H, W, 2]

    # Apply same 2D warp to every z-slice (papyrus deformation is mostly
    # in-plane on the scroll surface).
    x_flat = x.permute(0, 2, 1, 3, 4).reshape(B * Z, C, H, W)
    grid3d = grid2d.unsqueeze(1).expand(B, Z, H, W, 2).reshape(B * Z, H, W, 2)
    x_warped = F.grid_sample(
        x_flat,
        grid3d,
        mode="bilinear",
        padding_mode="border",
        align_corners=True,
    )
    x_warped = x_warped.reshape(B, Z, C, H, W).permute(0, 2, 1, 3, 4)

    ink_warped = _warp_2d_tensor(target_ink, grid2d).clamp(0, 1)
    fiber_warped = _warp_2d_tensor(target_fiber, grid2d).clamp(0, 1)
    return x_warped, ink_warped, fiber_warped


def scroll_squeeze(
    x: torch.Tensor,
    target_ink: torch.Tensor,
    target_fiber: torch.Tensor,
    scale_range: tuple[float, float] = (0.72, 0.92),
    shear_range: tuple[float, float] = (-0.18, 0.18),
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Sinusoidal X-compression with mild Y-undulation.

    Models "compressed regions from normal data" — the chunk gets squeezed
    in the X axis, with a small Y wobble. Each sample in the batch gets
    its own scale/shear/phase.
    """
    B, C, Z, H, W = x.shape
    device, dtype = x.device, x.dtype

    yy, xx = torch.meshgrid(
        torch.linspace(-1.0, 1.0, H, device=device, dtype=dtype),
        torch.linspace(-1.0, 1.0, W, device=device, dtype=dtype),
        indexing="ij",
    )
    scale = torch.empty((B, 1, 1), device=device, dtype=dtype).uniform_(*scale_range)
    shear = torch.empty((B, 1, 1), device=device, dtype=dtype).uniform_(*shear_range)
    phase = torch.empty((B, 1, 1), device=device, dtype=dtype).uniform_(
        0.0, 2.0 * math.pi
    )
    x_map = xx.unsqueeze(0) / scale + shear * torch.sin(
        math.pi * yy.unsqueeze(0) + phase
    )
    y_map = yy.unsqueeze(0) + 0.08 * torch.sin(2.0 * math.pi * xx.unsqueeze(0) + phase)
    grid2d = torch.stack([x_map.clamp(-1, 1), y_map.clamp(-1, 1)], dim=-1)

    x_flat = x.permute(0, 2, 1, 3, 4).reshape(B * Z, C, H, W)
    grid3d = grid2d.unsqueeze(1).expand(B, Z, H, W, 2).reshape(B * Z, H, W, 2)
    x_warped = F.grid_sample(
        x_flat,
        grid3d,
        mode="bilinear",
        padding_mode="border",
        align_corners=True,
    )
    x_warped = x_warped.reshape(B, Z, C, H, W).permute(0, 2, 1, 3, 4)

    ink_warped = _warp_2d_tensor(target_ink, grid2d).clamp(0, 1)
    fiber_warped = _warp_2d_tensor(target_fiber, grid2d).clamp(0, 1)
    return x_warped, ink_warped, fiber_warped


# ---------------------------------------------------------------------------
# Bonus augmentations
# ---------------------------------------------------------------------------


def scroll_z_dropout(x: torch.Tensor, drop_rate: float = 0.12) -> torch.Tensor:
    """Replace random z-slices with the z-mean of the volume.

    Simulates occasional bad / corrupted z-slices. The replacement
    intensity is the per-(y,x)-column mean across z, so it preserves
    local intensity distribution while erasing structure.
    """
    if x.shape[2] < 3:
        return x
    keep = (
        torch.rand(
            (x.shape[0], 1, x.shape[2], 1, 1),
            device=x.device,
        )
        > drop_rate
    ).to(dtype=x.dtype)
    z_mean = x.mean(dim=2, keepdim=True)
    return x * keep + z_mean * (1.0 - keep)


def scroll_intensity_drift(
    x: torch.Tensor,
    slope_range: tuple[float, float] = (-0.18, 0.18),
    bias_range: tuple[float, float] = (-0.08, 0.08),
) -> torch.Tensor:
    """Apply depth-dependent multiplicative intensity scaling.

    Simulates X-ray dose / beam-hardening variations across z. Each sample
    gets its own random slope and bias.
    """
    B, C, Z, H, W = x.shape
    depth = torch.linspace(-1.0, 1.0, Z, device=x.device, dtype=x.dtype).view(
        1, 1, -1, 1, 1
    )
    slope = torch.empty((B, 1, 1, 1, 1), device=x.device, dtype=x.dtype).uniform_(
        *slope_range
    )
    bias = torch.empty((B, 1, 1, 1, 1), device=x.device, dtype=x.dtype).uniform_(
        *bias_range
    )
    return x * (1.0 + slope * depth) + bias


# ---------------------------------------------------------------------------
# Convenience composition (API-compatible with train.py's existing function)
# ---------------------------------------------------------------------------


def apply_scroll_specific_3d_augmentations(
    x: torch.Tensor,
    target_ink: torch.Tensor,
    target_fiber: torch.Tensor,
    config,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Apply each scroll augmentation independently based on probabilities
    pulled from `config`. Returns the (possibly) modified tensors clamped
    to [0, 1].

    Config attributes (all default 0.0):
      - aug_scroll_decohesion_p
      - aug_scroll_warping_p          (new in this module; not in train.py yet)
      - aug_scroll_squeeze_p
      - aug_scroll_z_dropout_p
      - aug_scroll_intensity_drift_p
    """
    if config is None:
        return x, target_ink, target_fiber

    decohesion_p = float(getattr(config, "aug_scroll_decohesion_p", 0.0))
    warping_p = float(getattr(config, "aug_scroll_warping_p", 0.0))
    squeeze_p = float(getattr(config, "aug_scroll_squeeze_p", 0.0))
    z_dropout_p = float(getattr(config, "aug_scroll_z_dropout_p", 0.0))
    intensity_p = float(getattr(config, "aug_scroll_intensity_drift_p", 0.0))

    if decohesion_p > 0 and torch.rand((), device=x.device).item() < decohesion_p:
        alpha = (
            torch.empty((), device=x.device, dtype=x.dtype).uniform_(0.15, 0.45).item()
        )
        x = scroll_decohesion(x, alpha=alpha)

    if warping_p > 0 and torch.rand((), device=x.device).item() < warping_p:
        x, target_ink, target_fiber = scroll_warping(x, target_ink, target_fiber)

    if squeeze_p > 0 and torch.rand((), device=x.device).item() < squeeze_p:
        x, target_ink, target_fiber = scroll_squeeze(x, target_ink, target_fiber)

    if z_dropout_p > 0 and torch.rand((), device=x.device).item() < z_dropout_p:
        x = scroll_z_dropout(x)

    if intensity_p > 0 and torch.rand((), device=x.device).item() < intensity_p:
        x = scroll_intensity_drift(x)

    return x, target_ink.clamp(0, 1), target_fiber.clamp(0, 1)
