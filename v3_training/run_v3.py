"""Retired v3 entry point; retained to explain the supported training path."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v3_training.retirement import main

if __name__ == "__main__":
    raise SystemExit(main())
