"""Conservative fiber tracer: semantic fiber response -> separated instances.

The gap this fills, in villa's own words, is *"obtaining ... a way to identify and
separate long fibers with the right connectivity"*. The project already has
semantic fiber segmentation (`scrollprize/fiber_hz_vt` and friends) and a
manually-driven tracer inside VC3D; what is missing is an automatic step from a
fiber probability field to per-fiber instances.

The design objective is taken literally from the 🙋 ask in the 2026 open-problems
post:

    "The goal should be reliable connections. A tracer that confidently follows
    fewer fibers correctly is more useful than one that follows more fibers with
    a higher error rate."

So **abstention is a feature, not a shortfall**. Every walk records why it
stopped, and the thresholds that govern stopping are the knobs that trade
coverage for correctness. A merge (two real fibers fused into one instance) is
treated as strictly worse than a split, because a merge corrupts the U/V
parameterization that fibers are wanted for in the first place, whereas a split
merely fails to help.

Reads the orientation field from `fiber_direction()`, which returns an explicit
validity mask; this module never steps through an invalid voxel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from vesuvius_autoresearch.fibers.detection import (
    detect_vesselness,
    fiber_direction,
    hessian,
)


class StopReason(str, Enum):
    """Why a walk terminated. Reported per fiber end, never silently dropped."""

    OUT_OF_BOUNDS = "out_of_bounds"
    LOW_RESPONSE = "low_response"
    INVALID_DIRECTION = "invalid_direction"
    HIGH_CURVATURE = "high_curvature"
    COLLISION = "collision"
    MAX_LENGTH = "max_length"


@dataclass
class TraceParams:
    seed_threshold: float = 0.5
    """Minimum response to start a walk. Raising this trades coverage for purity."""

    continue_threshold: float = 0.25
    """Minimum response to keep walking. Below `seed_threshold` by design: it is
    reasonable to follow a fiber into a slightly dimmer region, but not to start
    one there."""

    max_angle_deg: float = 30.0
    """Maximum turn per step. Papyrus fibers are near-straight over short spans,
    so a large turn usually means the orientation field has jumped to a
    neighbouring fiber or sheet."""

    step: float = 0.7
    """Step length in voxels. Sub-voxel so the walk cannot skip past a thin fiber."""

    max_steps: int = 4000
    min_length: float = 8.0
    """Discard walks shorter than this; they are noise, not fibers."""

    claim_radius: float = 1.5
    """A traced fiber claims voxels within this radius. Another walk entering a
    claimed voxel stops with COLLISION rather than merging into it."""

    seed_stride: int = 2
    """Subsample seed candidates for speed; the walk itself is sub-voxel anyway."""

    seed_percentile: float | None = None
    """If set, seed where `seed_response` exceeds this percentile **of the voxels
    that already pass the continuation gate**, instead of using the absolute
    `seed_threshold`.

    This exists because of a measured property of real data, not as a
    convenience. On a 7.91 um scroll cube, globally max-normalized Hessian
    vesselness separates hand-traced fibers from background by a mean ratio of
    only ~2.2 (0.011 inside the label vs 0.005 outside), and the 90th percentile
    inside the label is ~0.03. Any fixed global threshold therefore either admits
    most of the background or almost none of the fibers, and an absolute
    `seed_threshold` of 0.3 finds essentially nothing.

    Vesselness is still a good *ranking* of centre-line-ness locally; it is a poor
    global detector. So when a semantic gate is available, the useful question is
    "which voxels inside the gate look most like a ridge centre", which is a
    percentile within the gate."""


@dataclass
class TracedFiber:
    points: np.ndarray  # (N, 3) float, (z, y, x), ordered along the fiber
    mean_response: float
    min_response: float
    stop_start: StopReason
    stop_end: StopReason

    @property
    def length(self) -> float:
        if len(self.points) < 2:
            return 0.0
        return float(np.linalg.norm(np.diff(self.points, axis=0), axis=1).sum())

    @property
    def confidence(self) -> float:
        """Per-fiber confidence in [0, 1].

        Deliberately simple and reported rather than tuned: the geometric mean of
        the mean and minimum response along the walk. Using the minimum as well
        as the mean penalizes a fiber that is strong nearly everywhere but passes
        through one ambiguous voxel, which is exactly where a merge happens.
        """
        return float(
            np.sqrt(max(self.mean_response, 0.0) * max(self.min_response, 0.0))
        )


@dataclass
class TraceResult:
    fibers: list[TracedFiber] = field(default_factory=list)
    shape: tuple[int, int, int] = (0, 0, 0)
    stop_counts: dict[str, int] = field(default_factory=dict)
    n_seeds_tried: int = 0

    def __len__(self) -> int:
        return len(self.fibers)

    @property
    def total_length(self) -> float:
        return float(sum(f.length for f in self.fibers))

    def filter_confidence(self, min_confidence: float) -> TraceResult:
        """The abstention knob: drop fibers below a confidence, keep the rest.

        Sweeping this is how the coverage/correctness curve is produced, so it
        must not mutate in place.
        """
        keep = [f for f in self.fibers if f.confidence >= min_confidence]
        return TraceResult(
            fibers=keep,
            shape=self.shape,
            stop_counts=dict(self.stop_counts),
            n_seeds_tried=self.n_seeds_tried,
        )

    def to_instances(self, radius: float = 1.0) -> np.ndarray:
        """Instance-label volume: 0 background, else fiber index + 1."""
        out = np.zeros(self.shape, dtype=np.int32)
        r = int(np.ceil(radius))
        offs = [
            (dz, dy, dx)
            for dz in range(-r, r + 1)
            for dy in range(-r, r + 1)
            for dx in range(-r, r + 1)
            if dz * dz + dy * dy + dx * dx <= radius * radius
        ]
        for i, f in enumerate(self.fibers, start=1):
            idx = np.rint(f.points).astype(int)
            for dz, dy, dx in offs:
                p = idx + np.array([dz, dy, dx])
                ok = np.ones(len(p), dtype=bool)
                for a in range(3):
                    ok &= (p[:, a] >= 0) & (p[:, a] < self.shape[a])
                p = p[ok]
                if len(p):
                    sl = (p[:, 0], p[:, 1], p[:, 2])
                    empty = out[sl] == 0
                    out[sl] = np.where(empty, i, out[sl])
        return out


def _trilinear(vol: np.ndarray, p: np.ndarray) -> float:
    """Trilinear sample of a scalar volume at a float (z, y, x) point.

    Coordinates are snapped into range by a small epsilon first. Without it a
    value like -5.7e-17, which arises routinely from a direction component that
    is mathematically zero, floors to -1 and the sample is reported as out of
    bounds. That failure killed every walk starting on a face of the volume.
    """
    eps = 1e-9
    p = np.asarray(p, dtype=float)
    p = np.where(np.abs(p) < eps, 0.0, p)
    z, y, x = p
    z0, y0, x0 = int(np.floor(z)), int(np.floor(y)), int(np.floor(x))
    # Sampling exactly on the far face is legitimate; step back one voxel so the
    # 2x2x2 neighbourhood stays inside the array.
    if z0 == vol.shape[0] - 1 and abs(z - z0) < eps:
        z0 -= 1
    if y0 == vol.shape[1] - 1 and abs(y - y0) < eps:
        y0 -= 1
    if x0 == vol.shape[2] - 1 and abs(x - x0) < eps:
        x0 -= 1
    if not (
        0 <= z0 < vol.shape[0] - 1
        and 0 <= y0 < vol.shape[1] - 1
        and 0 <= x0 < vol.shape[2] - 1
    ):
        return float("nan")
    dz, dy, dx = z - z0, y - y0, x - x0
    c = vol[z0 : z0 + 2, y0 : y0 + 2, x0 : x0 + 2]
    wz = np.array([1 - dz, dz])
    wy = np.array([1 - dy, dy])
    wx = np.array([1 - dx, dx])
    return float(np.einsum("i,j,k,ijk->", wz, wy, wx, c))


def _direction_at(
    dirs: np.ndarray, valid: np.ndarray, p: np.ndarray, prev: np.ndarray | None
) -> np.ndarray | None:
    """Nearest-neighbour orientation at p, sign-aligned to `prev`.

    Nearest neighbour rather than interpolation: an orientation field is only
    defined up to sign, so naively averaging neighbours can cancel two opposing
    but equally valid vectors to near-zero. Aligning signs before averaging is
    possible but adds a failure mode for no real gain at sub-voxel steps.
    """
    idx = tuple(int(round(v)) for v in p)
    for a in range(3):
        if not (0 <= idx[a] < dirs.shape[a]):
            return None
    if not valid[idx]:
        return None
    d = dirs[idx].astype(float)
    n = np.linalg.norm(d)
    if n < 1e-8:
        return None
    d = d / n
    if prev is not None and float(np.dot(d, prev)) < 0.0:
        d = -d
    return d


def _walk(
    start: np.ndarray,
    seed_dir: np.ndarray,
    response: np.ndarray,
    dirs: np.ndarray,
    valid: np.ndarray,
    claimed: np.ndarray,
    params: TraceParams,
    claim_id: int,
) -> tuple[list[np.ndarray], list[float], StopReason]:
    """Walk one direction from a seed until a stopping condition fires."""
    cos_limit = float(np.cos(np.deg2rad(params.max_angle_deg)))
    pts: list[np.ndarray] = []
    resp: list[float] = []
    p = start.astype(float).copy()
    prev = seed_dir.copy()
    reason = StopReason.MAX_LENGTH

    for _ in range(params.max_steps):
        d = _direction_at(dirs, valid, p, prev)
        if d is None:
            reason = StopReason.INVALID_DIRECTION
            break
        if float(np.dot(d, prev)) < cos_limit:
            reason = StopReason.HIGH_CURVATURE
            break

        nxt = p + d * params.step
        idx = tuple(int(round(v)) for v in nxt)
        if not all(0 <= idx[a] < response.shape[a] for a in range(3)):
            reason = StopReason.OUT_OF_BOUNDS
            break

        other = claimed[idx]
        if other != 0 and other != claim_id:
            reason = StopReason.COLLISION
            break

        r = _trilinear(response, nxt)
        if not np.isfinite(r):
            reason = StopReason.OUT_OF_BOUNDS
            break
        if r < params.continue_threshold:
            reason = StopReason.LOW_RESPONSE
            break

        pts.append(nxt.copy())
        resp.append(r)
        prev = d
        p = nxt

    return pts, resp, reason


def _claim(claimed: np.ndarray, points: np.ndarray, radius: float, fid: int) -> None:
    r = int(np.ceil(radius))
    idx = np.rint(points).astype(int)
    for dz in range(-r, r + 1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dz * dz + dy * dy + dx * dx > radius * radius:
                    continue
                p = idx + np.array([dz, dy, dx])
                ok = np.ones(len(p), dtype=bool)
                for a in range(3):
                    ok &= (p[:, a] >= 0) & (p[:, a] < claimed.shape[a])
                p = p[ok]
                if len(p):
                    sl = (p[:, 0], p[:, 1], p[:, 2])
                    claimed[sl] = np.where(claimed[sl] == 0, fid, claimed[sl])


def trace_fibers(
    volume: np.ndarray | None = None,
    *,
    response: np.ndarray | None = None,
    seed_response: np.ndarray | None = None,
    directions: np.ndarray | None = None,
    valid: np.ndarray | None = None,
    params: TraceParams | None = None,
    gauss_sigma: int = 1,
    sigma: int = 2,
) -> TraceResult:
    """Trace fiber instances from a CT volume or a precomputed response.

    Args:
        volume: raw CT cube. Used to compute vesselness and orientation if the
            corresponding arguments are not supplied.
        response: fiber probability in [0, 1], the **continuation gate** -- where
            fibers are. Pass a semantic model's output (e.g. `fiber_hz_vt`) here.
        seed_response: the **centre-line field** used to choose and rank seeds.
            Defaults to `response`, which is only correct when `response` is
            ridge-peaked (e.g. Hessian vesselness).

            This distinction is load-bearing. A saturated or binary semantic mask
            is flat inside a fiber, so it carries no information about where the
            centre line is; seeding on it scatters seeds across the whole
            cross-section and yields several parallel instances per fiber. On
            three synthetic tubes, a binary mask gave **15 instances instead of
            3**. Centre-line geometry has to come from the Hessian. When
            `volume` is supplied alongside a `response`, vesselness is computed
            from the volume and used for seeding automatically.
        directions, valid: orientation field from `fiber_direction()`, in
            (z, y, x) order. Computed from `volume` when omitted.
        params: thresholds; see `TraceParams`.

    Returns a `TraceResult` whose `stop_counts` summarises why walks ended. A
    healthy run is dominated by LOW_RESPONSE and OUT_OF_BOUNDS (the fiber genuinely
    ended); a run dominated by HIGH_CURVATURE or COLLISION means the orientation
    field or the thresholds need attention, and that should be reported rather
    than tuned away silently.
    """
    params = params or TraceParams()

    vol = None
    if volume is not None:
        vol = np.asarray(volume, dtype=float)

    def _vesselness() -> np.ndarray:
        if vol is None:
            raise ValueError("need `volume` to compute vesselness")
        v = np.asarray(
            detect_vesselness(vol.copy(), gauss_sigma=gauss_sigma, sigma=sigma),
            dtype=float,
        )
        mx = float(v.max())
        return v / mx if mx > 0 else v

    if response is None:
        response = _vesselness()
    if directions is None or valid is None:
        if vol is None:
            raise ValueError("provide `volume`, or all of response/directions/valid")
        J, _ = hessian(vol.copy(), gauss_sigma=gauss_sigma, sigma=sigma)
        directions, valid = fiber_direction(J)
    directions = np.asarray(directions)
    valid = np.asarray(valid)

    response = np.asarray(response, dtype=float)
    if seed_response is None:
        # Prefer a ridge-peaked field for seeding whenever we can build one.
        seed_response = _vesselness() if vol is not None else response
    seed_response = np.asarray(seed_response, dtype=float)

    shape = response.shape
    claimed = np.zeros(shape, dtype=np.int32)

    gate = (response >= params.continue_threshold) & valid
    if params.seed_percentile is not None:
        if not gate.any():
            return TraceResult(fibers=[], shape=shape, stop_counts={}, n_seeds_tried=0)
        cut = float(np.percentile(seed_response[gate], params.seed_percentile))
        cand = np.argwhere(gate & (seed_response >= cut))
    else:
        cand = np.argwhere(gate & (seed_response >= params.seed_threshold))
    if len(cand) == 0:
        return TraceResult(fibers=[], shape=shape, stop_counts={}, n_seeds_tried=0)

    order = np.argsort(-seed_response[cand[:, 0], cand[:, 1], cand[:, 2]])
    cand = cand[order][:: max(1, params.seed_stride)]

    result = TraceResult(shape=shape)
    counts: dict[str, int] = {}
    fid = 0

    for seed in cand:
        s = tuple(int(v) for v in seed)
        if claimed[s] != 0:
            continue
        result.n_seeds_tried += 1

        d0 = _direction_at(directions, valid, np.array(s, dtype=float), None)
        if d0 is None:
            continue

        fid += 1
        fwd_pts, fwd_r, fwd_stop = _walk(
            np.array(s, float), d0, response, directions, valid, claimed, params, fid
        )
        bwd_pts, bwd_r, bwd_stop = _walk(
            np.array(s, float), -d0, response, directions, valid, claimed, params, fid
        )

        pts = list(reversed(bwd_pts)) + [np.array(s, float)] + fwd_pts
        rs = list(reversed(bwd_r)) + [float(response[s])] + fwd_r
        if len(pts) < 2:
            fid -= 1
            continue

        arr = np.array(pts)
        length = float(np.linalg.norm(np.diff(arr, axis=0), axis=1).sum())
        if length < params.min_length:
            fid -= 1
            continue

        _claim(claimed, arr, params.claim_radius, fid)
        result.fibers.append(
            TracedFiber(
                points=arr,
                mean_response=float(np.mean(rs)),
                min_response=float(np.min(rs)),
                stop_start=bwd_stop,
                stop_end=fwd_stop,
            )
        )
        for r_ in (bwd_stop, fwd_stop):
            counts[r_.value] = counts.get(r_.value, 0) + 1

    result.stop_counts = counts
    return result
