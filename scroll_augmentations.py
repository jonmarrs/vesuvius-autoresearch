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
from dataclasses import dataclass

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


def scroll_sheet_compression(
    x: torch.Tensor,
    compression_strength: tuple[float, float] = (0.1, 0.3),
) -> torch.Tensor:
    """Simulates scroll sheets being closer together by compressing low-intensity
    (gap) regions along Z. Adapted from Villa's SheetCompressionTransform.
    """
    B, C, Z, H, W = x.shape
    device = x.device
    dtype = x.dtype

    strength = (
        torch.empty((), dtype=torch.float32, device=device)
        .uniform_(*compression_strength)
        .item()
    )

    x_mean = x.mean(dim=1, keepdim=True)
    smoothed = F.avg_pool3d(x_mean, kernel_size=3, stride=1, padding=1)

    s_min = smoothed.amin(dim=(2, 3, 4), keepdim=True)
    s_max = smoothed.amax(dim=(2, 3, 4), keepdim=True)
    denom = (s_max - s_min).clamp(min=1e-8)
    gap_weight = 1.0 - ((smoothed - s_min) / denom)

    displacement = torch.cumsum(gap_weight, dim=2) * strength
    displacement = F.avg_pool3d(
        displacement, kernel_size=(1, 5, 5), stride=1, padding=(0, 2, 2)
    )
    z_disp_norm = displacement / (Z / 2.0)

    z_coords = torch.linspace(-1, 1, Z, device=device, dtype=dtype)
    y_coords = torch.linspace(-1, 1, H, device=device, dtype=dtype)
    x_coords = torch.linspace(-1, 1, W, device=device, dtype=dtype)

    grid_z, grid_y, grid_x = torch.meshgrid(z_coords, y_coords, x_coords, indexing="ij")
    grid_z = grid_z.view(1, Z, H, W).expand(B, Z, H, W)
    grid_y = grid_y.view(1, Z, H, W).expand(B, Z, H, W)
    grid_x = grid_x.view(1, Z, H, W).expand(B, Z, H, W)

    grid_z_shifted = grid_z - z_disp_norm.squeeze(1)
    grid = torch.stack([grid_x, grid_y, grid_z_shifted], dim=-1)

    return F.grid_sample(
        x, grid, mode="bilinear", padding_mode="border", align_corners=True
    )


