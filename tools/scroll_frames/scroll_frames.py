"""Which coordinate frame are these mesh coordinates in?

83% of the segments with meshes in the Vesuvius Challenge open data ship more than one
`.tifxyz` mesh, one per CT scan of the same physical object. Every one of them declares
the same thing:

    "scale": [0.05, 0.05]

That is correct in each file. It means "one grid cell is 20 voxels OF MY OWN SCAN". It is
also indistinguishable between files whose voxel sizes differ by up to 40x, so coordinates
from two meshes of the same segment look interchangeable and are not. The only thing that
disambiguates them is the scan id inside the directory name.

Existing auditors do not catch this, and should not: `scroll-data-audit` checks artifacts
against the catalog and `tifxyz-repair` checks them against VC3D's loader semantics. Every
one of these files passes both. The problem is not validity, it is that two valid artifacts
describing one object are silently in different frames.

    scrollframes list PHercParis4/20230702185753

        mesh                                       um/voxel  grid           rel. scale
        -on-20260608103018-1.129um                    1.129  -                   1.00x  <- finest
        -on-20260411134726-2.4um                      2.400  -                   2.13x
        -on-20230205180739-7.91um                     7.910  -                   7.01x
        -on-20260310170716-45.532um                  45.532  -                  40.33x

What this does NOT give you
---------------------------
A transform. The relative scale above is the ratio of stated voxel sizes, nothing more. Two
scans of the same object do not share an origin or an orientation, and the surfaces
themselves may genuinely differ: on one segment we measured a fitted similarity between two
meshes leaving a median residual of 81 voxels, because the 2023 and 2026 segmentations are
not the same surface. Scaling coordinates by the ratio and calling them converted is how a
frame mismatch becomes a permanent fudge factor.

Use this to find out that you are in the wrong frame. Work out the transform separately, and
verify it, ideally against something that peaks at zero shift.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass

__all__ = ["Frame", "parse_mesh_name", "frames_for", "collision"]
__version__ = "0.1.0"

# <segment>-on-<scanid>-<voxelsize>um.tifxyz
_NAME = re.compile(
    r"^(?P<seg>.+?)-on-(?P<scan>\d+)-(?P<um>\d+(?:\.\d+)?|\.\d+)um\.tifxyz/?$"
)


@dataclass(frozen=True)
class Frame:
    """One mesh of a segment, and the scan whose voxel grid its coordinates live in."""

    mesh: str
    scan: str
    um_per_voxel: float
    declared_scale: float | None = None
    grid: tuple[int, int] | None = None
    bbox_diagonal: float | None = None

    @property
    def label(self) -> str:
        return f"-on-{self.scan}-{self.um_per_voxel:g}um"


def parse_mesh_name(name: str) -> Frame | None:
    """Frame from a `.tifxyz` directory name, or None if it does not follow the convention.

    The voxel size is only available here, in the filename. It is not in meta.json, which is
    the whole reason two frames are indistinguishable from their metadata.
    """
    m = _NAME.match(os.path.basename(name.rstrip("/")))
    if not m or float(m["um"]) <= 0:
        return None
    return Frame(
        mesh=os.path.basename(name.rstrip("/")),
        scan=m["scan"],
        um_per_voxel=float(m["um"]),
    )


def _scale(meta: dict) -> float | None:
    """The first declared scale, or None when it is absent or malformed."""
    sc = meta.get("scale")
    if not isinstance(sc, (list, tuple)) or not sc:
        return None
    try:
        value = float(sc[0])
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _grid(meta: dict) -> tuple[int, int] | None:
    """The grid shape, or None when it is absent or not two whole numbers."""
    g = meta.get("grid")
    if not isinstance(g, (list, tuple)) or len(g) != 2:
        return None
    try:
        if all(float(v) == int(v) for v in g):
            return (int(g[0]), int(g[1]))
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def _diag(bbox) -> float | None:
    try:
        return sum((bbox[1][i] - bbox[0][i]) ** 2 for i in range(3)) ** 0.5
    except Exception:
        return None


def frames_for(mesh_names, metas=None) -> list[Frame]:
    """Frames for one segment, finest voxel size first.

    `metas` optionally maps mesh name -> parsed meta.json, to enrich with declared scale,
    grid shape and bbox. Absent, the filename alone is enough to expose a collision. A field
    that is malformed is left out, as if absent, rather than raising.
    """
    out = []
    for name in mesh_names:
        f = parse_mesh_name(name)
        if f is None:
            continue
        meta = (metas or {}).get(f.mesh) or (metas or {}).get(name)
        if isinstance(meta, dict):
            f = Frame(
                f.mesh,
                f.scan,
                f.um_per_voxel,
                declared_scale=_scale(meta),
                grid=_grid(meta),
                bbox_diagonal=_diag(meta.get("bbox")),
            )
        out.append(f)
    return sorted(out, key=lambda f: f.um_per_voxel)


def collision(frames: list[Frame]) -> dict:
    """Do these frames look interchangeable while differing materially?

    `indistinguishable` is the condition that matters: every mesh declares the same scale,
    so nothing in the metadata warns a reader that the coordinates are not comparable.
    """
    if len(frames) < 2:
        return {
            "collides": False,
            "reason": "single frame" if frames else "no frames",
            "n_frames": len(frames),
            "n_declaring_scale": sum(f.declared_scale is not None for f in frames),
        }
    scales = sorted(f.declared_scale for f in frames if f.declared_scale is not None)
    ums = sorted(f.um_per_voxel for f in frames)
    spread = ums[-1] / ums[0]
    # Compare with a tolerance, not exactly. The catalog stores this field at both float32
    # and float64 precision, so the same value appears as 0.05 and 0.05000000074505806.
    # An exact comparison calls those "distinguishable metadata" and misses every real
    # collision, which is what the first version of this did.
    indistinguishable = not scales or (scales[-1] - scales[0]) <= 1e-6 * max(
        scales[-1], 1
    )
    return {
        "collides": bool(indistinguishable and spread > 1.001),
        "indistinguishable_metadata": indistinguishable,
        "declared_scales": scales,
        "n_declaring_scale": len(scales),
        "voxel_size_spread": spread,
        "finest_um": ums[0],
        "coarsest_um": ums[-1],
        "n_frames": len(frames),
    }


def render(segment: str, frames: list[Frame]) -> str:
    if not frames:
        return f"{segment}: no meshes following the -on-<scan>-<um>um.tifxyz convention"
    finest = frames[0].um_per_voxel
    lines = [
        f"{segment}",
        "",
        f"    {'mesh':<42}{'um/voxel':>9}  {'grid':<14}{'rel. scale':>11}",
    ]
    for f in frames:
        grid = f"{f.grid[0]}x{f.grid[1]}" if f.grid else "-"
        mark = "  <- finest" if f.um_per_voxel == finest else ""
        lines.append(
            f"    {f.label:<42}{f.um_per_voxel:>9.3f}  {grid:<14}"
            f"{f.um_per_voxel / finest:>10.2f}x{mark}"
        )
    c = collision(frames)
    lines.append("")
    n, declaring = c["n_frames"], c["n_declaring_scale"]
    if c["collides"]:
        spread = f"{c['voxel_size_spread']:.1f}x"
        scale = c["declared_scales"][0] if declaring else None
        if declaring == n:
            said = f"all {n} meshes declare scale {scale}, but their voxel sizes span {spread}"
        elif declaring == 1:
            # The others' meta.json was unreadable or had no scale: not "all".
            said = (
                f"their voxel sizes span {spread}; 1 of {n} meshes declares a scale "
                f"({scale}), and none was read for the other {n - 1}"
            )
        elif declaring:
            said = (
                f"their voxel sizes span {spread}; {declaring} of {n} meshes declare a "
                f"scale, all {scale}, and none was read for the other {n - declaring}"
            )
        else:
            said = f"their voxel sizes span {spread}, and no meta.json gave a scale"
        tail = " and the metadata does not say so" if declaring else ""
        lines.append(
            f"    COLLISION: {said}. Coordinates are NOT interchangeable{tail}."
        )
    elif n < 2:
        lines.append(
            "    Nothing to compare: only one mesh follows the -on-<scan>-<um>um.tifxyz "
            "convention."
        )
    elif c["voxel_size_spread"] <= 1.001:
        lines.append("    No collision: the meshes share one voxel size.")
    else:
        lines.append(
            "    No collision: frames are distinguishable from their metadata."
        )
    lines.append(
        "    The rel. scale column is a ratio of stated voxel sizes. It is not a "
        "transform:\n    scans differ in origin and orientation, and the "
        "segmented surfaces may differ too."
    )
    return "\n".join(lines)


def _fetch(segment: str):  # pragma: no cover - needs network
    import s3fs

    scroll, seg = segment.strip("/").split("/", 1)
    fs = s3fs.S3FileSystem(anon=True)
    prefix = f"vesuvius-challenge-open-data/{scroll}/segments/{seg}/mesh"
    names = [p for p in fs.ls(prefix, detail=False) if p.endswith(".tifxyz")]
    metas = {}
    for p in names:
        try:
            with fs.open(f"{p}/meta.json") as fh:
                metas[os.path.basename(p)] = json.load(fh)
        except Exception:
            pass
    return names, metas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="show the coordinate frames of one segment")
    p.add_argument("segment", help="e.g. PHercParis4/20230702185753")
    p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if "/" not in args.segment.strip("/"):
        ap.error(
            f"segment must be <scroll>/<segment>, e.g. PHercParis4/20230702185753; got "
            f"{args.segment!r}"
        )

    # Exit 1 means a collision, so a lookup that fails (no s3fs, no network, no such
    # segment) exits 2, as a usage error does, never 1.
    try:
        names, metas = _fetch(args.segment)
    except Exception as exc:
        if isinstance(exc, ImportError) and exc.name == "s3fs":
            why = "the live lookup needs s3fs (pip install s3fs)"
        else:
            why = f"could not list {args.segment}: {type(exc).__name__}: {exc}"
        print(f"scrollframes: {why}", file=sys.stderr)
        return 2
    frames = frames_for(names, metas)
    skipped = [
        os.path.basename(n.rstrip("/")) for n in names if parse_mesh_name(n) is None
    ]
    if skipped:
        print(
            f"scrollframes: skipped {len(skipped)} mesh name(s) off the "
            f"<segment>-on-<scan>-<um>um.tifxyz convention: {', '.join(skipped)}",
            file=sys.stderr,
        )
    if args.json:
        print(
            json.dumps(
                {
                    "segment": args.segment,
                    "frames": [f.__dict__ for f in frames],
                    "skipped": skipped,
                    "collision": collision(frames),
                },
                indent=2,
                default=str,
            )
        )
    else:
        print(render(args.segment, frames))
    return 1 if collision(frames)["collides"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
