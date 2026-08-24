"""Measure the real inter-winding nonlinearity of PHercParis4 from published
winding-inference ray-crossing data, to check whether the radial power-law
`alpha` used in `probe_spiral_satisfaction_robustness.py` is a realistic
model of the scroll's actual scan<->spiral geometry.

Background (see reports/spiral_satisfaction_winding_robustness.txt)
---------------------------------------------------------------------
The robustness probe found villa's spiral-fit satisfaction metric's
whole-winding blindness survives comfortably on a pinned sweep grid
`alpha in [1.0, 0.95, 0.90, 0.80, 0.60]` (worst case |delta| = 0.042), but
informal unpinned probing at `alpha = 0.2` drove the invariant break to
about -0.36. Nobody had measured how nonlinear a REAL scroll's winding
geometry actually is. This script measures it directly from published
ray-crossing data (not synthetic).

Data and verified semantics
----------------------------
Source: https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/winding_model/
(manifest.json at the root, plus shard_0 .. shard_6, each with its own
manifest.json + 6 arrays). All arrays are read exactly as documented in the
per-shard manifest; nothing below is inferred beyond what direct inspection
of the downloaded shard_0 arrays confirmed:

- `ray_step_zyx[i]` is very close to a unit vector (observed norms in
  [0.99999994, 1.0] across shard_0) -- so `crossing_t` is (to float32
  precision) already a physical scale-0-voxel distance along the ray, but
  this script still multiplies by the step norm rather than assuming it is
  exactly 1, per the task's stated gap formula.
- `crossing_level` increases by EXACTLY +1 between every pair of
  consecutive-in-t crossings on the same ray: verified exhaustively across
  all 3,905,142 crossings of shard_0 (3,683,057 within-ray adjacent pairs,
  100% had level-diff == +1, 0% had a skip). Non-adjacent-level exclusion
  logic is still implemented and exercised by the tests, and shard-by-shard
  exclusion counts are reported below in case a later shard differs.
- `crossing_t` is strictly increasing within each ray in the raw file order
  (verified: 0 of 3,683,057 within-ray adjacent t-diffs were <= 0), so no
  crossings needed re-sorting for shard_0 -- but this script still sorts by
  t within each ray defensively (see `_sort_within_ray`), because "adjacent"
  is defined physically (by position along the ray), not by array order.
- `crossing_level == 0` occurs at `crossing_t == anchor_sample` (192.0 in
  this dataset's top-level manifest) EXACTLY, for every one of 20 randomly
  sampled rays checked by hand. Combined with `seed_winding[i]` (the
  absolute physical winding number the ray was seeded from, per
  `source_attributes` in the root manifest), this gives a VERIFIED absolute
  winding number for every crossing:

      absolute_winding(ray, crossing) = seed_winding[ray] + crossing_level[ray, crossing]

  This is used below only for the equivalent-alpha calculation (see that
  section's docstring) -- the gap and ratio measurements themselves need no
  absolute winding number at all, only within-ray relative order.

Do NOT edit anything under villa/. Do not commit downloaded data (already
covered by the repo .gitignore's `local_data/` entry).

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/measure_real_winding_nonlinearity.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from dataclasses import dataclass, field

import numpy as np

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(_REPO, "local_data", "spiral_winding_model_phercparis4")
REPORT_PATH = os.path.join(_REPO, "reports", "real_winding_nonlinearity.txt")
DATASET_URL = (
    "https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/winding_model"
)
SHARD_NAMES = [f"shard_{i}" for i in range(7)]
ARRAY_FILES = [
    "ray_origin_zyx.npy",
    "ray_step_zyx.npy",
    "crossing_t.npy",
    "crossing_level.npy",
    "crossing_offsets.npy",
    "seed_winding.npy",
]

STEP_NORM_EPS = 1e-9  # below this a ray's direction vector is treated as degenerate
GAP_EPS = 1e-9  # below this a computed gap is treated as degenerate (duplicate t)

# Bracket for the equivalent-alpha numeric inversion (see EquivalentAlpha
# section below). Wide enough to cover the pinned sweep grid (down to 0.60)
# and the informally-probed breaking regime (0.2) with margin on both sides.
ALPHA_BRACKET_LO = 0.02
ALPHA_BRACKET_HI = 50.0
ALPHA_BISECTION_ITERS = (
    60  # log2((log(50)-log(0.02)) / 1e-12) ~= 53; 60 is a safety margin
)

QUANTILE_LEVELS = [0.05, 0.25, 0.50, 0.75, 0.95]


# ---------------------------------------------------------------------------
# Download + integrity verification
# ---------------------------------------------------------------------------


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with urllib.request.urlopen(url, timeout=180) as resp, open(tmp, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    os.replace(tmp, dest)


def ensure_manifest(shard: str | None = None) -> dict:
    """Download (if missing) and return the manifest.json at the dataset root,
    or for a given shard. Does not verify its own hash (manifests are not
    self-describing); shard array files ARE verified against it below."""
    if shard is None:
        url = f"{DATASET_URL}/manifest.json"
        dest = os.path.join(DATA_ROOT, "manifest.json")
    else:
        url = f"{DATASET_URL}/{shard}/manifest.json"
        dest = os.path.join(DATA_ROOT, shard, "manifest.json")
    if not os.path.exists(dest):
        download_file(url, dest)
    with open(dest) as f:
        return json.load(f)


class ShardIntegrityError(RuntimeError):
    """Raised when a downloaded shard array's sha256 does not match its
    manifest entry. This script never proceeds past a mismatch silently."""


def ensure_shard_arrays(shard: str) -> dict:
    """Download (if missing) every array file for `shard`, verify each one's
    sha256 against the shard's own manifest.json, and return the manifest's
    `arrays` dict. Raises ShardIntegrityError on any mismatch -- this is the
    task's binding requirement to "verify the shard sha256 values in the
    manifests against what you download; report any mismatch rather than
    proceeding silently."."""
    manifest = ensure_manifest(shard)
    arrays = manifest["arrays"]
    shard_dir = os.path.join(DATA_ROOT, shard)
    for name, meta in arrays.items():
        dest = os.path.join(shard_dir, meta["file"])
        url = f"{DATASET_URL}/{shard}/{meta['file']}"
        if not os.path.exists(dest):
            download_file(url, dest)
        actual = sha256_of_file(dest)
        expected = meta["sha256"]
        if actual != expected:
            raise ShardIntegrityError(
                f"{shard}/{meta['file']}: sha256 mismatch "
                f"(expected {expected}, got {actual})"
            )
    return arrays


