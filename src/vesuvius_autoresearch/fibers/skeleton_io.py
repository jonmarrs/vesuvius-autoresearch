"""WebKnossos NML skeleton I/O for the fiber-skeletons ground truth.

The `fiber-skeletons` dataset (dl.ash2txt.org/datasets/fiber-skeletons/) ships
both a voxelized semantic label (`labelsTr/*.tif`, background/fiber only) and the
**original per-fiber WebKnossos traces** (`nml/*.nml`). Only the NMLs carry fiber
identity and connectivity, so they are the only usable ground truth for
connectivity metrics such as expected run length.

Coordinate conventions, verified empirically against the shipped semantic labels
(see `reports/fiber_tracing_step0_gt_survey.md`):

- NML `<node x= y= z=>` are integer voxel coordinates in **absolute scroll
  space**, matching the older 7.91 um scan frame.
- The cube origin is encoded in the dataset filename as ``<scroll>_<z>_<y>_<x>_<size>``,
  so ``s1_00497_01497_03997_256`` has origin (x=3997, y=1497, z=497) and extent 256.
- Volumes index as ``vol[z, y, x]``. With the origin subtracted, in-bounds nodes
  land on semantic-positive voxels at a rate of exactly 1.000 on both cubes
  checked, which is what pins the convention.
- Annotators traced somewhat beyond the cube boundary (WebKnossos shows
  surrounding context), so roughly 14-34% of nodes fall outside the cube. Those
  must be excluded from anything scored against the volume, which is why
  `in_bounds_mask` exists rather than clipping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

_NODE_RE = re.compile(
    r'<node\s+id="(\d+)"[^>]*?\sx="(-?\d+)"\s+y="(-?\d+)"\s+z="(-?\d+)"'
)
_EDGE_RE = re.compile(r'<edge\s+source="(\d+)"\s+target="(\d+)"\s*/>')
_THING_RE = re.compile(r'<thing\s+id="(\d+)"([^>]*)>(.*?)</thing>', re.S)
_NAME_RE = re.compile(r'name="([^"]*)"')
_SCALE_RE = re.compile(r'<scale\s+x="([\d.]+)"\s+y="([\d.]+)"\s+z="([\d.]+)"')
_STEM_RE = re.compile(
    r"^(?P<scroll>[a-z0-9]+)_(?P<z>\d+)_(?P<y>\d+)_(?P<x>\d+)_(?P<size>\d+)"
)


@dataclass
class Fiber:
    """One traced fiber: a graph of nodes, usually a path but may branch."""

    id: int
    name: str
    node_ids: np.ndarray  # (N,) int
    coords: np.ndarray  # (N, 3) float, ordered (z, y, x)
    edges: np.ndarray  # (E, 2) int, indices into node_ids/coords

    def __len__(self) -> int:
        return len(self.node_ids)

    def segment_lengths(self, voxel_size_um: float | None = None) -> np.ndarray:
        """Euclidean length of every edge, in voxels or micrometres."""
        if len(self.edges) == 0:
            return np.zeros(0, dtype=float)
        a = self.coords[self.edges[:, 0]]
        b = self.coords[self.edges[:, 1]]
        lens = np.linalg.norm(a - b, axis=1)
        if voxel_size_um is not None:
            lens = lens * voxel_size_um
        return lens

    def total_length(self, voxel_size_um: float | None = None) -> float:
        return float(self.segment_lengths(voxel_size_um).sum())

    def in_bounds_mask(self, shape) -> np.ndarray:
        """Nodes strictly inside a volume of the given (Z, Y, X) shape."""
        c = self.coords
        ok = np.ones(len(c), dtype=bool)
        for axis in range(3):
            ok &= (c[:, axis] >= 0) & (c[:, axis] <= shape[axis] - 1)
        return ok


@dataclass
class Skeleton:
    """All fibers from one NML, plus the frame metadata needed to use them."""

    fibers: list[Fiber] = field(default_factory=list)
    scale_um: tuple[float, float, float] | None = None  # (z, y, x)
    origin_zyx: tuple[int, int, int] | None = None

    def __len__(self) -> int:
        return len(self.fibers)

    @property
    def n_nodes(self) -> int:
        return int(sum(len(f) for f in self.fibers))

    @property
    def n_edges(self) -> int:
        return int(sum(len(f.edges) for f in self.fibers))

    def total_length(self, voxel_size_um: float | None = None) -> float:
        return float(sum(f.total_length(voxel_size_um) for f in self.fibers))


def origin_from_stem(stem: str) -> tuple[int, int, int]:
    """Cube origin as (z, y, x) from a dataset stem like ``s1_00497_01497_03997_256``.

    Note the filename order is z, y, x, which is the opposite of the NML's
    ``x=`` ``y=`` ``z=`` attribute order. Getting this backwards is silent and
    produces a plausible-looking but wrong registration, so it is parsed in one
    place only.
    """
    m = _STEM_RE.match(Path(stem).name)
    if m is None:
        raise ValueError(f"cannot parse cube origin from stem: {stem!r}")
    return (int(m.group("z")), int(m.group("y")), int(m.group("x")))


def size_from_stem(stem: str) -> int:
    m = _STEM_RE.match(Path(stem).name)
    if m is None:
        raise ValueError(f"cannot parse cube size from stem: {stem!r}")
    return int(m.group("size"))


def parse_nml(path, origin_zyx=None) -> Skeleton:
    """Parse a WebKnossos NML into per-fiber graphs.

    Args:
        path: NML file.
        origin_zyx: if given, subtract this origin so coordinates become
            volume-local. Absolute scroll coordinates are kept otherwise.

    Nodes referenced by an edge but absent from the tree are dropped along with
    that edge rather than silently indexing garbage; malformed traces exist in
    hand-annotated data and must not become fake geometry.
    """
    raw = Path(path).read_text(errors="replace")

    scale = None
    ms = _SCALE_RE.search(raw)
    if ms:
        sx, sy, sz = (float(ms.group(i)) for i in (1, 2, 3))
        scale = (sz, sy, sx)

    off = np.asarray(origin_zyx, dtype=float) if origin_zyx is not None else None

    fibers: list[Fiber] = []
    for tid, attrs, body in _THING_RE.findall(raw):
        nm = _NAME_RE.search(attrs)
        nodes = _NODE_RE.findall(body)
        if not nodes:
            continue
        ids = np.array([int(n[0]) for n in nodes], dtype=np.int64)
        # NML lists x, y, z; store as (z, y, x) to match volume indexing.
        xyz = np.array([[int(n[1]), int(n[2]), int(n[3])] for n in nodes], dtype=float)
        coords = xyz[:, ::-1].copy()
        if off is not None:
            coords -= off

        index_of = {int(v): i for i, v in enumerate(ids)}
        pairs = []
        for s, t in _EDGE_RE.findall(body):
            si, ti = index_of.get(int(s)), index_of.get(int(t))
            if si is not None and ti is not None:
                pairs.append((si, ti))
        edges = (
            np.array(pairs, dtype=np.int64)
            if pairs
            else np.zeros((0, 2), dtype=np.int64)
        )

        fibers.append(
            Fiber(
                id=int(tid),
                name=nm.group(1) if nm else "",
                node_ids=ids,
                coords=coords,
                edges=edges,
            )
        )

    return Skeleton(fibers=fibers, scale_um=scale, origin_zyx=origin_zyx)


def load_cube_skeleton(data_dir, stem: str) -> Skeleton:
    """Load ``<stem>.nml`` from ``data_dir``, already localized to the cube."""
    origin = origin_from_stem(stem)
    return parse_nml(Path(data_dir) / f"{stem}.nml", origin_zyx=origin)


def rasterize(skeleton: Skeleton, shape, dilate: int = 0) -> np.ndarray:
    """Instance-label volume from a skeleton: 0 background, else fiber index+1.

    Edges are walked at sub-voxel steps so a label is written along the whole
    polyline, not only at annotated nodes (nodes sit ~1-2 voxels apart but are
    not guaranteed adjacent). Where fibers collide the later index wins; that is
    reported by the caller rather than resolved here, since overlap is a
    property of the annotation worth knowing about.
    """
    out = np.zeros(shape, dtype=np.int32)
    for i, f in enumerate(skeleton.fibers, start=1):
        if len(f.edges) == 0:
            pts = f.coords
        else:
            a = f.coords[f.edges[:, 0]]
            b = f.coords[f.edges[:, 1]]
            seg = np.linalg.norm(a - b, axis=1)
            steps = np.maximum(2, np.ceil(seg * 2).astype(int))
            chunks = [
                a[k][None, :]
                + (b[k] - a[k])[None, :] * np.linspace(0, 1, steps[k])[:, None]
                for k in range(len(seg))
            ]
            pts = np.concatenate(chunks, axis=0) if chunks else f.coords
        idx = np.rint(pts).astype(int)
        ok = np.ones(len(idx), dtype=bool)
        for axis in range(3):
            ok &= (idx[:, axis] >= 0) & (idx[:, axis] < shape[axis])
        idx = idx[ok]
        if len(idx):
            out[idx[:, 0], idx[:, 1], idx[:, 2]] = i

    if dilate > 0:
        from scipy import ndimage

        st = ndimage.generate_binary_structure(3, 3)
        grown = out.copy()
        for _ in range(dilate):
            mask = grown > 0
            dil = ndimage.grey_dilation(grown, footprint=st)
            grown = np.where(mask, grown, dil)
        out = grown
    return out
