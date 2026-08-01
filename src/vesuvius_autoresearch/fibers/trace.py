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

    tangent_window: int = 1
    """Compare each step against the mean of the last `tangent_window` directions
    rather than against the single previous step.

    `step` is sub-voxel while `_direction_at` is nearest-neighbour, so the
    orientation field is piecewise-constant and jumps at voxel boundaries. With a
    window of 1, a single noisy voxel ends a walk permanently -- measured as 46%
    of all stops on a real cube. A window spanning two voxels (`ceil(2 / step)`,
    i.e. 3 at the default step) averages that out while leaving `max_angle_deg`
    untouched, so a sustained bend still terminates the walk.

    Measured on both dev cubes (`reports/fiber_tracer_improvement.md`, Fix A): window
    3 improves merge-penalized ERL over window 1, but window **5** measured better
    still on both cubes (ERLpen 25.61 and 35.84 -- the best smoothing-only numbers
    per cube; cube 1's is the best found anywhere in that study, while cube 2 reached
    35.87 with seed NMS enabled, which was not shipped because NMS measured null) and
    is the value the frozen, shipped-improvement configuration actually uses -- 3 is a
    reasonable prior, not the measured optimum.

    Defaults to 1, which is exactly the published baseline's behaviour; pass 5 to get
    the measured, frozen configuration.
    """

    max_skip_steps: int = 0
    """Consecutive curvature rejections to coast through before giving up.

    Smoothing the reference cannot reject a bad *sample*: at a wildly-wrong
    voxel the incoming direction is perpendicular, so the turn test fails
    however stable the reference is. Coasting steps along the reference instead
    of terminating, and resumes as soon as the field agrees again.

    2 at the default step of 0.7 voxels spans ~1.4 voxels -- enough to cross one
    corrupted voxel, not enough to cross a genuine fiber boundary and keep
    going. The counter resets on any accepted step, so this is a budget for
    *consecutive* rejections; a walk that keeps coasting is following something
    the field does not support and must still stop.

    This is the parameter most likely to buy merges, since coasting is exactly
    how a walk could cross into a neighbour.

    **Measured and rejected.** `reports/fiber_tracer_improvement.md` (Fix A) tested
    this in same-window isolation (window held fixed, skip 0 vs. skip 1 vs. skip 2)
    on both dev cubes -- four comparisons total. In all four, coasting regressed
    merge-penalized ERL and raised the merge count relative to smoothing alone at
    the same window. It does not add real connectivity; it suppresses a
    `high_curvature` stop long enough to occasionally paper over a bad segment, at
    the price of wrong-instance merges. It ships disabled (0) for that reason, not
    because it was untested.

    Defaults to 0, the published baseline's behaviour and the value the frozen,
    shipped-improvement configuration also uses.
    """

    max_steps: int = 4000
    min_length: float = 8.0
    """Discard walks shorter than this; they are noise, not fibers."""

    claim_radius: float = 1.5
    """A traced fiber claims voxels within this radius. Another walk entering a
    claimed voxel stops with COLLISION rather than merging into it."""

    seed_stride: int = 2
    """Subsample seed candidates for speed; the walk itself is sub-voxel anyway."""

    seed_nms_radius: float = 0.0
    """Suppress seed candidates lying within this distance of an accepted seed,
    measured **perpendicular to that seed's tangent**. 0 disables it.

    Several seeds landing across one fiber's cross-section each start a walk;
    the first claims the fiber and the rest stop immediately with COLLISION.
    Suppression is perpendicular-only on purpose: distance *along* the tangent
    is unconstrained, so a long fiber can still be re-seeded beyond a gap.

    A radius of 2 comes from fiber geometry rather than tuning -- papyrus fibers
    are roughly 10-20 um at 7.91 um/voxel.

    **Measured and rejected.** `reports/fiber_tracer_improvement.md` (Fix B) tested
    radius 2.0 alone and combined with the best smoothing setting, on both dev
    cubes. It produced no distinguishable merge-penalized-ERL change (collisions
    fell by only single-digit percentages, and combined with smoothing the ERLpen
    was indistinguishable from smoothing alone -- slightly worse on one dev cube),
    and alone on the other dev cube it was a double regression: merges rose while
    ERLpen worsened, the only row in that study where merges rose at all. Seed NMS
    can only remove redundant seed points; it has no mechanism to stop an
    already-running walk from drifting into a neighbouring fiber's territory,
    which is where most collisions originate. It ships disabled (0) because it was
    measured to do nothing useful, not because it was untested.
    """

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
    window = max(1, int(params.tangent_window))
    budget = max(0, int(params.max_skip_steps))
    recent: list[np.ndarray] = [seed_dir.copy()]
    skipped = 0
    reason = StopReason.MAX_LENGTH

    for _ in range(params.max_steps):
        # Reference tangent: sign-aligned mean of the recent directions. The
        # orientation field is defined only up to sign, so each entry is flipped
        # into the frame of the first before averaging -- otherwise two equally
        # valid opposing vectors cancel to near-zero.
        ref = np.zeros(3, dtype=float)
        for q in recent:
            ref += q if float(np.dot(q, recent[0])) >= 0.0 else -q
        n_ref = float(np.linalg.norm(ref))
        ref = prev if n_ref < 1e-8 else ref / n_ref

        d = _direction_at(dirs, valid, p, ref)
        if d is None:
            reason = StopReason.INVALID_DIRECTION
            break
        if float(np.dot(d, ref)) < cos_limit:
            # Coast: the sample disagrees, but a bounded run of disagreement is
            # a corrupted voxel rather than a real turn. Step along the
            # reference and try again; give up once the budget is spent.
            skipped += 1
            if skipped > budget:
                reason = StopReason.HIGH_CURVATURE
                break
            d = ref
        else:
            skipped = 0

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
        recent.append(d.copy())
        if len(recent) > window:
            recent.pop(0)
        p = nxt

    return pts, resp, reason