def load_shard(shard: str) -> dict:
    """Ensure `shard`'s files are present and verified, then load its six
    arrays into memory as a dict keyed by the manifest's array names."""
    arrays_meta = ensure_shard_arrays(shard)
    shard_dir = os.path.join(DATA_ROOT, shard)
    out = {}
    for name, meta in arrays_meta.items():
        out[name] = np.load(os.path.join(shard_dir, meta["file"]))
    return out


# ---------------------------------------------------------------------------
# Gap / ratio computation
# ---------------------------------------------------------------------------


@dataclass
class GapRatioResult:
    """Output of `compute_gaps_and_ratios` for one shard (or any single CSR
    ray-crossing array set)."""

    gaps: np.ndarray  # (n_valid_gaps,) float64, inter-winding gap in scale-0 voxels
    gap_ray_index: np.ndarray  # (n_valid_gaps,) int, which ray each gap came from
    gap_anchor_winding: np.ndarray  # (n_valid_gaps,) int64, absolute winding of the LOWER-level crossing of the gap (seed_winding + level), used only for equivalent-alpha
    ratios: np.ndarray  # (n_valid_ratios,) float64, g[k+1] / g[k]
    ratio_ray_index: np.ndarray  # (n_valid_ratios,) int
    ratio_anchor_winding: np.ndarray  # (n_valid_ratios,) int64, absolute winding of the LOWEST-level crossing of the 3-crossing triple behind each ratio
    counts: dict = field(default_factory=dict)


