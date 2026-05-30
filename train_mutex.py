"""Back-compat shim for the prior train_mutex.py stub.

Forwards to scripts/launch_mutex.py, which is the maintained launcher that
delegates to villa's MutexAffinityTrainer via the official CLI. The original
stub instantiated the trainer but never actually trained; we keep this entry
so existing instructions (e.g. prepare_mutex_training.py's usage hint) still
work, but the implementation now matches the launch_uamt / launch_lejepa
pattern.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAUNCHER = HERE / "scripts" / "launch_mutex.py"


def main() -> int:
    if not LAUNCHER.exists():
        print(f"ERROR: launcher not found at {LAUNCHER}", file=sys.stderr)
        return 1

    argv = sys.argv[1:]
    if argv and argv[0] == "--data_path":
        argv = ["--data-path", *argv[1:]]

    os.execv(sys.executable, [sys.executable, str(LAUNCHER), *argv])


if __name__ == "__main__":
    sys.exit(main())
