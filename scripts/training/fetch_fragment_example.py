#!/usr/bin/env python3
"""Fetch a pinned official surface-fragment example and prepare binary PNGs.

Keeps uint16 TIFF bytes unchanged; no training, configuration change or import.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=ROOT / "configs/data/fr47_two_layers.json"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="new download directory"
    )
    parser.add_argument("--max-download-bytes", type=int, default=512 * 1024**2)
    parser.add_argument("--max-file-bytes", type=int, default=128 * 1024**2)
    args = parser.parse_args(argv)
    import json
    import urllib.error

    from vesuvius_autoresearch.core.fragment_example import fetch_example

    try:
        path = fetch_example(
            args.manifest,
            args.output,
            max_download_bytes=args.max_download_bytes,
            max_file_bytes=args.max_file_bytes,
        )
        print(json.dumps({"status": "complete", "path": str(path)}))
        return 0
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
        urllib.error.URLError,
    ) as exc:
        print(f"fragment example fetch: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