def _suppress_perpendicular(
    candidate: np.ndarray, accepted: np.ndarray, tangent: np.ndarray, radius: float
) -> bool:
    """Test-only oracle: true if `candidate` lies within `radius` of `accepted`,
    perpendicular to `tangent`. Not called from `trace_fibers` or anywhere else in
    production; its only consumer is `test_nms_suppresses_perpendicular_only`.

    A candidate far down the same fiber line has zero perpendicular offset
    (it sits *on* the tangent), so stripping the tangent component alone is
    not enough to exempt it -- that would suppress the whole line forever.
    The along-tangent component is instead bounded to a thin band
    (`|offset . t| <= 0.5`), matching the along-tangent bound of the
    stamped-disc volume path used in `trace_fibers`'s seed-NMS block.

    The two do **not** agree at the boundary: the production disc keeps offsets
    with squared perpendicular distance `<= r_nms**2` (inclusive), while this
    helper's radius check is strict (`< radius`). A candidate sitting exactly on
    the radius is suppressed by production but not by this function. This is a
    geometric spec/oracle for the perpendicular-vs-along-tangent shape of the
    suppression, not a literal reimplementation of the production boundary.
    """
    v = np.asarray(candidate, dtype=float) - np.asarray(accepted, dtype=float)
    t = np.asarray(tangent, dtype=float)
    n = float(np.linalg.norm(t))
    if n < 1e-8:
        return bool(np.linalg.norm(v) < radius)
    t = t / n
    along = float(np.dot(v, t))
    if abs(along) > 0.5:
        return False
    perp = v - along * t
    return bool(np.linalg.norm(perp) < radius)


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

    if params.seed_nms_radius > 0.0:
        r_nms = float(params.seed_nms_radius)
        rr = int(np.ceil(r_nms))
        suppressed = np.zeros(shape, dtype=bool)
        offsets = np.array(
            [
                (dz, dy, dx)
                for dz in range(-rr, rr + 1)
                for dy in range(-rr, rr + 1)
                for dx in range(-rr, rr + 1)
                if dz * dz + dy * dy + dx * dx <= r_nms * r_nms
            ],
            dtype=float,
        )
        kept = []
        for c in cand:
            cs = tuple(int(v) for v in c)
            if suppressed[cs]:
                continue
            kept.append(c)
            t = _direction_at(directions, valid, np.array(cs, dtype=float), None)
            if t is None:
                continue
            # stamp a disc perpendicular to the tangent: keep offsets whose
            # component along t is small, so the mark does not extend down the fiber
            along = offsets @ t
            disc = offsets[np.abs(along) <= 0.5]
            pts = np.rint(np.array(cs, dtype=float) + disc).astype(int)
            ok = np.ones(len(pts), dtype=bool)
            for a in range(3):
                ok &= (pts[:, a] >= 0) & (pts[:, a] < shape[a])
            pts = pts[ok]
            if len(pts):
                suppressed[pts[:, 0], pts[:, 1], pts[:, 2]] = True
        cand = np.array(kept) if kept else np.zeros((0, 3), dtype=int)
        if len(cand) == 0:
            return TraceResult(fibers=[], shape=shape, stop_counts={}, n_seeds_tried=0)

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


