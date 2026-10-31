"""CPU conversion CLI for the maintained detector data-preparation helpers."""

import argparse
import sys
from pathlib import Path

# Support this historical command directly from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vesuvius_autoresearch.core.fragment_conversion import (
    MAX_PIXELS,
    conversion_status,
    convert_fragment,
    convert_layer_u16_to_u8,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frag", required=True)
    parser.add_argument("--src-root", default="local_data")
    parser.add_argument("--dst-root", default="villa/ink-detection/train_scrolls")
    parser.add_argument(
        "--z-start", type=int, default=17, help="DetectorConfig.start_idx"
    )
    parser.add_argument("--z-end", type=int, default=43, help="DetectorConfig.end_idx")
    parser.add_argument("--max-pixels", type=int, default=MAX_PIXELS)
    parser.add_argument(
        "--check",
        "--dry-run",
        action="store_true",
        help="check reusable outputs without reading raw sources or writing; exit 2 if conversion is needed",
    )
    args = parser.parse_args(argv)
    if args.check:
        ready, reason = conversion_status(
            args.dst_root,
            args.frag,
            args.z_start,
            args.z_end,
            max_pixels=args.max_pixels,
        )
        print(f"{args.frag}: {'READY' if ready else 'NEEDS_CONVERSION'}: {reason}")
        return 0 if ready else 2
    try:
        stats = convert_fragment(
            args.frag,
            args.src_root,
            args.dst_root,
            args.z_start,
            args.z_end,
            max_pixels=args.max_pixels,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"conversion failed: {exc}\n")
    lo = min(s["u8_mean"] for s in stats.values())
    hi = max(s["u8_mean"] for s in stats.values())
    print(f"{args.frag}: converted {len(stats)} layers; u8_mean range [{lo}, {hi}]")
    print(f"Completion manifest: {Path(args.dst_root) / args.frag / 'conversion.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
