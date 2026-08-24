"""Probe whether villa's spiral-fit satisfaction metric can detect a patch placed
exactly one winding away from where it belongs.

`satisfaction_metrics.get_patch_satisfied_areas` decides whether a patch is
"satisfied" against a target winding it derives from the patch's OWN median
shifted-radius (snapped to the nearest integer winding). It never reads the
absolute winding annotations that `fit_spiral.get_patch_abs_winding_loss` uses to
fit. This script measures the consequence:

    reference patch, on winding 5      -> satisfied fraction 1.00
    displaced by exactly 1 winding     -> satisfied fraction 1.00   <- blind
    displaced by 0.5 winding (control) -> satisfied fraction drops  <- metric works

The 0.5-winding control is what makes the null interpretable: it shows the
instrument is capable of reporting dissatisfaction at all.

The metric ANDs two independent per-quad conditions -- a spiral-space
shifted-radius tolerance (0.45*dr = 45 units at DR=100) and an absolute
scan-space distance tolerance (6.0 voxels, unscaled by dr). `score_conditions`
reads each one out separately (see its docstring for how, honestly, without
reimplementing villa's arithmetic). At a whole-winding offset BOTH conditions
independently read 1.0 -- the blind spot is not an artifact of one condition
saturating while the other actually fired.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_winding.py
"""

import os
import sys
import types
from dataclasses import dataclass

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np
import torch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPIRAL = os.path.join(_REPO, "villa", "volume-cartographer", "scripts", "spiral")
sys.path.insert(0, _SPIRAL)


def _install_villa_import_stubs():
    """satisfaction_metrics.py transitively imports tracks.py and visualization.py.
    Neither imports cleanly in this project's environment, and villa is a pinned
    submodule this probe must not edit:

    - tracks.py does `import kornia` at module scope, but kornia is not an
      installed dependency here. It is used only inside
      `render_spiral_on_tracks_for_slice`, a rendering helper that
      `get_patch_satisfied_areas` never calls.
    - visualization.py fails to *parse* on this project's pinned Python 3.10
      (spiral/pyproject.toml itself requires >=3.14): it uses PEP 646
      subscript-unpacking (`slice[*marker_yx...]`), a 3.11+ construct. It
      exports `save_overlay`, which `satisfaction_metrics.py` only calls from
      `save_overlay_and_print_satisfaction`, not from `get_patch_satisfied_areas`.

    Both stubs are installed in sys.modules before the real import so the
    interpreter never has to load either broken module.
    """
    if "kornia" not in sys.modules:
        kornia_stub = types.ModuleType("kornia")
        kornia_stub.color = types.ModuleType("kornia.color")
        sys.modules["kornia"] = kornia_stub
        sys.modules["kornia.color"] = kornia_stub.color

    if "visualization" not in sys.modules:

        def _save_overlay_unavailable(*args, **kwargs):
            raise NotImplementedError(
                "visualization.save_overlay is stubbed out for this probe: the "
                "real module does not parse under this project's pinned Python "
                "3.10, and get_patch_satisfied_areas never calls it"
            )

        visualization_stub = types.ModuleType("visualization")
        visualization_stub.save_overlay = _save_overlay_unavailable
        sys.modules["visualization"] = visualization_stub


_install_villa_import_stubs()

from satisfaction_metrics import get_patch_satisfied_areas  # noqa: E402

DR = 100.0
Z_BEGIN = 0
Z_END = 100000


class IdentityTransform:
    """The synthetic scroll is built directly in spiral space, so scan == spiral."""

    def __call__(self, zyx):
        return zyx

    def inv(self, zyx):
        return zyx


@dataclass
class SyntheticPatch:
    zyxs: torch.Tensor  # (H, W, 3) float32
    valid_quad_mask: torch.Tensor  # (H-1, W-1) bool
    area: float


def build_synthetic_patch(
    dr, winding, n_rows=12, n_cols=16, theta0=0.30, theta1=1.30, z0=1000.0, dz=2.0
):
    """A patch lying exactly on `winding`.

    get_theta_and_radii defines shifted_radius = radius - theta/(2pi)*dr, so a
    point with radius = winding*dr + theta/(2pi)*dr has shifted_radius exactly
    winding*dr. theta stays well inside (0, 2pi) so no theta=0 seam is crossed.
    """
    thetas = torch.linspace(theta0, theta1, n_cols, dtype=torch.float32)
    radii = winding * dr + thetas / (2 * np.pi) * dr
    ys = torch.sin(thetas) * radii
    xs = torch.cos(thetas) * radii
    zs = z0 + dz * torch.arange(n_rows, dtype=torch.float32)

    zyxs = torch.empty([n_rows, n_cols, 3], dtype=torch.float32)
    zyxs[..., 0] = zs[:, None]
    zyxs[..., 1] = ys[None, :]
    zyxs[..., 2] = xs[None, :]
    return SyntheticPatch(
        zyxs=zyxs,
        valid_quad_mask=torch.ones([n_rows - 1, n_cols - 1], dtype=torch.bool),
        area=1.0,
    )


