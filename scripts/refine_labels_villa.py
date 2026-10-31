#!/usr/bin/env python3
"""Compatibility entry point for 2D label proposals; bulk EDT/Frangi edits retired.

The former pipeline operated on labels rather than CT and could change preferred
training targets in place. Its outputs were never established as better labels.
Use --input PNG --out NEW_DIRECTORY for an explicit bounded proposal instead.
The historical prototype remains available in Git history before this change.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_ROOT), str(REPO_ROOT / "src")]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    legacy = (
        "--in_place",
        "--in-place",
        "--labels_dir",
        "--labels-dir",
        "--output_dir",
        "--output-dir",
        "--sigma_frangi",
        "--edt_threshold",
        "--ridge_threshold",
        "--min_component_size",
        "--num_workers",
        "--dry_run",
    )
    if any(argument.split("=", 1)[0] in legacy for argument in argv):
        print(
            "Bulk/in-place EDT + Frangi label refinement is retired. "
            "Use --input binary.png --out NEW_REVIEW_DIRECTORY for a bounded 2D proposal. "
            "3D label editing requires a separately reviewed workflow. "
            "See docs/LABEL_EDIT_PROPOSALS.md.",
            file=sys.stderr,
        )
        return 2
    from scripts.preprocess_labels import main as proposal_main

    return proposal_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