def _sort_within_ray(t: np.ndarray, level: np.ndarray, ray_index: np.ndarray):
    """Sort crossings primarily by ray, secondarily by t, so that array
    adjacency always means physical adjacency along the ray -- regardless of
    whether the source file already stored crossings in that order (verified
    it does, for shard_0, but this does not rely on that holding elsewhere).
    lexsort's last key is primary, so (t, ray_index) sorts by ray_index
    first, then by t within each ray."""
    order = np.lexsort((t, ray_index))
    return t[order], level[order], ray_index[order]


def compute_gaps_and_ratios(
    crossing_t: np.ndarray,
    crossing_level: np.ndarray,
    crossing_offsets: np.ndarray,
    ray_step_zyx: np.ndarray,
    seed_winding: np.ndarray,
) -> GapRatioResult:
    """Vectorized computation of inter-winding gaps and adjacent-gap ratios
    across every ray in one shard's CSR-layout crossing arrays.

    Methodology (matches the task spec exactly):
      - A gap is the Euclidean scale-0-voxel distance between two
        consecutive-along-the-ray crossings whose `crossing_level` differs
        by exactly 1: `|t2 - t1| * ||step||`.
      - Only crossings on the SAME ray are ever compared (enforced via the
        ray-boundary mask below, derived from `crossing_offsets`).
      - A pair spanning a level skip (|level2 - level1| != 1, including
        duplicate levels or decreasing levels) is excluded from `gaps`
        entirely and counted in `counts["excluded_nonadjacent_level_pairs"]`.
      - A ratio g[k+1]/g[k] is only computed when BOTH g[k] and g[k+1] are
        themselves valid (non-excluded) gaps computed from three
        consecutive-along-the-ray crossings within a single ray. If either
        neighboring pair was excluded (level skip, degenerate step, or
        zero/negative gap), no ratio bridges across the gap -- this is
        enforced structurally below, not by a separate check, because a
        ratio can only be built from two ADJACENT positions in the
        per-pair validity mask.
      - Rays with < 2 crossings contribute no gaps; rays with < 3
        crossings contribute no ratios. Both are counted.
      - Rays whose `ray_step_zyx` norm is < STEP_NORM_EPS are treated as
        degenerate and excluded entirely (all their gaps and ratios).
    """
    n_rays = len(crossing_offsets) - 1
    counts = {
        "n_rays": n_rays,
        "n_crossings": len(crossing_t),
    }

    ray_index = np.repeat(np.arange(n_rays), np.diff(crossing_offsets))

    step_norm_per_ray = np.linalg.norm(ray_step_zyx.astype(np.float64), axis=1)
    degenerate_step_ray = step_norm_per_ray < STEP_NORM_EPS
    counts["n_rays_degenerate_step"] = int(degenerate_step_ray.sum())

    crossings_per_ray = np.diff(crossing_offsets)
    counts["n_rays_lt2_crossings"] = int(np.sum(crossings_per_ray < 2))
    counts["n_rays_lt3_crossings"] = int(np.sum(crossings_per_ray < 3))

    t_sorted, level_sorted, ray_sorted = _sort_within_ray(
        crossing_t.astype(np.float64), crossing_level.astype(np.int64), ray_index
    )

    # A "pair" is flat position p paired with p+1 in the sorted arrays.
    # It is a same-ray pair iff ray_sorted[p] == ray_sorted[p+1] (crossing
    # a ray boundary otherwise, in which case it must never be treated as a
    # gap at all -- not even an excluded one, since the two crossings are
    # not on the same ray to begin with).
    same_ray = ray_sorted[:-1] == ray_sorted[1:]
    t_diff = t_sorted[1:] - t_sorted[:-1]
    level_diff = level_sorted[1:] - level_sorted[:-1]

    pair_ray = ray_sorted[:-1]
    pair_step_norm = step_norm_per_ray[pair_ray]
    pair_ray_degenerate = degenerate_step_ray[pair_ray]

    adjacent_level = level_diff == 1
    positive_t = t_diff > GAP_EPS

    counts["n_pairs_total"] = int(same_ray.sum())
    counts["excluded_nonadjacent_level_pairs"] = int(np.sum(same_ray & ~adjacent_level))
    counts["excluded_degenerate_t_pairs"] = int(
        np.sum(same_ray & adjacent_level & ~positive_t)
    )
    counts["excluded_degenerate_step_pairs"] = int(
        np.sum(same_ray & adjacent_level & positive_t & pair_ray_degenerate)
    )

    valid_gap = same_ray & adjacent_level & positive_t & ~pair_ray_degenerate

    gap = t_diff * pair_step_norm  # only meaningful where valid_gap is True
    anchor_winding = seed_winding[pair_ray].astype(np.int64) + level_sorted[:-1]

    counts["n_gaps_valid"] = int(valid_gap.sum())

    gaps = gap[valid_gap]
    gap_ray_index = pair_ray[valid_gap]
    gap_anchor_winding = anchor_winding[valid_gap]

    # A ratio at flat pair-position p uses gap[p] and gap[p+1]. Both must be
    # individually valid; this automatically also guarantees positions
    # p, p+1, p+2 are all on the same ray (see docstring).
    ratio_valid = valid_gap[:-1] & valid_gap[1:]
    counts["n_ratio_slots_total"] = int(len(ratio_valid))
    counts["n_ratios_valid"] = int(ratio_valid.sum())

    g_k = gap[:-1][ratio_valid]
    g_k1 = gap[1:][ratio_valid]
    ratios = g_k1 / g_k
    ratio_ray_index = pair_ray[:-1][ratio_valid]
    ratio_anchor_winding = anchor_winding[:-1][ratio_valid]

    return GapRatioResult(
        gaps=gaps,
        gap_ray_index=gap_ray_index,
        gap_anchor_winding=gap_anchor_winding,
        ratios=ratios,
        ratio_ray_index=ratio_ray_index,
        ratio_anchor_winding=ratio_anchor_winding,
        counts=counts,
    )


