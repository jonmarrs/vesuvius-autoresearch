#!/usr/bin/env python3
"""
Generate or execute predict.py commands for top ranked Scroll 2/3 candidates.

Dry-run is the default. Use --execute to run commands serially.
"""

import argparse
import csv
import io
import math
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

if __package__ in (None, ""):
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root), str(root / "src")]

from scripts.text_snapshot import Snapshot
from vesuvius_autoresearch.core.file_modes import replacement_mode
from vesuvius_autoresearch.core.prediction_artifacts import (
    prediction_paths,
    prediction_stem,
    validate_plan_paths,
)

PREDICT_SCRIPT = Path(__file__).resolve().with_name("predict.py")
MAX_CANDIDATE_BYTES = 16 * 1024**2
MAX_CANDIDATE_ROWS = 100_000


def _as_int(row, key, default=0):
    try:
        value = row.get(key, default)
        number = float(value)
        if (
            isinstance(value, bool)
            or not math.isfinite(number)
            or not number.is_integer()
        ):
            raise ValueError
        return int(number)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"candidate {key} must be an integer") from exc


def build_predict_command(
    row,
    python_executable=sys.executable,
    prediction_dir="predictions",
    checkpoint="best_model.pt",
):
    width = _as_int(row, "width", _as_int(row, "patch_size", 64))
    height = _as_int(row, "height", _as_int(row, "patch_size", 64))
    patch = _as_int(row, "patch_size", 64)
    if min(width, height, patch) <= 0 or width < patch or height < patch:
        raise ValueError(
            "candidate width and height must be at least one positive patch"
        )
    if any(key not in row or _as_int(row, key) < 0 for key in ("x", "y", "z")):
        raise ValueError("candidate must provide nonnegative x/y/z voxel indices")
    stem = prediction_stem(
        f"pred_{_as_int(row, 'z')}_{_as_int(row, 'y')}_{_as_int(row, 'x')}_{width}x{height}",
        row.get("artifact_stem") or None,
    )
    uri = row.get("local_uri") or row.get("source_uri")
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError(f"candidate {stem} has no local_uri/source_uri")

    output_img = str(Path(prediction_dir) / f"{stem}.png")
    metadata_out = str(Path(prediction_dir) / f"{stem}_meta.json")
    # predict.py prefers a voxel size the checkpoint records; training's do not,
    # so without this every export was scaled at its 7.91 um default, and the
    # evidence chain then compared that with the candidate's voxel_um.
    voxel = []
    if row.get("voxel_um") not in (None, ""):
        try:
            voxel_um = float(row["voxel_um"])
        except (TypeError, ValueError) as exc:
            raise ValueError("candidate voxel_um must be a number") from exc
        if not math.isfinite(voxel_um) or voxel_um <= 0:
            raise ValueError("candidate voxel_um must be positive and finite")
        voxel = ["--voxel_size_um", str(voxel_um)]
    return [
        os.fspath(python_executable),
        str(PREDICT_SCRIPT),
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
        str(patch),
        "--output_img",
        output_img,
        "--metadata_out",
        metadata_out,
        "--artifact_stem",
        stem,
        "--checkpoint",
        os.fspath(checkpoint),
        *voxel,
        "--skip_active_learning",
    ]


def read_candidate_table(path, expected_sha256=None):
    source = Snapshot.read(path, MAX_CANDIDATE_BYTES)
    if expected_sha256 is not None and source.provenance()["sha256"] != expected_sha256:
        raise ValueError("ranked candidate table changed; regenerate the worklist")
    try:
        return source, parse_candidate_table(source.text())
    except csv.Error as exc:
        raise ValueError(f"invalid candidate TSV: {exc}") from exc


