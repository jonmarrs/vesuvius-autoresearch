#!/usr/bin/env python3
"""Compatibility entry point for the explicit region-mask pseudo-label producer.

The old URI/architecture-guessing interface is retired. Use --help for the
checkpoint, fragment, region mask, and new output arguments.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_pseudo_labels import main

if __name__ == "__main__":
    main()
