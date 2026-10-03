"""docs/preregistration/2026-10-03_coarse_grid_interpolation.md -- finding 72's analysis, unchanged, on the
coarse-grid work dir. Same subcommands as scripts/analyse_scorer_vs_labels.py.

Usage: .venv/bin/python scripts/analyse_scorer_vs_labels_coarse.py analyse [--out reports/scorer_vs_labels_coarse.json]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_scorer_vs_labels as base  # noqa: E402

base.WORK = Path(
    "/home/jon/openclaw-workspace/Neo-VM/spiral_out/gt_interp/scorer_study_coarse"
)

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "analyse" and "--out" not in sys.argv:
        sys.argv += ["--out", "reports/scorer_vs_labels_coarse.json"]
    sys.exit(base.main())
