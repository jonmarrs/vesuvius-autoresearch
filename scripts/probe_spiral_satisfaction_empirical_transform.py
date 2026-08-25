"""Test the winding-blindness against a transform built from REAL measured winding
positions, instead of a synthetic power law.

`reports/spiral_satisfaction_winding_blindness.md` Limit 6 says the robustness
sweep perturbs the geometry SMOOTHLY (a global radial power law), while the real
field's irregularity is LOCAL and noisy, and that the sweep's clean "safe for
alpha >= 0.60" story must not be read as bounding real local irregularity. That
limit stands as long as the only nonlinear transform ever tested is a smooth one.

This closes it without running a fit. The published PHercParis4 `winding_model/`
crossing export records, for each ray, where successive windings actually sit. The
cumulative sums of those measured inter-winding gaps ARE the real radial map along
that ray: winding k sits at ideal radius `k*dr` in an undeformed spiral, and at the
measured cumulative distance `D_k` in the scan. Interpolating between the measured
knots gives a piecewise-linear radial warp that is real, locally noisy, and
invertible, with no smoothness imposed anywhere.

    Convention, matching the pinned probes: `transform(zyx)` maps scan space to
    spiral space (villa applies it internally), and `transform.inv(zyx)` maps
    spiral space to scan space (we use it to prepare inputs). So `.inv` sends the
    ideal radius `k*dr` to the measured radius `D_k`, and `__call__` sends it back.

What this still is NOT: a real fit. No fitted spiral checkpoint is published, so
the deformation tested here is reconstructed from published winding-crossing
measurements rather than taken from a fitted model. It is a real measured radial
geometry, not a real fitted transform.

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


def run_ray(measured_radii, overrides, n_windings=1.0):
    """Score a reference and a displaced patch through villa's unmodified metric
    under a transform built from one real ray's measured winding positions."""
    dr = float(np.mean(np.diff(measured_radii)))
    ideal = np.arange(len(measured_radii), dtype=np.float64) * dr
    transform = EmpiricalRadialTransform(ideal, measured_radii)

    ref_spiral = build_synthetic_patch(dr=dr, winding=WINDING)
    moved_spiral = displace(ref_spiral, dr, n_windings=n_windings)
    ref = _to_scan_space(ref_spiral, transform)
    moved = _to_scan_space(moved_spiral, transform)

    total = int(ref.valid_quad_mask.sum().item())
    ref_f = score_with(ref, dr, overrides, transform)
    disp_f = score_with(moved, dr, overrides, transform)
    thr = overrides["satisfied_patch_quad_fraction"]
    return {
        "dr": dr,
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
        "Winding-blindness under a transform built from REAL measured winding positions"
    )
    out.append(
        "Radial warp interpolates the cumulative inter-winding distances measured along one "
        "real ray of the published PHercParis4 winding_model export. No smoothness imposed: "
        "the map is exactly as locally irregular as the measurement. This is NOT a fitted "
        "transform; no fitted spiral checkpoint is published."
    )
    out.append(
        f"Rays: {N_RAYS} requested, drawn under seed {RAY_SEED} from shard_0, each required to "
        f"carry at least {MIN_CROSSINGS} crossings at strictly consecutive winding levels."
    )
    out.append("")
    for name, rows in results:
        s = summarize(rows)
        out.append(f"=== {name} configuration ===")
        out.append(f"  rays scored                        {s['n']}")
        out.append(f"  median dr across rays (voxels)     {s['median_dr']:.4f}")
        out.append(
            f"  max local irregularity (|d2 gap|/dr) {s['max_local_irregularity']:.4f}"
        )
        out.append(f"  max |delta| over rays              {s['max_abs_delta']:.6f}")
        out.append(
            f"  rays where the VERDICT differs     {s['n_verdict_disagree']} of {s['n']}"
        )
        out.append(
            f"  rays where the REFERENCE fails     {s['n_ref_unsat']} of {s['n']}"
        )
        out.append("")
    out.append(
        "The local-irregularity column is the largest second difference of the measured gap "
        "sequence, in units of dr. It is the quantity the smooth power-law sweep structurally "
        "could not represent: a power law has a slowly varying derivative by construction, "
        "while these knots wander gap to gap."
    )
    return "\n".join(out) + "\n"


def main():
    shard = load_shard()
    rays = usable_rays(shard)
    if not rays:
        raise SystemExit("no usable rays found; check the shard path and filters")
    results = []
    for name, cfg in (("reporting", REPORTING), ("splicing", SPLICING)):
        results.append((name, [run_ray(radii, cfg) for _, radii in rays]))
    print(format_report(results))


if __name__ == "__main__":
    main()
