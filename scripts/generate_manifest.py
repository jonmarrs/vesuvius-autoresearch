#!/usr/bin/env python3
"""Publish a bounded metadata inventory without inferring training readiness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.data_catalogue import (
    MAX_DEPTH,
    MAX_ENTRIES,
    artifact_record,
    bounded_integer,
    default_output,
    fingerprint,
    inventory_snapshot,
    local_root,
    markdown_name,
    write_verified_json,
)
from scripts.labeling.label_artifacts import new_output, publish_new


def get_dir_size(path, *, max_entries=MAX_ENTRIES, max_depth=MAX_DEPTH):
    """Sum apparent bytes of regular files, excluding symlink targets."""
    snapshot = inventory_snapshot(path, max_entries, max_depth)
    return sum(
        entry["bytes"]
        for entry in snapshot["entries"]
        if entry["kind"] == "regular_file"
    )


def summarize(entries):
    return {
        "entries": len(entries),
        "regular_files": sum(entry["kind"] == "regular_file" for entry in entries),
        "apparent_bytes": sum(
            entry["bytes"] for entry in entries if entry["kind"] == "regular_file"
        ),
        "directories": sum(entry["kind"] == "directory" for entry in entries),
        "symlinks_not_followed": sum(
            entry["kind"] == "symlink_not_followed" for entry in entries
        ),
        "special_files_not_read": sum(
            entry["kind"] == "special_file_not_read" for entry in entries
        ),
    }


def inventory_markdown(report):
    lines = [
        "# Local data metadata inventory",
        "",
        f"Root: {markdown_name(report['source']['root'])}",
        "",
        "Scope: observed path metadata only. File content, dataset identity, CT/label",
        "alignment, ground truth, training readiness and coverage are not assessed.",
        "Apparent bytes are logical file sizes, not allocated disk space. Hardlinks",
        "count once per pathname. Symlink targets and special-file contents are not read.",
        "",
        f"Observed regular files: {report['totals']['regular_files']}; "
        f"apparent bytes: {report['totals']['apparent_bytes']}.",
        "",
        "| Top-level entry | Regular files | Apparent bytes | Ignored links | Special files |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["top_level"]:
        lines.append(
            f"| {markdown_name(row['name'])} | {row['regular_files']} | "
            f"{row['apparent_bytes']} | {row['symlinks_not_followed']} | "
            f"{row['special_files_not_read']} |"
        )
    lines.extend(
        [
            "",
            f"Metadata SHA-256: {report['metadata_sha256']}",
            "",
            "The JSON contains the complete bounded listing and scan limits. This fingerprint",
            "identifies listing/stat metadata; it is not a content digest or an eligibility check.",
            "",
        ]
    )
    return "\n".join(lines)


def generate(
    root="local_data", output=None, *, max_entries=MAX_ENTRIES, max_depth=MAX_DEPTH
):
    max_entries = bounded_integer(max_entries, "max_entries", MAX_ENTRIES)
    max_depth = bounded_integer(max_depth, "max_depth", MAX_DEPTH)
    root = local_root(root)
    output = new_output(
        output if output is not None else default_output("data_inventory"), root
    )
    snapshot = inventory_snapshot(root, max_entries, max_depth)
    grouped = {}
    for entry in snapshot["entries"]:
        grouped.setdefault(entry["path"].split("/", 1)[0], []).append(entry)
    report = {
        "contract": 1,
        "scope": "local path metadata inventory; training readiness not assessed",
        "content_hashed": False,
        "source": snapshot,
        "metadata_sha256": fingerprint(snapshot),
        "limits": {"max_entries": int(max_entries), "max_depth": int(max_depth)},
        "totals": summarize(snapshot["entries"]),
        "top_level": [
            {"name": name, **summarize(entries)}
            for name, entries in sorted(grouped.items())
        ],
    }
    markdown = inventory_markdown(report)
    with publish_new(output) as staging:
        document = staging / "inventory.md"
        document.write_text(markdown, encoding="utf-8")
        if document.read_text(encoding="utf-8") != markdown:
            raise ValueError("inventory Markdown verification failed")
        report["artifacts"] = {"inventory.md": artifact_record(document)}
        write_verified_json(staging / "inventory.json", report)
        if inventory_snapshot(root, max_entries, max_depth) != snapshot:
            raise ValueError("inventory source changed before publication")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("local_data"))
    parser.add_argument("--out", type=Path, help="new, separate output directory")
    parser.add_argument("--max-entries", type=int, default=MAX_ENTRIES)
    parser.add_argument("--max-depth", type=int, default=MAX_DEPTH)
    args = parser.parse_args(argv)
    try:
        output = generate(
            args.root, args.out, max_entries=args.max_entries, max_depth=args.max_depth
        )
    except (OSError, ValueError) as exc:
        print(f"Inventory failed: {exc}", file=sys.stderr)
        return 1
    print(f"Metadata inventory saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
