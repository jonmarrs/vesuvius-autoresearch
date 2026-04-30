#!/usr/bin/env python3
"""
Generate or execute predict.py commands for top ranked Scroll 2/3 candidates.

Dry-run is the default. Use --execute to run commands serially.
"""
import argparse
import csv
import shlex
import subprocess
import sys
from pathlib import Path


def _as_int(row, key, default=0):
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return default


def build_predict_command(row, python_executable=sys.executable, prediction_dir="predictions"):
    width = _as_int(row, "width", _as_int(row, "patch_size", 64))
    height = _as_int(row, "height", _as_int(row, "patch_size", 64))
    stem = row.get("artifact_stem") or f"pred_{_as_int(row, 'z')}_{_as_int(row, 'y')}_{_as_int(row, 'x')}_{width}x{height}"
    uri = row.get("local_uri") or row.get("source_uri")
    if not uri:
        raise ValueError(f"candidate {stem} has no local_uri/source_uri")

    output_img = str(Path(prediction_dir) / f"{stem}.png")
    metadata_out = str(Path(prediction_dir) / f"{stem}_meta.json")
    return [
        python_executable,
        "predict.py",
        "--uri",
        uri,
        "--z",
        str(_as_int(row, "z")),
        "--y",
        str(_as_int(row, "y")),
        "--x",
        str(_as_int(row, "x")),
        "--width",
        str(width),
        "--height",
        str(height),
        "--patch_size",
        str(_as_int(row, "patch_size", width)),
        "--output_img",
        output_img,
        "--metadata_out",
        metadata_out,
    ]


def load_candidates(path, limit=None, require_local=True):
    with open(path, "r", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if require_local:
        rows = [row for row in rows if row.get("local_uri")]
    if limit is not None:
        rows = rows[:limit]
    return rows


def write_manifest(commands, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for cmd in commands:
            f.write(shlex.join(cmd) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--prediction-dir", default="predictions")
    parser.add_argument("--manifest", default="reports/scroll23_inference_commands.sh")
    parser.add_argument("--execute", action="store_true", help="Run commands serially; default only writes/prints commands")
    parser.add_argument("--allow-missing-local-uri", action="store_true")
    args = parser.parse_args()

    rows = load_candidates(args.ranked, limit=args.limit, require_local=not args.allow_missing_local_uri)
    commands = [build_predict_command(row, prediction_dir=args.prediction_dir) for row in rows]
    write_manifest(commands, args.manifest)

    print(f"Wrote {len(commands)} inference commands to {args.manifest}")
    for cmd in commands:
        print(shlex.join(cmd))

    if args.execute:
        for cmd in commands:
            subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