def scroll_thick_slice(
    x: torch.Tensor,
    target_ink: torch.Tensor,
    target_fiber: torch.Tensor,
    scale_range: tuple[float, float] = (0.25, 0.6),
    candidate_axes: tuple[int, ...] = (0, 1, 2),
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Simulates thicker slice acquisition by downsampling and restoring along a single spatial axis.
    Adapted from Villa's SimulateThickSliceTransform.
    """
    B, C, Z, H, W = x.shape
    spatial_shape = [Z, H, W]
    valid_axes = [ax for ax in candidate_axes if 0 <= ax < 3]
    if not valid_axes:
        return x, target_ink, target_fiber

    chosen_axis = valid_axes[torch.randint(len(valid_axes), (), device=x.device).item()]
    scale = (
        torch.empty((), dtype=torch.float32, device=x.device)
        .uniform_(*scale_range)
        .item()
    )

    target_shape = list(spatial_shape)
    target_dim = max(1, int(round(target_shape[chosen_axis] * scale)))

    if target_dim == target_shape[chosen_axis]:
        return x, target_ink, target_fiber

    target_shape[chosen_axis] = target_dim

    down_x = F.interpolate(x, size=target_shape, mode="nearest")
    res_x = F.interpolate(down_x, size=spatial_shape, mode="nearest")

    res_ink = target_ink
    res_fib = target_fiber
    if chosen_axis in (1, 2):
        t_shape_2d = [target_shape[1], target_shape[2]]
        s_shape_2d = [H, W]

        down_ink = F.interpolate(target_ink, size=t_shape_2d, mode="nearest")
        res_ink = F.interpolate(down_ink, size=s_shape_2d, mode="nearest")

        down_fib = F.interpolate(target_fiber, size=t_shape_2d, mode="nearest")
        res_fib = F.interpolate(down_fib, size=s_shape_2d, mode="nearest")

    return res_x, res_ink, res_fib


def scroll_rician_noise(
    x: torch.Tensor, noise_variance: tuple[float, float] = (0.0, 0.1)
) -> torch.Tensor:
    """Adds Rician noise typical of MRI/CT magnitude data.
    Adapted from Villa's RicianNoiseTransform.
    """
    variance = (
        torch.empty((), dtype=torch.float32, device=x.device)
        .uniform_(*noise_variance)
        .item()
    )
    if variance <= 0:
        return x
    std_dev = math.sqrt(variance)
    real_noise = torch.randn_like(x) * std_dev
    imag_noise = torch.randn_like(x) * std_dev
    return torch.sqrt((x + real_noise) ** 2 + imag_noise**2)


def scroll_blank_rectangles(
    x: torch.Tensor, num_rectangles: tuple[int, int] = (1, 3), max_size: int = 16
) -> torch.Tensor:
    """Overwrites random 3D regions with the mean intensity.
    Adapted from Villa's BlankRectangleTransform.
    """
    B, C, Z, H, W = x.shape
    n_rect = torch.randint(
        num_rectangles[0], num_rectangles[1] + 1, (), device=x.device
    ).item()
    res_x = x.clone()
    for _ in range(n_rect):
        sz_z = torch.randint(1, min(Z, max_size) + 1, (), device=x.device).item()
        sz_y = torch.randint(1, min(H, max_size) + 1, (), device=x.device).item()
        sz_x = torch.randint(1, min(W, max_size) + 1, (), device=x.device).item()

        z0 = torch.randint(0, max(1, Z - sz_z + 1), (), device=x.device).item()
        y0 = torch.randint(0, max(1, H - sz_y + 1), (), device=x.device).item()
        x0 = torch.randint(0, max(1, W - sz_x + 1), (), device=x.device).item()

        mean_val = res_x[:, :, z0 : z0 + sz_z, y0 : y0 + sz_y, x0 : x0 + sz_x].mean()
        res_x[:, :, z0 : z0 + sz_z, y0 : y0 + sz_y, x0 : x0 + sz_x] = mean_val
    return res_x


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

    # New Villa Augmentations
    sheet_comp_p = float(getattr(config, "aug_scroll_sheet_compression_p", 0.0))
    thick_slice_p = float(getattr(config, "aug_scroll_thick_slice_p", 0.0))
    rician_noise_p = float(getattr(config, "aug_scroll_rician_noise_p", 0.0))
    blank_rects_p = float(getattr(config, "aug_scroll_blank_rectangles_p", 0.0))

    if sheet_comp_p > 0 and torch.rand((), device=x.device).item() < sheet_comp_p:
        x = scroll_sheet_compression(x)

    if thick_slice_p > 0 and torch.rand((), device=x.device).item() < thick_slice_p:
        x, target_ink, target_fiber = scroll_thick_slice(x, target_ink, target_fiber)

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

    if rician_noise_p > 0 and torch.rand((), device=x.device).item() < rician_noise_p:
        x = scroll_rician_noise(x)

    if blank_rects_p > 0 and torch.rand((), device=x.device).item() < blank_rects_p:
        x = scroll_blank_rectangles(x)

    return x, target_ink.clamp(0, 1), target_fiber.clamp(0, 1)


# ---------------------------------------------------------------------------
# Reusable public API (decoupled from the autoresearch ExperimentConfig)
# ---------------------------------------------------------------------------


@dataclass
class ScrollAugProbs:
    """Per-augmentation application probabilities (each in [0, 1]).

    Decoupled from the autoresearch ExperimentConfig so external callers can
    use this library directly.
    """

    decohesion: float = 0.0
    warping: float = 0.0
    squeeze: float = 0.0
    z_dropout: float = 0.0
    intensity_drift: float = 0.0
    sheet_compression: float = 0.0
    thick_slice: float = 0.0
    rician_noise: float = 0.0
    blank_rectangles: float = 0.0


def _fires(p: float, device) -> bool:
    return p > 0.0 and torch.rand((), device=device).item() < p


def apply_scroll_augmentations(x, target_ink, target_fiber, probs: ScrollAugProbs):
    """Apply each scroll augmentation independently with its probability.

    x: [B,C,Z,H,W]; target_ink: [B,1,H,W]; target_fiber: [B,1,1,H,W].
    Geometric augmentations (warping, squeeze, thick_slice) also transform the
    targets. Returns the (possibly) modified tensors with labels clamped to
    [0, 1].
    """
    dev = x.device
    if _fires(probs.sheet_compression, dev):
        x = scroll_sheet_compression(x)
    if _fires(probs.thick_slice, dev):
        x, target_ink, target_fiber = scroll_thick_slice(x, target_ink, target_fiber)
    if _fires(probs.decohesion, dev):
        alpha = torch.empty((), device=dev, dtype=x.dtype).uniform_(0.15, 0.45).item()
        x = scroll_decohesion(x, alpha=alpha)
    if _fires(probs.warping, dev):
        x, target_ink, target_fiber = scroll_warping(x, target_ink, target_fiber)
    if _fires(probs.squeeze, dev):
        x, target_ink, target_fiber = scroll_squeeze(x, target_ink, target_fiber)
    if _fires(probs.z_dropout, dev):
        x = scroll_z_dropout(x)
    if _fires(probs.intensity_drift, dev):
        x = scroll_intensity_drift(x)
    if _fires(probs.rician_noise, dev):
        x = scroll_rician_noise(x)
    if _fires(probs.blank_rectangles, dev):
        x = scroll_blank_rectangles(x)
    return x, target_ink.clamp(0, 1), target_fiber.clamp(0, 1)
