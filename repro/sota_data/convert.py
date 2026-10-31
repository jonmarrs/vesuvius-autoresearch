"""Bounded raw-TIFF conversion; help imports neither image libraries nor ML/S3."""

import argparse
import json
import sys

SHAPE_TOLERANCE_PX = 2
DEFAULT_MAX_VOXELS = 128 * 1024**2


def to_uint8(arr, *, float_encoding="auto"):
    """Compatibility export used by teacher-label preparation."""
    from .fragment import to_uint8 as convert

    return convert(arr, float_encoding=float_encoding)


def convert_surface_volume(
    src_dir,
    seg_id,
    out_root,
    n_layers=26,
    start_idx=17,
    *,
    float_encoding="auto",
    max_voxels=DEFAULT_MAX_VOXELS,
):
    from .conversion_artifacts import convert

    return convert(
        src_dir, seg_id, out_root, n_layers, start_idx, float_encoding, max_voxels
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, help="local raw segment directory")
    parser.add_argument("--segment", required=True, help="new fragment id")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--layers", type=int, default=26)
    parser.add_argument("--start-idx", type=int, default=17)
    parser.add_argument(
        "--float-encoding", choices=("auto", "unit", "byte"), default="auto"
    )
    parser.add_argument("--max-voxels", type=int, default=DEFAULT_MAX_VOXELS)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="inspect headers; no pixel decoding or output writes",
    )
    args = parser.parse_args(argv)
    try:
        from .conversion_artifacts import build_plan, convert

        arguments = (
            args.src,
            args.segment,
            args.out_root,
            args.layers,
            args.start_idx,
            args.float_encoding,
            args.max_voxels,
        )
        result = (
            build_plan(*arguments) if args.dry_run else {"output": convert(*arguments)}
        )
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError) as exc:
        print(f"conversion failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
