"""WebKnossos NML skeleton I/O for the fiber-skeletons ground truth.

The `fiber-skeletons` dataset (dl.ash2txt.org/datasets/fiber-skeletons/) ships
both a voxelized semantic label (`labelsTr/*.tif`, background/fiber only) and the
**original per-fiber WebKnossos traces** (`nml/*.nml`). Only the NMLs carry fiber
identity and connectivity, so they are the only usable ground truth for
connectivity metrics such as expected run length.

Coordinate conventions, verified empirically against the shipped semantic labels
(see `reports/fiber_tracing_step0_gt_survey.md`):

- The published NML `<node x= y= z=>` use integer voxel coordinates in
  **absolute scroll space**, matching the older 7.91 um scan frame. The reader
  also preserves finite fractional coordinates from other NML exports.
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

import hashlib
import math
import re
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Version 1 used attribute-order-sensitive regexes and integer coordinates.
# Keep this separate from SCORING_VERSION: the metric formulas have not changed.
NML_PARSER_VERSION = 2
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
    source_sha256: str | None = None  # NML bytes parsed; None for constructed graphs

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


def _identifier(element, name, path, context):
    try:
        value = int(element.attrib[name])
        if not 0 <= value <= np.iinfo(np.int64).max:
            raise ValueError
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"{path}: {context} {name} must be a nonnegative int64 identifier"
        ) from exc
    return value


def _coordinate(element, name, path, context, *, positive=False):
    try:
        value = float(element.attrib[name])
        if not math.isfinite(value) or (positive and value <= 0):
            raise ValueError
    except (KeyError, ValueError) as exc:
        requirement = "finite and positive" if positive else "finite"
        raise ValueError(f"{path}: {context} {name} must be {requirement}") from exc
    return value


def parse_nml(path, origin_zyx=None, *, strict_edges=False) -> Skeleton:
    """Parse a WebKnossos NML into per-fiber graphs.

    Args:
        path: NML file.
        origin_zyx: if given, subtract this origin so coordinates become
            volume-local. Absolute scroll coordinates are kept otherwise.

        strict_edges: refuse edges referencing missing nodes. By default these
            edges are dropped with a warning, preserving the legacy graph rule.

    XML attribute order, quoting, namespaces and empty-element syntax do not
    affect the graph. Node/edge order remains the document's order. Invalid XML,
    invalid geometry and ambiguous duplicate IDs fail with source context.
    """
    path = Path(path)
    if not isinstance(strict_edges, bool):
        raise ValueError(f"{path}: strict_edges must be a boolean")
    off = None
    if origin_zyx is not None:
        try:
            raw_origin = np.asarray(origin_zyx)
            if (
                raw_origin.shape != (3,)
                or raw_origin.dtype.kind not in "iuf"
                or any(isinstance(v, (bool, np.bool_)) for v in origin_zyx)
                or not np.isfinite(raw_origin).all()
            ):
                raise ValueError
            off = raw_origin.astype(float)
            if not np.isfinite(off).all():
                raise ValueError
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                f"{path}: origin must be a finite numeric (z, y, x) vector"
            ) from exc

    try:
        source = path.read_bytes()
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise ValueError(f"{path}: invalid NML XML: {exc}") from exc
    if root.tag.rsplit("}", 1)[-1] != "things":
        raise ValueError(f"{path}: NML root must be things")
    namespace = root.tag[: root.tag.rfind("}") + 1]

    scale = None
    scales = list(root.iter(f"{namespace}scale"))
    if len(scales) > 1:
        raise ValueError(f"{path}: multiple scale elements are ambiguous")
    if scales:
        sx, sy, sz = (
            _coordinate(scales[0], axis, path, "scale", positive=True) for axis in "xyz"
        )
        scale = (sz, sy, sx)

    fibers: list[Fiber] = []
    thing_ids = set()
    dangling = 0
    for thing in root.iter(f"{namespace}thing"):
        tid = _identifier(thing, "id", path, "thing")
        if tid in thing_ids:
            raise ValueError(f"{path}: duplicate thing id {tid}")
        thing_ids.add(tid)
        if any(child is not thing for child in thing.iter(f"{namespace}thing")):
            raise ValueError(f"{path}: nested thing elements are ambiguous")
        ids_list, xyz_list = [], []
        index_of = {}
        for node in thing.iter(f"{namespace}node"):
            nid = _identifier(node, "id", path, f"thing {tid} node")
            if nid in index_of:
                raise ValueError(f"{path}: duplicate node id {nid} in thing {tid}")
            index_of[nid] = len(ids_list)
            ids_list.append(nid)
            xyz_list.append(
                [
                    _coordinate(node, axis, path, f"thing {tid} node {nid}")
                    for axis in "xyz"
                ]
            )
        ids = np.array(ids_list, dtype=np.int64)
        # NML lists x, y, z; store as (z, y, x) to match volume indexing.
        xyz = np.array(xyz_list, dtype=float).reshape(-1, 3)
        coords = xyz[:, ::-1].copy()
        if off is not None:
            with np.errstate(over="ignore", invalid="ignore"):
                coords -= off
            if not np.isfinite(coords).all():
                raise ValueError(f"{path}: localized node coordinates must be finite")

        pairs = []
        for edge in thing.iter(f"{namespace}edge"):
            s = _identifier(edge, "source", path, f"thing {tid} edge")
            t = _identifier(edge, "target", path, f"thing {tid} edge")
            si, ti = index_of.get(s), index_of.get(t)
            if si is not None and ti is not None:
                pairs.append((si, ti))
            elif strict_edges:
                raise ValueError(f"{path}: dangling edge {s}->{t} in thing {tid}")
            else:
                dangling += 1
        if not ids_list:
            continue
        edges = (
            np.array(pairs, dtype=np.int64)
            if pairs
            else np.zeros((0, 2), dtype=np.int64)
        )

        fibers.append(
            Fiber(
                id=tid,
                name=thing.get("name", ""),
                node_ids=ids,
                coords=coords,
                edges=edges,
            )
        )

    if dangling:
        warnings.warn(
            f"{path}: dropped {dangling} dangling edge(s) referencing missing nodes; "
            "use strict_edges=True or benchmark --strict-nml to refuse partial graphs",
            RuntimeWarning,
            stacklevel=2,
        )
    return Skeleton(
        fibers=fibers,
        scale_um=scale,
        origin_zyx=origin_zyx,
        source_sha256=hashlib.sha256(source).hexdigest(),
    )


def load_cube_skeleton(data_dir, stem: str, *, strict_edges=False) -> Skeleton:
    """Load ``<stem>.nml`` from ``data_dir``, already localized to the cube."""
    origin = origin_from_stem(stem)
    return parse_nml(
        Path(data_dir) / f"{stem}.nml", origin_zyx=origin, strict_edges=strict_edges
    )


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