def displace(patch, dr, n_windings):
    """Move every point radially outward by n_windings * dr, at fixed theta and z.

    This is the physically meaningful displacement: it places the patch where the
    adjacent wrap sits. Fractional n_windings are used for the control.
    """
    zyxs = patch.zyxs.clone()
    ys = zyxs[..., 1]
    xs = zyxs[..., 2]
    radii = torch.sqrt(ys**2 + xs**2)
    thetas = torch.arctan2(ys, xs) % (2 * np.pi)
    new_radii = radii + n_windings * dr
    zyxs[..., 1] = torch.sin(thetas) * new_radii
    zyxs[..., 2] = torch.cos(thetas) * new_radii
    return SyntheticPatch(
        zyxs=zyxs,
        valid_quad_mask=patch.valid_quad_mask.clone(),
        area=patch.area,
    )


def score(patch, dr):
    """Satisfied-quad fraction under villa's unmodified metric."""
    _, _, _, masks, _, _ = get_patch_satisfied_areas(
        IdentityTransform(),
        torch.tensor(dr),
        [patch],
        Z_BEGIN,
        Z_END,
    )
    mask = masks[0]
    total = int(patch.valid_quad_mask.sum().item())
    return int(mask.sum().item()) / max(total, 1)


# A tolerance override large enough that the condition it gates can never
# bind (spiral_tolerance = dr * satisfaction_radius_tolerance, and
# satisfaction_distance_tolerance is itself a voxel distance -- either way,
# 1e9 dwarfs every displacement this probe exercises).
_NEUTRAL_TOLERANCE = 1e9


def score_conditions(patch, dr):
    """The two satisfaction conditions villa's metric ANDs together, read out
    separately, plus their combination (which must equal `score(patch, dr)`).

    get_patch_satisfied_areas requires a quad to pass BOTH (a) a spiral-space
    shifted-radius tolerance (`satisfaction_radius_tolerance * dr`) and (b) an
    absolute scan-space distance tolerance (`satisfaction_distance_tolerance`
    voxels) before counting it satisfied; it never exposes the two masks
    separately. Rather than reimplementing that arithmetic here -- which would
    make this probe measure its own copy of the logic instead of villa's --
    we call the real function three times, using its `metrics_overrides` hook
    to neutralize one tolerance at a time so only the other condition can
    still reject a quad.
    """
    total = int(patch.valid_quad_mask.sum().item())

    def _fraction(overrides):
        _, _, _, masks, _, _ = get_patch_satisfied_areas(
            IdentityTransform(),
            torch.tensor(dr),
            [patch],
            Z_BEGIN,
            Z_END,
            metrics_overrides=overrides,
        )
        return int(masks[0].sum().item()) / max(total, 1)

    spiral_fraction = _fraction({"satisfaction_distance_tolerance": _NEUTRAL_TOLERANCE})
    scan_fraction = _fraction({"satisfaction_radius_tolerance": _NEUTRAL_TOLERANCE})
    combined_fraction = score(patch, dr)
    return spiral_fraction, scan_fraction, combined_fraction


def main():
    ref = build_synthetic_patch(dr=DR, winding=5)
    ref_score = score(ref, DR)
    print(f"reference (winding 5)          satisfied = {ref_score:.6f}")

    moved = displace(ref, DR, n_windings=1)
    moved_score = score(moved, DR)
    print(f"displaced by 1 winding         satisfied = {moved_score:.6f}")
    print(f"delta                                    = {moved_score - ref_score:+.6e}")

    print()
    print("control sweep (fractional displacements):")
    for frac in [0.0, 0.25, 0.40, 0.50, 0.60, 0.75, 1.0, 2.0]:
        s = score(displace(ref, DR, n_windings=frac), DR)
        print(f"  {frac:5.2f} winding  satisfied = {s:.6f}")

    print()
    print(
        "control sweep, by condition (spiral-space 0.45*dr=45 units vs "
        "scan-space 6.0 voxels absolute):"
    )
    print(f"  {'winding':>7}  {'spiral':>8}  {'scan':>8}  {'combined':>8}")
    for frac in [0.0, 0.25, 0.40, 0.50, 0.60, 0.75, 1.0, 2.0]:
        spiral_f, scan_f, combined_f = score_conditions(
            displace(ref, DR, n_windings=frac), DR
        )
        print(f"  {frac:7.2f}  {spiral_f:8.6f}  {scan_f:8.6f}  {combined_f:8.6f}")


if __name__ == "__main__":
    main()