# ---------------------------------------------------------------------------
# Equivalent alpha
# ---------------------------------------------------------------------------
#
# Derivation
# ----------
# `RadialPowerLawTransform` in probe_spiral_satisfaction_robustness.py models
# the scan<->spiral map as a purely radial power law anchored at a reference
# radius r0:
#
#     s = r0 * (r / r0) ** alpha            (forward, scan -> spiral)
#     r = r0 * (s / r0) ** (1 / alpha)       (inverse, spiral -> scan)
#
# and its sweep anchors r0 EXACTLY at the winding under test (r0 = winding *
# dr), so that the transform is the identity at that one winding and only
# the ONE-WINDING step away from it is examined. This script reuses the
# SAME anchoring convention -- treating the lower-level crossing of each
# observed triple as the local r0 -- so a value computed here is directly
# comparable to the pinned sweep's alpha values.
#
# This IS a modeling choice, not a claim about the real field's true form:
# real winding geometry need not be any power law at all. We fit the
# simplest one that matches the sweep's own parametrization, purely so the
# real field's nonlinearity can be placed on the same scale the sweep used.
#
# Let n0 be the absolute winding number of the triple's lowest-level
# crossing (n0 = seed_winding[ray] + level, VERIFIED exact -- see module
# docstring). Spiral-space windings are equally spaced by construction
# (that is the definition of "linear" in spiral space) with some constant
# spacing D per winding (D's actual value is never needed -- see below).
# Anchor r0 := n0 * D, matching the sweep's r0 = winding * dr convention
# exactly with n0 playing the role of "winding" and D playing the role of
# "dr". Local relative winding offset j (0, 1, 2, ...) then has scan-space
# radius:
#
#     r(j) = r0 * (1 + j * delta) ** (1 / alpha),   delta := D / r0 = 1 / n0
#
# (D cancels algebraically: delta = D / (n0 * D) = 1 / n0, so this needs
# only the ABSOLUTE WINDING NUMBER n0, never the spiral-space winding
# spacing D itself.)
#
# The two observed gaps around the triple are then, algebraically:
#
#     g0 = r(1) - r(0) = r0 * [ (1 + delta) ** (1/alpha) - 1 ]
#     g1 = r(2) - r(1) = r0 * [ (1 + 2*delta) ** (1/alpha) - (1 + delta) ** (1/alpha) ]
#
# and their ratio (r0 cancels):
#
#     R(alpha, n0) = g1 / g0
#                  = [ (1+2*delta)**(1/alpha) - (1+delta)**(1/alpha) ]
#                    / [ (1+delta)**(1/alpha) - 1 ],           delta = 1/n0
#
# R(1, n0) = 1 for every n0 (linear spiral space gives ratio exactly 1,
# matching the task spec's stated sanity property; algebraically: at
# alpha=1, (1+delta)**1 = 1+delta, so both numerator and denominator equal
# delta). Numerically (see tests + the ad hoc check performed while writing
# this script) R(alpha, n0) is STRICTLY MONOTONIC DECREASING in alpha over
# alpha in (0, infinity) for every n0 in the observed range (10 <= n0 <=
# ~150), so R uniquely determines alpha given n0 -- but the equation is
# transcendental (no closed-form inverse), so `equivalent_alpha` inverts it
# numerically via vectorized bisection in log(alpha)-space (monotonic in
# log(alpha) too, since alpha = exp(u) is monotonic increasing in u).
#
# R is bounded: as alpha -> infinity, R approaches a finite floor > R(inf)
# that depends only on n0 (never reaching it); as alpha -> 0+, R -> infinity.
# An observed ratio below that floor, or an anchor n0 <= 0 (meaning the
# triple's lowest crossing has non-positive absolute winding number, where
# the r0 = n0*D anchoring convention itself breaks down -- there is no
# "n0 windings from center" scale to anchor at), has NO solution within the
# bracket and is reported as unresolved rather than silently clipped into
# the distribution.


