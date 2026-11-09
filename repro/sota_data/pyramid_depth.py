"""Classify an ink surface-volume pyramid that dropped depth slices.

Some published surface volumes store a coarser pyramid level as the first
slices of level 0, pooled in X and Y only, while the OME-Zarr scale says Z
did not change. A 65-slice render then exposes 17 slices at level 2. Reading
that level as a 4x downsampled copy of the whole sheet keeps only the outer
quarter of the depth. A level that declares the matching Z scale, and whose
depth agrees with it, is a different layout: depth was pooled on purpose.

The header check reads a local Zarr v2 group (``.zattrs`` and each level's
``.zarray``). It does not fetch the public ink bucket. ``--compare`` reads
one XY window through the full depth of level 0 and of one coarser level and
reports whether those pixels are slice-indexed copies or a depth pool.

Header check::

    python -m repro.sota_data.pyramid_depth /path/to/segment.zarr

Pixel check of level 2 over a level-0 window (H and W divisible by that
level's XY scale)::

    python -m repro.sota_data.pyramid_depth /path/to/segment.zarr \\
        --compare 2 --origin Y X --size H W

A header check of the volumes whose level 2 keeps 17 of 65 slices needs
those groups on disk, or at least the group ``.zattrs`` and each level's
``.zarray``. This command does not download them.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from numbers import Integral
from pathlib import Path

import numpy as np

SCALE_TOLERANCE = 1e-3
POOL_VOXEL_TOLERANCE = 1.0
POOL_RELATIVE_TOLERANCE = 0.08
CONTENT_HIGH = 0.7
CONTENT_LOW = 0.4
DEFAULT_MAX_VOXELS = 4_000_000
USABLE = frozenset({"full_depth", "depth_pooled"})


def successive_half_depth(depth: int, steps: int) -> int:
    """Depth after ``steps`` rounds of ceil(n / 2), the XY-only pyramid rule."""
    if isinstance(depth, bool) or not isinstance(depth, Integral) or int(depth) < 1:
        raise ValueError("depth must be a positive integer")
    if isinstance(steps, bool) or not isinstance(steps, Integral) or int(steps) < 0:
        raise ValueError("steps must be a nonnegative integer")
    value = int(depth)
    for _ in range(int(steps)):
        value = (value + 1) // 2
    return value


def _shape3(value: object, what: str) -> tuple[int, int, int]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 3
        or any(
            isinstance(item, bool) or not isinstance(item, Integral) or int(item) < 1
            for item in value
        )
    ):
        raise ValueError(f"{what} must be three positive integers")
    return int(value[0]), int(value[1]), int(value[2])


def _scale3(value: object, what: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{what} must be three positive finite numbers")
    scale: list[float] = []
    for item in value:
        if (
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
            or float(item) <= 0
        ):
            raise ValueError(f"{what} must be three positive finite numbers")
        scale.append(float(item))
    return scale[0], scale[1], scale[2]


def _near_one(ratio: float) -> bool:
    return abs(ratio - 1.0) <= SCALE_TOLERANCE


def _depth_matches(depth: int, reference_depth: int, ratio: float) -> bool:
    expected = reference_depth / ratio
    return abs(depth - expected) <= max(
        POOL_VOXEL_TOLERANCE, POOL_RELATIVE_TOLERANCE * expected
    )


def _level_index(path: str) -> int | None:
    if path == "0" or (path.isdigit() and not path.startswith("0")):
        return int(path)
    return None


def _dataset_scale(
    dataset: Mapping[str, object], what: str
) -> tuple[float, float, float]:
    transforms = dataset.get("coordinateTransformations")
    if not isinstance(transforms, list) or any(
        not isinstance(item, Mapping) for item in transforms
    ):
        raise ValueError(f"{what} must include coordinateTransformations")
    scales = [item.get("scale") for item in transforms if item.get("type") == "scale"]
    if len(scales) != 1:
        raise ValueError(f"{what} must include exactly one scale transform")
    return _scale3(scales[0], f"{what} scale")


def pooling_factor(xy_ratio: Sequence[float]) -> int:
    """Integer XY downsample implied by a level's scale, or an error."""
    if len(xy_ratio) != 2:
        raise ValueError("xy scale ratio must have two components")
    y_ratio, x_ratio = float(xy_ratio[0]), float(xy_ratio[1])
    if abs(y_ratio - x_ratio) > SCALE_TOLERANCE:
        raise ValueError(
            f"y and x scale ratios disagree ({y_ratio:.6g} and {x_ratio:.6g})"
        )
    factor = int(round(y_ratio))
    if factor < 1 or abs(y_ratio - factor) > SCALE_TOLERANCE:
        raise ValueError(
            f"xy scale ratio {y_ratio:.6g} is not an integer pooling factor"
        )
    return factor