def resolve_candidate_paths(row, base_dir):
    """Resolve recorded filesystem paths once; leave remote source URIs intact."""
    row = dict(row)
    base = Path(base_dir).resolve()
    for key in ("local_uri", "source_uri", "train_mask_path", "predict_mask_path"):
        value = row.get(key)
        if not value:
            continue
        parts = urlsplit(value)
        if (base / value).exists() or not parts.scheme:
            row[key] = str((base / value).resolve())
        elif parts.scheme == "file":
            if parts.netloc not in {"", "localhost"}:
                raise ValueError("file URI must refer to the local host")
            row[key] = str((base / unquote(parts.path)).resolve())
    return row


def parse_candidate_table(text):
    reader = csv.reader(io.StringIO(text, newline=""), delimiter="\t", strict=True)
    try:
        columns = next(reader)
    except StopIteration as exc:
        raise ValueError("candidate table is empty") from exc
    if (
        not columns
        or any(not column for column in columns)
        or len(set(columns)) != len(columns)
    ):
        raise ValueError("candidate table has empty or duplicate column names")
    rows = []
    for cells in reader:
        if not cells:
            continue  # Match DictReader's treatment of genuinely blank lines.
        if len(rows) >= MAX_CANDIDATE_ROWS:
            raise ValueError(f"candidate table exceeds {MAX_CANDIDATE_ROWS} rows")
        if len(cells) != len(columns):
            raise ValueError(
                f"candidate table line {reader.line_num} has wrong column count"
            )
        rows.append(dict(zip(columns, cells, strict=True)))
    return rows


def load_candidates(path, limit=None, require_local=True):
    if limit is not None and (type(limit) is not int or limit <= 0):
        raise ValueError("limit must be a positive integer")
    _, rows = read_candidate_table(path)
    if require_local:
        rows = [row for row in rows if row.get("local_uri")]
    if limit is not None:
        rows = rows[:limit]
    return rows


def plan_inference(
    rows,
    ranked_path,
    manifest,
    prediction_dir="predictions",
    checkpoint="best_model.pt",
):
    commands = []
    writes = [(Path(manifest), "command manifest")]
    reads = [(Path(ranked_path), "ranked input"), (Path(checkpoint), "checkpoint")]
    reads.append(
        (Path(__file__).resolve().parents[2] / "autoresearch.lock", "research lock")
    )
    for index, row in enumerate(rows, 1):
        command = build_predict_command(
            row, prediction_dir=prediction_dir, checkpoint=checkpoint
        )
        commands.append(command)
        stem = command[command.index("--artifact_stem") + 1]
        owner = f"candidate {index} ({stem})"
        writes.extend((path, owner) for path in prediction_paths(prediction_dir, stem))
        uri = row.get("local_uri") or row.get("source_uri")
        if uri and "://" not in uri:
            reads.append((Path(uri), f"{owner} source volume"))
    validate_plan_paths(writes, reads)
    return commands


def write_manifest(commands, out_path):
    encoded = "".join(shlex.join(command) + "\n" for command in commands)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=out_path.parent, prefix=f".{out_path.name}.", delete=False
        ) as f:
            staged = Path(f.name)
            f.write(encoded)
        os.chmod(staged, replacement_mode(out_path))
        os.replace(staged, out_path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranked", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--prediction-dir", default="predictions")
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument("--manifest", default="reports/scroll23_inference_commands.sh")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run commands serially; default only writes/prints commands",
    )
    parser.add_argument("--allow-missing-local-uri", action="store_true")
    args = parser.parse_args(argv)
    try:
        rows = load_candidates(
            args.ranked,
            limit=args.limit,
            require_local=not args.allow_missing_local_uri,
        )
        if not rows:
            raise ValueError(
                "no eligible candidates; check the ranked table and local_uri fields (use --allow-missing-local-uri to plan remote sources)"
            )
        commands = plan_inference(
            rows, args.ranked, args.manifest, args.prediction_dir, args.checkpoint
        )
        write_manifest(commands, args.manifest)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print(f"Wrote {len(commands)} inference commands to {args.manifest}")
    for cmd in commands:
        print(shlex.join(cmd))

    if args.execute:
        for cmd in commands:
            subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
