"""Back-compat shim for the prior train_mutex.py stub.

Forwards to scripts/training/launch_mutex.py, the maintained launcher that
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
LAUNCHER = HERE / "scripts" / "training" / "launch_mutex.py"


def main() -> int:
    if not LAUNCHER.exists():
        print(f"ERROR: launcher not found at {LAUNCHER}", file=sys.stderr)
        return 1

    argv = sys.argv[1:]
    argv = [
        arg.replace("--data_path", "--data-path", 1)
        if arg == "--data_path" or arg.startswith("--data_path=")
        else arg
        for arg in argv
    ]

    os.execv(sys.executable, [sys.executable, str(LAUNCHER), *argv])


if __name__ == "__main__":
    sys.exit(main())