def _R_model(alpha: np.ndarray, n0: np.ndarray) -> np.ndarray:
    """Forward model R(alpha, n0), vectorized. See derivation above."""
    delta = 1.0 / n0
    a = 1.0 / alpha
    r1 = (1.0 + delta) ** a
    r2 = (1.0 + 2.0 * delta) ** a
    g0 = r1 - 1.0
    g1 = r2 - r1
    return g1 / g0


@dataclass
class EquivalentAlphaResult:
    alpha: np.ndarray  # (n_resolved,) float64
    ray_index: np.ndarray
    anchor_winding: np.ndarray = field(default_factory=lambda: np.array([]))
    counts: dict = field(default_factory=dict)


def equivalent_alpha(
    ratios: np.ndarray,
    anchor_winding: np.ndarray,
    ray_index: np.ndarray,
    lo: float = ALPHA_BRACKET_LO,
    hi: float = ALPHA_BRACKET_HI,
    iters: int = ALPHA_BISECTION_ITERS,
) -> EquivalentAlphaResult:
    """Invert `_R_model` for alpha given observed ratios and their triples'
    anchor winding numbers, via vectorized bisection in log(alpha)-space.
    Points with non-positive anchor winding, or whose ratio falls outside
    the achievable range for [lo, hi], are excluded and counted rather than
    clipped into the returned distribution."""
    ratios = np.asarray(ratios, dtype=np.float64)
    n0 = np.asarray(anchor_winding, dtype=np.float64)
    ray_index = np.asarray(ray_index)

    counts = {"n_input": len(ratios)}

    resolvable = n0 > 0
    counts["excluded_nonpositive_anchor_winding"] = int(np.sum(~resolvable))

    r_lo_bound = _R_model(
        np.full_like(n0, hi), np.where(n0 > 0, n0, 1.0)
    )  # R floor at alpha=hi
    r_hi_bound = _R_model(
        np.full_like(n0, lo), np.where(n0 > 0, n0, 1.0)
    )  # R ceiling at alpha=lo
    in_range = (ratios >= r_lo_bound) & (ratios <= r_hi_bound)
    resolvable = resolvable & in_range
    counts["excluded_ratio_out_of_bracket_range"] = int(np.sum((n0 > 0) & ~in_range))
    # Split for diagnosis: "below floor" means the observed ratio is smaller
    # than what even alpha=hi (maximal compression, in this convention) can
    # produce -- no finite alpha explains it. "above ceiling" is the
    # opposite (smaller than lo can reach). Reported separately because they
    # have different readings: a large below-floor count at large n0 means
    # the local ratio spread is comparable to or exceeds what this
    # one-winding-step, center-anchored power law can represent AT ALL for
    # that winding number, which is itself informative (see report footer).
    counts["excluded_below_floor"] = int(np.sum((n0 > 0) & (ratios < r_lo_bound)))
    counts["excluded_above_ceiling"] = int(np.sum((n0 > 0) & (ratios > r_hi_bound)))

    counts["n_resolved"] = int(resolvable.sum())

    r_sub = ratios[resolvable]
    n0_sub = n0[resolvable]
    ray_sub = ray_index[resolvable]

    u_lo = np.full(r_sub.shape, np.log(lo))
    u_hi = np.full(r_sub.shape, np.log(hi))
    for _ in range(iters):
        u_mid = 0.5 * (u_lo + u_hi)
        alpha_mid = np.exp(u_mid)
        r_mid = _R_model(alpha_mid, n0_sub)
        # R is decreasing in alpha (increasing in u is decreasing in R):
        # if r_mid > r_sub, the true alpha is larger (u is too low) -> raise u_lo.
        go_up = r_mid > r_sub
        u_lo = np.where(go_up, u_mid, u_lo)
        u_hi = np.where(go_up, u_hi, u_mid)

    alpha_resolved = np.exp(0.5 * (u_lo + u_hi))

    return EquivalentAlphaResult(
        alpha=alpha_resolved, ray_index=ray_sub, anchor_winding=n0_sub, counts=counts
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def quantiles(x: np.ndarray) -> dict:
    if len(x) == 0:
        return {f"q{int(q * 100):02d}": float("nan") for q in QUANTILE_LEVELS} | {
            "min": float("nan"),
            "max": float("nan"),
            "count": 0,
        }
    qs = np.quantile(x, QUANTILE_LEVELS)
    out = {
        f"q{int(q * 100):02d}": float(v)
        for q, v in zip(QUANTILE_LEVELS, qs, strict=False)
    }
    out["min"] = float(np.min(x))
    out["max"] = float(np.max(x))
    out["count"] = int(len(x))
    return out


def format_quantile_line(label: str, q: dict) -> str:
    return (
        f"{label:28s} n={q['count']:>10,}  min={q['min']:>12.4f}  "
        f"p05={q['q05']:>10.4f}  p25={q['q25']:>10.4f}  p50={q['q50']:>10.4f}  "
        f"p75={q['q75']:>10.4f}  p95={q['q95']:>10.4f}  max={q['max']:>12.4f}"
    )


def run_shard(shard: str) -> dict:
    arrays = load_shard(shard)
    result = compute_gaps_and_ratios(
        crossing_t=arrays["crossing_t"],
        crossing_level=arrays["crossing_level"],
        crossing_offsets=arrays["crossing_offsets"],
        ray_step_zyx=arrays["ray_step_zyx"],
        seed_winding=arrays["seed_winding"],
    )
    alpha_result = equivalent_alpha(
        result.ratios, result.ratio_anchor_winding, result.ratio_ray_index
    )
    return {
        "shard": shard,
        "gap_result": result,
        "alpha_result": alpha_result,
    }


def build_report(shard_results: list[dict]) -> str:
    lines = []
    lines.append("Real inter-winding nonlinearity of PHercParis4")
    lines.append(
        "Source: https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/"
        "winding_model/ (shard sha256 verified against each shard's manifest.json "
        "before use)"
    )
    lines.append(f"Shards: {', '.join(r['shard'] for r in shard_results)}")
    lines.append("")

    all_gaps = np.concatenate([r["gap_result"].gaps for r in shard_results])
    all_ratios = np.concatenate([r["gap_result"].ratios for r in shard_results])
    all_alphas = np.concatenate([r["alpha_result"].alpha for r in shard_results])

    lines.append("=== 1. Inter-winding gap distribution (scale-0 voxels), pooled ===")
    lines.append(format_quantile_line("gaps", quantiles(all_gaps)))
    lines.append("")
    lines.append("Per-shard gap median:")
    for r in shard_results:
        g = r["gap_result"].gaps
        med = float(np.median(g)) if len(g) else float("nan")
        lines.append(f"  {r['shard']:10s} n={len(g):>10,}  median={med:.4f}")
    lines.append("")

    lines.append("=== 2. Adjacent-gap ratio distribution, pooled ===")
    lines.append(format_quantile_line("ratios (g[k+1]/g[k])", quantiles(all_ratios)))
    lines.append("")
    lines.append("Per-shard ratio median:")
    for r in shard_results:
        rt = r["gap_result"].ratios
        med = float(np.median(rt)) if len(rt) else float("nan")
        lines.append(f"  {r['shard']:10s} n={len(rt):>10,}  median={med:.4f}")
    lines.append("")
    lines.append(
        "Tail explicitly: fraction of ratios outside [0.5, 2.0] (a 2x "
        f"asymmetry between consecutive gaps) = "
        f"{float(np.mean((all_ratios < 0.5) | (all_ratios > 2.0))):.6f}; "
        "outside [0.8, 1.25] = "
        f"{float(np.mean((all_ratios < 0.8) | (all_ratios > 1.25))):.6f}"
    )
    lines.append("")

    lines.append(
        "=== 3. Equivalent alpha (power-law model fit per triple; see script "
        "docstring for the algebraic derivation) ==="
    )
    lines.append(format_quantile_line("equivalent alpha", quantiles(all_alphas)))
    lines.append("")
    lines.append("Per-shard equivalent-alpha median:")
    for r in shard_results:
        a = r["alpha_result"].alpha
        med = float(np.median(a)) if len(a) else float("nan")
        lines.append(f"  {r['shard']:10s} n={len(a):>10,}  median={med:.4f}")
    lines.append("")
    lines.append(
        "Comparison to the pinned sweep grid [1.0, 0.95, 0.90, 0.80, 0.60] and "
        "the informally-probed breaking regime (~0.2):"
    )
    q = quantiles(all_alphas)
    for label, level in [
        ("p05", "q05"),
        ("p25", "q25"),
        ("p50 (median)", "q50"),
        ("p75", "q75"),
        ("p95", "q95"),
    ]:
        lines.append(f"  {label:16s} equivalent alpha = {q[level]:.4f}")
    lines.append("")

    all_n0 = np.concatenate([r["alpha_result"].anchor_winding for r in shard_results])
    lines.append(
        "Equivalent alpha stratified by absolute local winding number n0 "
        "(diagnostic: this convention (r0 = n0*D, one-winding step) makes R "
        "less sensitive to alpha as n0 grows -- see derivation docstring -- "
        "so the SAME real local ratio noise maps to increasingly extreme "
        "alpha at larger n0, independent of any change in the true field):"
    )
    n0_edges = [0, 20, 40, 60, 80, 100, 200]
    for lo_edge, hi_edge in zip(n0_edges[:-1], n0_edges[1:], strict=False):
        bucket_mask = (all_n0 >= lo_edge) & (all_n0 < hi_edge)
        bucket_alpha = all_alphas[bucket_mask]
        med = float(np.median(bucket_alpha)) if len(bucket_alpha) else float("nan")
        lines.append(
            f"  n0 in [{lo_edge:>3d},{hi_edge:>4d}) n={len(bucket_alpha):>10,}  "
            f"median alpha={med:.4f}"
        )
    lines.append("")

    lines.append("=== Exclusions (counted, not silently dropped) ===")
    total_counts: dict = {}
    for r in shard_results:
        for k, v in r["gap_result"].counts.items():
            total_counts[k] = total_counts.get(k, 0) + v
    for k, v in total_counts.items():
        lines.append(f"  {k:36s} {v:>12,}")
    lines.append("")
    alpha_counts: dict = {}
    for r in shard_results:
        for k, v in r["alpha_result"].counts.items():
            alpha_counts[k] = alpha_counts.get(k, 0) + v
    lines.append("  --- equivalent-alpha inversion ---")
    for k, v in alpha_counts.items():
        lines.append(f"  {k:36s} {v:>12,}")
    lines.append("")

    lines.append(
        "MODELING CAVEAT: equivalent alpha assumes the real scan<->spiral map "
        "is locally a power law anchored at the lower-level crossing of each "
        "observed triple, in the SAME convention "
        "probe_spiral_satisfaction_robustness.py's sweep used (r0 = winding * "
        "dr). This is a modeling choice made to put the real field's "
        "nonlinearity on the same scale the sweep used -- it is NOT a claim "
        "that the real winding geometry truly follows a power law."
    )
    lines.append("")
    lines.append(
        "PLAIN READING: the directly-observed adjacent-gap ratio is close to "
        "uniform in the middle (pooled median 0.9985, every per-shard median "
        "within 0.98-1.01) but has a real, substantial local spread (p05/p95 "
        "= 0.72/1.38; 21.6% of ratios fall outside [0.8, 1.25]) -- this "
        "spread is the directly measured, convention-free quantity and is "
        "the most trustworthy number in this report. The derived "
        "equivalent-alpha (median 0.117, IQR 0.063-0.258) sits BELOW the "
        "pinned sweep's most conservative tested point (0.60) and mostly "
        "below the informally-probed breaking regime (~0.2) -- but the n0 "
        "stratification above shows this number is strongly convention-"
        "dependent (it falls monotonically from 0.33 to 0.08 as n0 alone "
        "rises from <20 to 100-200, with no change in the underlying ratio "
        "noise), and 93% of the 11.4M unresolvable ratios are BELOW the "
        "model's floor (i.e. the observed gap shrinks by MORE than even "
        "maximal compression in this one-winding-step convention can "
        "produce), which points to local fiber waviness / winding-inference "
        "noise rather than a smooth global power-law drift. Read together: "
        "the real field's local irregularity is real and substantial, is at "
        "least as large as (and plausibly larger than) the informally-"
        "probed breaking case in a sizeable fraction of triples, but is "
        "probably not well described as a single smooth alpha at all -- so "
        "the pinned sweep's clean 'safe within alpha>=0.60' story should be "
        "read as characterizing SMOOTH systematic nonlinearity only, and "
        "should NOT be read as bounding the real field's local irregularity, "
        "which this measurement suggests is comparable to or beyond the "
        "sweep's breaking regime for a meaningful fraction of local winding "
        "triples."
    )
    return "\n".join(lines) + "\n"


def main():
    shard_results = []
    for shard in SHARD_NAMES:
        print(f"processing {shard} ...", file=sys.stderr)
        shard_results.append(run_shard(shard))

    report = build_report(shard_results)
    print(report)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)


if __name__ == "__main__":
    main()
