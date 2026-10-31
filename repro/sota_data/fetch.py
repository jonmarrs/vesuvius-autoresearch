"""Plan or download one public SOTA segment into a new, verified raw directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path[:0] = [
        str(Path(__file__).resolve().parents[2]),
        str(Path(__file__).resolve().parents[2] / "src"),
    ]

from repro.sota_data.download_artifacts import (
    BUCKET,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_FILE_BYTES,
    MAX_ENTRIES,
    build_plan,
    destination_path,
    execute_plan,
    limits,
    source_prefix,
)


def _filesystem():
    import s3fs

    return s3fs.S3FileSystem(anon=True)


def _prepare(
    s3_seg_prefix,
    out_dir,
    filesystem,
    max_bytes,
    max_file_bytes,
    max_files,
    max_entries,
    center_layers,
):
    options = limits(max_bytes, max_file_bytes, max_files, max_entries, center_layers)
    prefix = source_prefix(s3_seg_prefix)
    output = destination_path(out_dir)
    fs = _filesystem() if filesystem is None else filesystem
    plan = build_plan(fs, prefix, options)
    return fs, prefix, output, plan


def plan_segment(
    s3_seg_prefix,
    out_dir,
    *,
    filesystem=None,
    max_bytes=DEFAULT_MAX_BYTES,
    max_file_bytes=DEFAULT_MAX_FILE_BYTES,
    max_files=512,
    max_entries=MAX_ENTRIES,
    center_layers=None,
):
    """Read remote metadata only; do not create directories or read object bodies."""
    _, _, output, plan = _prepare(
        s3_seg_prefix,
        out_dir,
        filesystem,
        max_bytes,
        max_file_bytes,
        max_files,
        max_entries,
        center_layers,
    )
    return {**plan, "status": "PLANNED", "output": str(output)}


def fetch_segment(
    s3_seg_prefix,
    out_dir,
    *,
    filesystem=None,
    max_bytes=DEFAULT_MAX_BYTES,
    max_file_bytes=DEFAULT_MAX_FILE_BYTES,
    max_files=512,
    max_entries=MAX_ENTRIES,
    center_layers=None,
):
    """Download explicit direct files, publish after all transfers and checks pass.

    Existing destinations are refused. Return out_dir for the existing converter
    handoff. The completion record is out_dir/download.json, not a readiness gate.
    """
    fs, prefix, output, plan = _prepare(
        s3_seg_prefix,
        out_dir,
        filesystem,
        max_bytes,
        max_file_bytes,
        max_files,
        max_entries,
        center_layers,
    )
    execute_plan(fs, prefix, output, plan)
    return out_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "s3_seg_prefix",
        help="bucket-relative prefix or URI in the public Vesuvius bucket",
    )
    parser.add_argument("out_dir", type=Path, help="new local raw-segment directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the metadata plan without object-body reads or output writes",
    )
    parser.add_argument(
        "--center-layers",
        type=int,
        help="download this centered count of sorted numeric layers; same selection rule as convert",
    )
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--max-files", type=int, default=512)
    parser.add_argument("--max-entries", type=int, default=MAX_ENTRIES)
    args = parser.parse_args(argv)
    kwargs = {
        name: getattr(args, name)
        for name in (
            "center_layers",
            "max_bytes",
            "max_file_bytes",
            "max_files",
            "max_entries",
        )
    }
    try:
        if args.dry_run:
            print(
                json.dumps(
                    plan_segment(args.s3_seg_prefix, args.out_dir, **kwargs),
                    indent=2,
                    allow_nan=False,
                )
            )
        else:
            fetch_segment(args.s3_seg_prefix, args.out_dir, **kwargs)
            print(
                f"Downloaded raw segment: {args.out_dir.resolve()}; see download.json. Image geometry and label quality are unverified."
            )
    except (OSError, ValueError, ImportError) as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
