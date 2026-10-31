#!/usr/bin/env python3
"""Check detector report checksums without importing ML or image libraries."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vesuvius_autoresearch.core.report_artifacts import check_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "marker", type=Path, help="fragment scorecard or measurement manifest JSON"
    )
    args = parser.parse_args(argv)
    try:
        record = check_report(args.marker)
        result = {
            "integrity_verified": True,
            "report_status": record["report_status"],
            "report_kind": record["report_kind"],
            "created_at_utc": record["created_at_utc"],
            "artifacts": list(record["artifacts"]),
        }
        if record["report_kind"] == "cross_scroll_measurement":
            result.update(
                {
                    key: record[key]
                    for key in ("target_count", "success_count", "failure_count")
                }
            )
        print(json.dumps(result, indent=2))
        return int(record["report_status"] != "COMPLETE")
    except (OSError, ValueError) as exc:
        print(f"Report check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