# --- fragment re-linking -----------------------------------------------------
#
# The connectivity evaluation showed fragmentation, not detection, is what limits
# this tracer: coverage of ground-truth length reached 0.69-0.88, but each true
# fiber was recovered as 10-26 separate instances, so expected run length stayed
# far below a connected-components baseline
# (`reports/fiber_connectivity_eval.md`).
#
# Re-linking joins fragments that are plausibly the same fiber. The asymmetry
# that governs every threshold here: a wrong link is a MERGE, and a merge
# corrupts the U/V parameterization fibers are wanted for, whereas the split it
# would have fixed merely fails to help. So the acceptance test is deliberately
# strict, and `max_link_angle_deg` defaults tighter than the tracer's own
# per-step turn limit.


@dataclass
class RelinkParams:
    max_gap: float = 6.0
    """Longest gap to bridge, in voxels. Beyond this the evidence that two
    fragments are one fiber is too weak to act on."""

    max_link_angle_deg: float = 20.0
    """Each fragment's outgoing tangent must point at the other fragment, and
    vice versa, within this angle. Tighter than the tracer's per-step limit
    because a link is a single irreversible commitment rather than one step among
    many."""

    max_tangent_angle_deg: float = 25.0
    """The two tangents must additionally be near-antiparallel, which rules out
    joining fragments that run side by side rather than end to end."""

    endpoint_window: int = 4
    """Points averaged at each end to estimate the outgoing tangent. One point is
    too noisy; too many blurs genuine curvature."""

    gap_weight: float = 1.0
    angle_weight: float = 0.15
    """Cost is `gap_weight * gap + angle_weight * total_angle_deg`; used only to
    order candidates, since matching is greedy best-first."""

    gap_fill_step: float = 0.7
    """Spacing of interpolated points inserted across a bridged gap, matching the
    tracer's own step. Without filling, a link changes the instance count but no
    connectivity metric, because the gap stays background in the rasterization."""


def _endpoint_tangents(
    points: np.ndarray, window: int
) -> tuple[np.ndarray, np.ndarray]:
    """Outward-pointing unit tangents at the start and end of a polyline."""
    n = len(points)
    w = max(1, min(window, n - 1))
    start_dir = points[0] - points[w]
    end_dir = points[-1] - points[-1 - w]
    out = []
    for d in (start_dir, end_dir):
        nrm = float(np.linalg.norm(d))
        out.append(d / nrm if nrm > 1e-9 else np.zeros(3))
    return out[0], out[1]


def _angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na < 1e-9 or nb < 1e-9:
        return 180.0
    c = float(np.dot(a, b) / (na * nb))
    return float(np.degrees(np.arccos(max(-1.0, min(1.0, c)))))


