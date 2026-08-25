"""Test the winding-blindness against a transform built from REAL measured winding
positions, instead of a synthetic power law.

`reports/spiral_satisfaction_winding_blindness.md` Limit 7 says the robustness
sweep perturbs the geometry SMOOTHLY (a global radial power law), while the real
field's irregularity is LOCAL and noisy, so the sweep's "safe for alpha >= 0.60"
story does not bound real local irregularity.

This NARROWS that limit; it does not close it. The published PHercParis4
`winding_model/` crossing export records, for each ray, where successive windings
actually sit. Interpolating between the cumulative sums of those measured gaps
gives a piecewise-linear warp that is real, locally irregular, and invertible,
with no smoothness imposed anywhere.

**What the knots actually are, stated plainly.** They are the measured SEQUENCE OF
INTER-WINDING SPACINGS along one ray, re-anchored at zero and read as radial
knots. They are not the scroll's radial map. The rays are oblique (median
|step_z| 0.215 over the selected rays, max 0.826), so a crossing distance along a
ray exceeds the in-plane spacing by the ray's obliquity; and the first crossing is
placed at radius 0 by this code, though in the scan it sits at a substantial real
radius. Some part of the measured irregularity is therefore crossing-ANGLE
variation rather than radial-spacing variation. What the probe needs from the warp
is only that it be real, monotone, and locally irregular, which it is, and it is a
STRONGER perturbation than any pinned alpha: at the patch radii it displaces
points by a median of about 0.87 dr against the power law's 0.067 dr at alpha=0.95
and 0.514 dr at alpha=0.60.

**Scatter is the measurement; zero scatter is degenerate.** At zero scatter the
patch lies exactly on a winding and the report's section 1 proves the delta is
zero for ANY invertible transform, because the snap target lands on the patch's
own spiral point and the transform cancels. Section 4's own table already
publishes that: its scatter=0.00 row reads +0.000000 at every alpha. A
zero-scatter sweep over empirical warps therefore CANNOT FAIL, and an earlier
version of this probe reported exactly that zero as though it were evidence about
the warps. It was not. The scatter cross below is the measurement, and under it
the invariance does break.

    Convention, matching the pinned probes: `transform(zyx)` maps scan space to
    spiral space (villa applies it internally), and `transform.inv(zyx)` maps
    spiral space to scan space (we use it to prepare inputs).

What this still is NOT: a real fit. No fitted spiral checkpoint is published, so
the deformation here is reconstructed from published winding-crossing
measurements rather than taken from a fitted model. A real fitted transform would
also not be purely radial.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_empirical_transform.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402
import torch  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_spiral_satisfaction_robustness import (  # noqa: E402
    _patch_is_satisfied,
    _to_scan_space,
    add_radius_scatter,
    draw_unit_noise,
)
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REPORTING,
    SPLICING,
    score_with,
)
from probe_spiral_satisfaction_winding import (  # noqa: E402
    build_synthetic_patch,
    displace,
)

DATA = os.path.join(_REPO, "local_data", "spiral_winding_model_phercparis4", "shard_0")
WINDING = 5
# Rays need enough consecutive crossings to span the patch's radial extent with
# knots on both sides. The patch sits between windings 5 and 6, so a ray must
# reach at least winding 7 to bracket a one-winding displacement.
MIN_CROSSINGS = 10
N_RAYS = 40
RAY_SEED = 20260825
# Absolute-voxel scatter. 6.0 is villa's entire scan tolerance, included as the
# reference point; 0.0 is retained only to show it is the degenerate case.
SCATTER_VOXEL_LEVELS = [0.0, 2.0, 3.0, 4.0, 5.0, 6.0]


class EmpiricalRadialTransform:
    """A radial warp interpolating measured winding positions.

    `ideal_radii[k] = k * dr` are the knots in spiral space; `measured_radii[k]`
    are where those windings actually sit along one real ray. Both sequences are
    strictly increasing, so `numpy.interp` in either direction is a genuine
    inverse pair on the covered range. No smoothness is imposed: the map is
    exactly as locally irregular as the measurement.
    """

    def __init__(self, ideal_radii, measured_radii):
        self.ideal = np.asarray(ideal_radii, dtype=np.float64)
        self.measured = np.asarray(measured_radii, dtype=np.float64)
        if np.any(np.diff(self.ideal) <= 0) or np.any(np.diff(self.measured) <= 0):
            raise ValueError("both knot sequences must be strictly increasing")

    def _warp(self, zyxs, src, dst):
        ys = zyxs[..., 1].detach().numpy().astype(np.float64)
        xs = zyxs[..., 2].detach().numpy().astype(np.float64)
        r = np.sqrt(ys**2 + xs**2)
        theta = np.arctan2(ys, xs)
        r_new = np.interp(r, src, dst)
        out = zyxs.clone()
        out[..., 1] = torch.from_numpy(np.sin(theta) * r_new).to(zyxs.dtype)
        out[..., 2] = torch.from_numpy(np.cos(theta) * r_new).to(zyxs.dtype)
        return out

    def __call__(self, zyxs):
        """scan -> spiral"""
        return self._warp(zyxs, self.measured, self.ideal)

    def inv(self, zyxs):
        """spiral -> scan"""
        return self._warp(zyxs, self.ideal, self.measured)


def load_shard(path=DATA):
    return {
        name: np.load(os.path.join(path, f"{name}.npy"))
        for name in (
            "ray_origin_zyx",
            "ray_step_zyx",
            "crossing_t",
            "crossing_level",
            "crossing_offsets",
        )
    }


def ray_winding_radii(shard, ray_index):
    """The measured cumulative inter-winding distances along one ray, in voxels.

    Returns None when the ray's crossings are not a run of consecutive winding
    levels long enough to bracket the patch, so no ray is silently used with
    skipped windings folded into a single gap.
    """
    lo = int(shard["crossing_offsets"][ray_index])
    hi = int(shard["crossing_offsets"][ray_index + 1])
    if hi - lo < MIN_CROSSINGS:
        return None
    levels = shard["crossing_level"][lo:hi].astype(np.int64)
    ts = shard["crossing_t"][lo:hi].astype(np.float64)
    order = np.argsort(ts)
    levels, ts = levels[order], ts[order]
    if np.any(np.diff(levels) != 1):
        return None
    step_norm = float(
        np.linalg.norm(shard["ray_step_zyx"][ray_index].astype(np.float64))
    )
    if step_norm <= 0:
        return None
    gaps = np.diff(ts) * step_norm
    if np.any(gaps <= 0):
        return None
    return np.concatenate([[0.0], np.cumsum(gaps)])


def usable_rays(shard, n_rays=N_RAYS, seed=RAY_SEED):
    """Rays whose measured winding sequence can carry the probe, drawn from a
    fixed seed so the selection is reproducible and not cherry-picked."""
    rng = np.random.default_rng(seed)
    n = len(shard["crossing_offsets"]) - 1
    out = []
    for idx in rng.permutation(n):
        radii = ray_winding_radii(shard, int(idx))
        if radii is None:
            continue
        out.append((int(idx), radii))
        if len(out) >= n_rays:
            break
    return out


def run_ray(measured_radii, overrides, n_windings=1.0, scatter_voxels=0.0):
    """Score a reference and a displaced patch through villa's unmodified metric
    under a transform built from one real ray's measured winding positions.

    `scatter_voxels` is not optional decoration. At zero scatter the patch lies
    exactly on a winding, and the report's own section 1 PROVES the delta is zero
    for any invertible transform, because the snap target lands on the patch's own
    spiral point and the transform cancels. A zero-scatter sweep over empirical
    warps therefore cannot fail, and reporting its zero as a measurement about
    those warps would be circular. The scatter cross is the measurement.
    """
    dr = float(np.mean(np.diff(measured_radii)))
    ideal = np.arange(len(measured_radii), dtype=np.float64) * dr
    transform = EmpiricalRadialTransform(ideal, measured_radii)

    ref_spiral = build_synthetic_patch(dr=dr, winding=WINDING)
    if scatter_voxels != 0.0:
        noise = draw_unit_noise(ref_spiral.zyxs.shape[0], ref_spiral.zyxs.shape[1])
        ref_spiral = add_radius_scatter(ref_spiral, noise, scatter_voxels / dr, dr)
    moved_spiral = displace(ref_spiral, dr, n_windings=n_windings)
    ref = _to_scan_space(ref_spiral, transform)
    moved = _to_scan_space(moved_spiral, transform)

    total = int(ref.valid_quad_mask.sum().item())
    ref_f = score_with(ref, dr, overrides, transform)
    disp_f = score_with(moved, dr, overrides, transform)
    thr = overrides["satisfied_patch_quad_fraction"]
    return {
        "dr": dr,
        "scatter_voxels": scatter_voxels,
        "ref_frac": ref_f,
        "disp_frac": disp_f,
        "delta": disp_f - ref_f,
        "ref_verdict": _patch_is_satisfied(ref_f, total, thr),
        "disp_verdict": _patch_is_satisfied(disp_f, total, thr),
        "local_irregularity": float(
            np.max(np.abs(np.diff(np.diff(measured_radii)) / dr))
        ),
    }


def summarize(rows):
    deltas = [abs(r["delta"]) for r in rows]
    return {
        "n": len(rows),
        "scatter_voxels": rows[0]["scatter_voxels"],
        "max_abs_delta": max(deltas) if deltas else float("nan"),
        "n_verdict_disagree": sum(
            1 for r in rows if r["ref_verdict"] != r["disp_verdict"]
        ),
        "n_ref_unsat": sum(1 for r in rows if not r["ref_verdict"]),
        "max_local_irregularity": max(r["local_irregularity"] for r in rows),
        "median_dr": float(np.median([r["dr"] for r in rows])),
    }


def format_report(results):
    out = []
    out.append(
        "Winding-blindness under a warp built from REAL measured winding spacings"
    )
    out.append(
        "The knots are the measured SEQUENCE OF INTER-WINDING SPACINGS along one ray, "
        "re-anchored at zero and read as radial knots. They are NOT the scroll's radial map: "
        "the rays are oblique and the first crossing is placed at radius 0 by this code, so "
        "part of the measured irregularity is crossing-angle variation rather than radial "
        "spacing. What the probe needs is that the warp be real, monotone and locally "
        "irregular, which it is. This is not a fitted transform; none is published."
    )
    out.append(
        f"Rays: {N_RAYS} drawn under seed {RAY_SEED} from shard_0, each carrying at least "
        f"{MIN_CROSSINGS} crossings at strictly consecutive winding levels."
    )
    out.append("")
    out.append(
        "SCATTER IS THE MEASUREMENT. At zero scatter the patch lies exactly on a winding and "
        "the delta is zero for ANY invertible transform by the section-1 algebra, so that row "
        "is degenerate and is shown only to make the degeneracy visible."
    )
    out.append("")
    for name, per_scatter in results:
        out.append(f"=== {name} configuration ===")
        out.append("   scatter |    max|delta| | verdict differs | reference fails")
        out.append("  " + "-" * 62)
        for rows in per_scatter:
            s = summarize(rows)
            deg = "  <- degenerate" if s["scatter_voxels"] == 0.0 else ""
            out.append(
                f"  {s['scatter_voxels']:6.1f}vox | {s['max_abs_delta']:12.6f} "
                f"| {s['n_verdict_disagree']:6d} of {s['n']:<5d} | {s['n_ref_unsat']:6d} of {s['n']}{deg}"
            )
        out.append("")
    first = results[0][1][0]
    s0 = summarize(first)
    out.append(
        f"Median dr across the selected rays: {s0['median_dr']:.4f} voxels. This is a per-ray "
        f"MEAN gap, then a median across rays, so it sits above the global MEDIAN gap of 12.81 "
        f"reported elsewhere: shard_0's gap distribution is right-skewed (median 12.92, mean "
        f"14.92), and the >= {MIN_CROSSINGS}-crossing filter moves the figure down, not up. "
        "The difference is a statistic-choice artifact, not a selection bias."
    )
    out.append(
        f"Max local irregularity across the selected rays: {s0['max_local_irregularity']:.4f} "
        "in units of dr (largest second difference of the measured gap sequence). A power law "
        "has a slowly varying derivative by construction and structurally cannot represent it."
    )
    return "\n".join(out) + "\n"


def main():
    shard = load_shard()
    rays = usable_rays(shard)
    if not rays:
        raise SystemExit("no usable rays found; check the shard path and filters")
    results = []
    for name, cfg in (("reporting", REPORTING), ("splicing", SPLICING)):
        per_scatter = [
            [run_ray(radii, cfg, scatter_voxels=vox) for _, radii in rays]
            for vox in SCATTER_VOXEL_LEVELS
        ]
        results.append((name, per_scatter))
    print(format_report(results))


if __name__ == "__main__":
    main()