def assess_levels(levels: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Classify each level against the dataset whose path is ``0``.

    Each item needs ``path``, ``shape`` (z, y, x) and ``scale`` (z, y, x).
    ``full_depth`` keeps every slice at an unchanged Z scale. ``depth_pooled``
    has a Z scale above 1 and a depth within one voxel, or 8%, of
    ``reference_depth / z_scale``. ``truncated`` has an unchanged Z scale and
    a shorter depth: the silent missing-slice layout. Anything else is
    ``inconsistent``.
    """
    if not isinstance(levels, Sequence) or isinstance(levels, (str, bytes)):
        raise ValueError("levels must be a sequence of pyramid levels")
    parsed: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in levels:
        if not isinstance(item, Mapping):
            raise ValueError("each pyramid level must be a mapping")
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("each pyramid level needs a path")
        if path in seen:
            raise ValueError(f"duplicate pyramid level {path!r}")
        seen.add(path)
        shape = _shape3(item.get("shape"), f"{path} shape")
        scale = _scale3(item.get("scale"), f"{path} scale")
        parsed.append({"path": path, "shape": shape, "scale": scale})
    reference = next((level for level in parsed if level["path"] == "0"), None)
    if reference is None:
        raise ValueError("pyramid has no level 0 to compare against")
    reference_shape = reference["shape"]
    reference_scale = reference["scale"]
    assert isinstance(reference_shape, tuple) and isinstance(reference_scale, tuple)
    records: list[dict[str, object]] = []
    for level in parsed:
        shape = level["shape"]
        scale = level["scale"]
        path = level["path"]
        assert isinstance(shape, tuple) and isinstance(scale, tuple)
        assert isinstance(path, str)
        depth, height, width = shape
        ratio = float(scale[0]) / float(reference_scale[0])
        xy_ratio = (
            float(scale[1]) / float(reference_scale[1]),
            float(scale[2]) / float(reference_scale[2]),
        )
        index = _level_index(path)
        halved = (
            None if index is None else successive_half_depth(reference_shape[0], index)
        )
        record: dict[str, object] = {
            "path": path,
            "level": index,
            "shape_zyx": [depth, height, width],
            "z_scale_ratio": ratio,
            "xy_scale_ratio": [xy_ratio[0], xy_ratio[1]],
            "expected_depth_at_z_scale": reference_shape[0] / ratio,
            "depth_matches_successive_xy_halving": (
                None if halved is None else depth == halved
            ),
        }
        if _near_one(ratio) and depth == reference_shape[0]:
            record["status"] = "full_depth"
            record["reason"] = "z scale is unchanged and every depth slice is present"
        elif not _near_one(ratio) and _depth_matches(depth, reference_shape[0], ratio):
            record["status"] = "depth_pooled"
            record["reason"] = "depth matches the declared z scale"
        elif _near_one(ratio) and depth < reference_shape[0]:
            record["status"] = "truncated"
            if halved is not None and depth == halved:
                record["reason"] = (
                    "z scale is unchanged but depth is shorter than level 0; "
                    "the depth matches successive ceil-half XY-only downsampling"
                )
            else:
                record["reason"] = (
                    "z scale is unchanged but depth is shorter than level 0"
                )
        else:
            record["status"] = "inconsistent"
            record["reason"] = "depth does not match the declared z scale"
        records.append(record)
    records.sort(
        key=lambda item: (
            item["level"] is None,
            item["level"] if isinstance(item["level"], int) else 0,
            str(item["path"]),
        )
    )
    return records


def _xy_pool(plane: np.ndarray, factor: int) -> np.ndarray:
    height, width = plane.shape
    if height % factor or width % factor:
        raise ValueError(
            f"plane {plane.shape} is not divisible by pooling factor {factor}"
        )
    folded = np.asarray(plane, dtype=np.float64).reshape(
        height // factor, factor, width // factor, factor
    )
    return folded.mean(axis=(1, 3))


def _correlation(left: np.ndarray, right: np.ndarray) -> float | None:
    left = np.asarray(left, dtype=np.float64).ravel()
    right = np.asarray(right, dtype=np.float64).ravel()
    if left.shape != right.shape or left.size < 2:
        return None
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        return None
    if float(left.std()) == 0.0 or float(right.std()) == 0.0:
        return None
    value = float(np.corrcoef(left, right)[0, 1])
    if not math.isfinite(value):
        return None
    return value


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(np.median(np.asarray(values, dtype=np.float64)))


def content_agreement(
    level0: np.ndarray, coarse: np.ndarray, factor: int
) -> dict[str, object]:
    """Compare one coarse window with the two ways it could have been built.

    ``slice_indexed`` means coarse slice ``i`` matches the XY pool of level-0
    slice ``i`` (the copied-prefix layout, and also a full-depth XY
    downsample). ``depth_pooled`` means it matches the mean of ``factor``
    consecutive level-0 slices. A window whose slices do not vary along depth
    cannot separate the two and is ``ambiguous``.
    """
    level0 = np.asarray(level0)
    coarse = np.asarray(coarse)
    if level0.ndim != 3 or coarse.ndim != 3:
        raise ValueError("volumes must have shape (depth, height, width)")
    if isinstance(factor, bool) or not isinstance(factor, Integral) or int(factor) < 1:
        raise ValueError("factor must be a positive integer")
    factor = int(factor)
    if (
        coarse.shape[1] * factor != level0.shape[1]
        or coarse.shape[2] * factor != level0.shape[2]
    ):
        raise ValueError(
            "coarse height and width must be the level-0 window divided by the pooling factor"
        )
    slice_scores: list[float] = []
    pool_scores: list[float] = []
    fine_depth = int(level0.shape[0])
    coarse_depth = int(coarse.shape[0])
    for index in range(coarse_depth):
        if index < fine_depth:
            score = _correlation(coarse[index], _xy_pool(level0[index], factor))
            if score is not None:
                slice_scores.append(score)
        start = index * factor
        stop = start + factor
        if stop <= fine_depth:
            pooled = np.mean(
                [_xy_pool(level0[depth], factor) for depth in range(start, stop)],
                axis=0,
            )
            score = _correlation(coarse[index], pooled)
            if score is not None:
                pool_scores.append(score)
    slice_median = _median(slice_scores)
    pool_median = _median(pool_scores)
    verdict = "ambiguous"
    if (
        slice_median is not None
        and pool_median is not None
        and slice_median >= CONTENT_HIGH
        and pool_median <= CONTENT_LOW
    ):
        verdict = "slice_indexed"
    elif (
        slice_median is not None
        and pool_median is not None
        and pool_median >= CONTENT_HIGH
        and slice_median <= CONTENT_LOW
    ):
        verdict = "depth_pooled"
    return {
        "factor": factor,
        "slices_scored_slice_indexed": len(slice_scores),
        "slices_scored_depth_pooled": len(pool_scores),
        "median_r_slice_indexed": slice_median,
        "median_r_depth_pooled": pool_median,
        "verdict": verdict,
    }


def _load_json(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"could not read {path}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"could not parse {path}: {exc}") from exc


def _level_directory(root: Path, relative: str) -> Path:
    if not relative or relative.startswith(("/", "\\")) or "\\" in relative:
        raise ValueError(f"dataset path must stay inside the zarr group: {relative!r}")
    parts = Path(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"dataset path must stay inside the zarr group: {relative!r}")
    root_resolved = root.resolve()
    directory = root.joinpath(*parts).resolve()
    if directory != root_resolved and root_resolved not in directory.parents:
        raise ValueError(f"dataset path escapes the zarr group: {relative!r}")
    return directory


def _axes_zyx(frame: Mapping[str, object]) -> None:
    axes = frame.get("axes")
    if not isinstance(axes, list) or any(
        not isinstance(axis, Mapping) for axis in axes
    ):
        raise ValueError("OME-Zarr axes must be named z, y, x in that order")
    names = [axis.get("name") for axis in axes]
    if names != ["z", "y", "x"]:
        raise ValueError(
            f"OME-Zarr axes must be named z, y, x in that order, got {names}"
        )


def load_levels(root: Path) -> list[dict[str, object]]:
    """Read level path, shape and scale from a local Zarr v2 group."""
    if not root.is_dir():
        raise ValueError(f"pyramid path is not a directory: {root}")
    attrs_path = root / ".zattrs"
    if not attrs_path.is_file():
        raise ValueError(f"{root} has no .zattrs multiscale metadata")
    attrs = _load_json(attrs_path)
    if not isinstance(attrs, Mapping):
        raise ValueError(f"{attrs_path} must be a JSON object")
    multiscales = attrs.get("multiscales")
    if (
        not isinstance(multiscales, list)
        or len(multiscales) != 1
        or not isinstance(multiscales[0], Mapping)
    ):
        raise ValueError("expected exactly one OME-Zarr multiscales entry")
    frame = multiscales[0]
    _axes_zyx(frame)
    datasets = frame.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("multiscales entry has no datasets")
    levels: list[dict[str, object]] = []
    for dataset in datasets:
        if not isinstance(dataset, Mapping):
            raise ValueError("each dataset must be a JSON object")
        path = dataset.get("path")
        if not isinstance(path, str):
            raise ValueError("each dataset needs a path")
        array_meta = _load_json(_level_directory(root, path) / ".zarray")
        if not isinstance(array_meta, Mapping):
            raise ValueError(f"{path}/.zarray must be a JSON object")
        if array_meta.get("zarr_format") not in (None, 2):
            raise ValueError(f"{path} is not a Zarr v2 array")
        levels.append(
            {
                "path": path,
                "shape": _shape3(array_meta.get("shape"), f"{path} shape"),
                "scale": _dataset_scale(dataset, path),
            }
        )
    return levels


def _content_agrees(status: str, verdict: str) -> bool:
    if status == "full_depth":
        return verdict == "slice_indexed"
    if status == "depth_pooled":
        return verdict == "depth_pooled"
    return False


def _chunk_names(
    shape: Sequence[int],
    chunks: Sequence[int],
    origin: Sequence[int],
    size: Sequence[int],
    separator: str,
) -> list[str]:
    names: list[str] = []
    spans: list[range] = []
    for start, count, chunk, limit in zip(origin, size, chunks, shape, strict=True):
        if count < 1 or start < 0 or start + count > limit:
            raise ValueError(
                f"window origin {tuple(origin)} size {tuple(size)} is outside shape {tuple(shape)}"
            )
        spans.append(range(start // chunk, (start + count - 1) // chunk + 1))
    for z_index in spans[0]:
        for y_index in spans[1]:
            for x_index in spans[2]:
                names.append(
                    separator.join(str(index) for index in (z_index, y_index, x_index))
                )
    return names


def _require_chunks(
    array_dir: Path, origin: Sequence[int], size: Sequence[int]
) -> None:
    meta = _load_json(array_dir / ".zarray")
    if not isinstance(meta, Mapping):
        raise ValueError(f"{array_dir.name}/.zarray must be a JSON object")
    shape = _shape3(meta.get("shape"), f"{array_dir.name} shape")
    chunks = _shape3(meta.get("chunks"), f"{array_dir.name} chunks")
    separator = meta.get("dimension_separator", ".")
    if not isinstance(separator, str) or separator not in {".", "/"}:
        raise ValueError(f"{array_dir.name} has an unsupported dimension separator")
    missing = [
        name
        for name in _chunk_names(shape, chunks, origin, size, separator)
        if not (array_dir / name).is_file()
    ]
    if missing:
        raise ValueError(
            f"{array_dir.name} is missing {len(missing)} chunk(s) for this window; "
            f"the first is {missing[0]}"
        )


def _read_window(
    root: Path, level: str, origin: tuple[int, int, int], size: tuple[int, int, int]
) -> np.ndarray:
    directory = _level_directory(root, level)
    _require_chunks(directory, origin, size)
    import zarr

    array = zarr.open(str(directory), mode="r")
    z0, y0, x0 = origin
    depth, height, width = size
    data = np.asarray(array[z0 : z0 + depth, y0 : y0 + height, x0 : x0 + width])
    if data.shape != (depth, height, width):
        raise ValueError(
            f"{level} read returned shape {data.shape}, expected {(depth, height, width)}"
        )
    return data


def _compare_window(
    root: Path,
    records: Sequence[Mapping[str, object]],
    level: str,
    origin_y: int,
    origin_x: int,
    height: int,
    width: int,
    max_voxels: int,
) -> dict[str, object]:
    chosen = next((record for record in records if record["path"] == level), None)
    reference = next(record for record in records if record["path"] == "0")
    if chosen is None:
        raise ValueError(f"pyramid has no level {level!r}")
    if level == "0":
        raise ValueError(
            "compare a coarser level with level 0, not level 0 with itself"
        )
    xy_ratio = chosen["xy_scale_ratio"]
    if not isinstance(xy_ratio, list):
        raise ValueError(f"{level} is missing an xy scale ratio")
    factor = pooling_factor(xy_ratio)
    for name, value in (
        ("origin y", origin_y),
        ("origin x", origin_x),
        ("height", height),
        ("width", width),
    ):
        if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    origin_y, origin_x, height, width = (
        int(origin_y),
        int(origin_x),
        int(height),
        int(width),
    )
    if min(height, width) < factor or any(
        value % factor for value in (origin_y, origin_x, height, width)
    ):
        raise ValueError(
            f"the level-0 window must be aligned to the pooling factor {factor}"
        )
    reference_shape = reference["shape_zyx"]
    coarse_shape = chosen["shape_zyx"]
    if not isinstance(reference_shape, list) or not isinstance(coarse_shape, list):
        raise ValueError("classified levels are missing shapes")
    fine_depth = int(reference_shape[0])
    coarse_depth = int(coarse_shape[0])
    coarse_origin_y = origin_y // factor
    coarse_origin_x = origin_x // factor
    coarse_height = height // factor
    coarse_width = width // factor
    voxels = fine_depth * height * width + coarse_depth * coarse_height * coarse_width
    if voxels > max_voxels:
        raise ValueError(
            f"window would read {voxels} voxels, above the cap of {max_voxels}; "
            "choose a smaller XY window"
        )
    fine = _read_window(root, "0", (0, origin_y, origin_x), (fine_depth, height, width))
    coarse = _read_window(
        root,
        level,
        (0, coarse_origin_y, coarse_origin_x),
        (coarse_depth, coarse_height, coarse_width),
    )
    agreement = content_agreement(fine, coarse, factor)
    status = str(chosen["status"])
    agreement["level"] = level
    agreement["agrees_with_metadata"] = _content_agrees(
        status, str(agreement["verdict"])
    )
    return agreement


def assess(
    root: Path,
    compare: tuple[str, int, int, int, int] | None = None,
    max_voxels: int = DEFAULT_MAX_VOXELS,
) -> dict[str, object]:
    """Classify ``root`` and, if asked, compare one level's pixels with level 0."""
    if (
        isinstance(max_voxels, bool)
        or not isinstance(max_voxels, Integral)
        or int(max_voxels) < 1
    ):
        raise ValueError("max voxels must be a positive integer")
    records = assess_levels(load_levels(root))
    content = None
    if compare is not None:
        level, origin_y, origin_x, height, width = compare
        content = _compare_window(
            root, records, level, origin_y, origin_x, height, width, int(max_voxels)
        )
    header_ok = all(record["status"] in USABLE for record in records)
    pixels_ok = content is None or content["agrees_with_metadata"] is True
    return {
        "source": str(root),
        "ok": bool(header_ok and pixels_ok),
        "usable_levels": [
            str(record["path"]) for record in records if record["status"] in USABLE
        ],
        "levels": records,
        "content": content,
    }


def format_report(report: Mapping[str, object]) -> str:
    lines = [f"source: {report['source']}", f"ok: {report['ok']}"]
    levels = report["levels"]
    if isinstance(levels, list):
        for level in levels:
            if not isinstance(level, Mapping):
                continue
            shape = level["shape_zyx"]
            if not isinstance(shape, list):
                continue
            rendered = ",".join(str(value) for value in shape)
            ratio_value = level["z_scale_ratio"]
            if isinstance(ratio_value, bool) or not isinstance(
                ratio_value, (int, float)
            ):
                continue
            ratio = float(ratio_value)
            lines.append(
                f"level {level['path']}: shape [{rendered}] "
                f"z-scale {ratio:.6g} {level['status']}"
            )
            if level["status"] == "truncated":
                lines.append(f"  {level['reason']}")
    content = report.get("content")
    if isinstance(content, Mapping):
        lines.append(
            f"pixels {content['level']}: {content['verdict']} "
            f"slice-index r={content['median_r_slice_indexed']} "
            f"depth-pool r={content['median_r_depth_pooled']}"
        )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check whether an ink surface-volume pyramid kept every depth slice. "
            "A coarser level whose z scale is unchanged but whose depth is shorter "
            "than level 0 is the silent truncation that keeps 17 of 65 slices."
        ),
        epilog=(
            "The header check needs a local Zarr v2 group. Pixel comparison reads "
            "one XY window through the full depth and refuses a window above "
            f"{DEFAULT_MAX_VOXELS} voxels. This command does not download data."
        ),
    )
    parser.add_argument("pyramid", type=Path, help="local Zarr v2 group")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument(
        "--compare",
        metavar="LEVEL",
        help="compare this coarser level's pixels with level 0",
    )
    parser.add_argument(
        "--origin",
        nargs=2,
        type=int,
        metavar=("Y", "X"),
        help="level-0 row and column where the pixel window starts",
    )
    parser.add_argument(
        "--size",
        nargs=2,
        type=int,
        metavar=("H", "W"),
        help="level-0 height and width of the pixel window",
    )
    parser.add_argument(
        "--max-voxels",
        type=int,
        default=DEFAULT_MAX_VOXELS,
        help=f"cap on voxels read by --compare (default {DEFAULT_MAX_VOXELS})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    requested = (
        args.compare is not None,
        args.origin is not None,
        args.size is not None,
    )
    if any(requested) and not all(requested):
        print(
            "error: --compare, --origin and --size are used together",
            file=sys.stderr,
        )
        return 2
    compare = None
    if args.compare is not None:
        origin_y, origin_x = args.origin
        height, width = args.size
        compare = (
            str(args.compare),
            int(origin_y),
            int(origin_x),
            int(height),
            int(width),
        )
    try:
        report = assess(args.pyramid, compare=compare, max_voxels=args.max_voxels)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_report(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