def relink_fragments(
    result: TraceResult, params: RelinkParams | None = None
) -> TraceResult:
    """Join collinear fragment endpoints into longer fibers.

    Greedy best-first over candidate links. Each endpoint may be used at most
    once, and links that would close a cycle are rejected, so the output is a set
    of chains. Fragments are concatenated in order, giving a single instance per
    chain.

    Returns a new `TraceResult`; the input is not modified, so a caller can score
    both and report the difference rather than only the improved number.
    """
    params = params or RelinkParams()
    frags = result.fibers
    n = len(frags)
    if n < 2:
        return TraceResult(
            fibers=list(frags),
            shape=result.shape,
            stop_counts=dict(result.stop_counts),
            n_seeds_tried=result.n_seeds_tried,
        )

    # endpoint index: 2*i = start of fragment i, 2*i + 1 = end
    pos = np.zeros((2 * n, 3), dtype=float)
    tan = np.zeros((2 * n, 3), dtype=float)
    for i, f in enumerate(frags):
        t0, t1 = _endpoint_tangents(f.points, params.endpoint_window)
        pos[2 * i], tan[2 * i] = f.points[0], t0
        pos[2 * i + 1], tan[2 * i + 1] = f.points[-1], t1

    cands = []
    for a in range(2 * n):
        fa = a // 2
        for b in range(a + 1, 2 * n):
            if b // 2 == fa:
                continue
            d = pos[b] - pos[a]
            gap = float(np.linalg.norm(d))
            if gap > params.max_gap or gap <= 0:
                continue
            ang_a = _angle_deg(tan[a], d)
            ang_b = _angle_deg(tan[b], -d)
            if ang_a > params.max_link_angle_deg or ang_b > params.max_link_angle_deg:
                continue
            # Near-antiparallel tangents: end-to-end, not side-by-side.
            if _angle_deg(tan[a], -tan[b]) > params.max_tangent_angle_deg:
                continue
            cost = params.gap_weight * gap + params.angle_weight * (ang_a + ang_b)
            cands.append((cost, a, b))

    cands.sort()
    used = np.zeros(2 * n, dtype=bool)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    links: dict[int, int] = {}
    for _cost, a, b in cands:
        if used[a] or used[b]:
            continue
        ra, rb = find(a // 2), find(b // 2)
        if ra == rb:  # would close a cycle
            continue
        used[a] = used[b] = True
        parent[ra] = rb
        links[a] = b
        links[b] = a

    # Walk each chain from an unlinked endpoint, concatenating fragments.
    visited = np.zeros(n, dtype=bool)
    out: list[TracedFiber] = []
    order = [i for i in range(n) if not (used[2 * i] and used[2 * i + 1])] + list(
        range(n)
    )
    for seed in order:
        if visited[seed]:
            continue
        # start from whichever end of `seed` is free, if any
        start_ep = 2 * seed if not used[2 * seed] else 2 * seed + 1
        chain_pts: list[np.ndarray] = []
        resp_mean: list[float] = []
        resp_min: list[float] = []
        ep = start_ep
        while True:
            fi = ep // 2
            if visited[fi]:
                break
            visited[fi] = True
            pts = frags[fi].points
            # traverse from the entry endpoint toward the far end
            if ep % 2 == 1:
                pts = pts[::-1]
            chain_pts.append(pts)
            resp_mean.append(frags[fi].mean_response)
            resp_min.append(frags[fi].min_response)
            far = 2 * fi + (0 if ep % 2 == 1 else 1)
            nxt = links.get(far)
            if nxt is None:
                break
            ep = nxt
        if not chain_pts:
            continue
        # Fill each bridged gap with interpolated points. Concatenating the
        # fragment polylines alone leaves the gap unlabelled, so a downstream
        # rasterization still shows background between them and the ground-truth
        # run stays broken: the link would reduce the instance count while
        # changing no connectivity metric at all. Asserting the link means
        # asserting the fiber continues through the gap, so the geometry has to
        # say so too.
        bridged: list[np.ndarray] = [chain_pts[0]]
        for prev_seg, next_seg in zip(chain_pts, chain_pts[1:], strict=False):
            a, b = prev_seg[-1], next_seg[0]
            gap = float(np.linalg.norm(b - a))
            n_fill = int(np.floor(gap / max(params.gap_fill_step, 1e-6)))
            if n_fill > 0:
                ts = np.linspace(0.0, 1.0, n_fill + 2)[1:-1]
                bridged.append(a[None, :] + (b - a)[None, :] * ts[:, None])
            bridged.append(next_seg)
        merged = np.concatenate(bridged, axis=0)
        first, last = frags[start_ep // 2], frags[ep // 2]
        out.append(
            TracedFiber(
                points=merged,
                mean_response=float(np.mean(resp_mean)),
                min_response=float(np.min(resp_min)),
                stop_start=first.stop_start,
                stop_end=last.stop_end,
            )
        )

    return TraceResult(
        fibers=out,
        shape=result.shape,
        stop_counts=dict(result.stop_counts),
        n_seeds_tried=result.n_seeds_tried,
    )
