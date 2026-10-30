"""Every GPU chain that checks for the autoresearch loop starts only when `loop_control.py status` says
nothing runs.

status exits 0 for a running loop, 1 for none, and 2 when it cannot tell, as when the lock is held
without a valid PID. start.sh and scripts/loop_watchdog.sh start only on 1. The fiber chains aborted
only on 0, so a 2, or an interpreter that is not there (127), let a GPU study start beside the loop.
The tracing-context and CT-context chains (#206, #209) copied the guard from the pitch and seeding
chains.

Each chain runs here against a stub checkout whose interpreter answers status with a chosen code. A
chain that passes the guard stops at the next step, freezing scripts the stub checkout does not have.
"""

import os
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
CHAINS = sorted(
    p
    for p in (_REPO / "repro").rglob("*.sh")
    if 'loop_control.py" status' in p.read_text()
)
RUNNING = "SC_ABORTED the autoresearch loop is running"
UNKNOWN = "SC_ABORTED loop_control.py status cannot tell"


def test_the_guarded_chains_are_found():
    assert {
        "run_neural_tracer_pitch_chain.sh",
        "run_neural_tracer_seeding_chain.sh",
        "run_tracing_context_chain.sh",
        "run_neural_tracer_ct_context_chain.sh",
    } <= {p.name for p in CHAINS}


def _run(chain: Path, tmp_path: Path, rc: int) -> tuple[int, str]:
    repo = tmp_path / "repo"
    py = repo / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text(
        '#!/bin/sh\ncase "$1" in *loop_control.py) exit "$STATUS_RC" ;; esac\nexit 1\n'
    )
    py.chmod(0o755)
    # The seed-heading re-run refuses a missing status helper before its loop guard.
    helper = repo / "scripts" / "seed_heading_chain_status.py"
    helper.parent.mkdir()
    helper.touch()
    w = tmp_path / "w"
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "STATUS_RC": str(rc),
        "REPO": str(repo),
        "LOOPDIR": str(repo),
        "T": str(tmp_path / "t"),
        "W": str(w),
        "G": str(tmp_path / "g"),
        "HELDOUT": str(tmp_path / "heldout"),
    }
    proc = subprocess.run(
        ["bash", str(chain)], env=env, capture_output=True, text=True, timeout=120
    )
    log = w / "chain.log"
    return proc.returncode, log.read_text() if log.exists() else ""


@pytest.mark.parametrize("chain", CHAINS, ids=lambda p: p.name)
@pytest.mark.parametrize(
    "rc,refusal", [(0, RUNNING), (2, UNKNOWN), (127, UNKNOWN), (1, None)]
)
def test_a_chain_starts_only_when_nothing_runs(tmp_path, chain, rc, refusal):
    code, log = _run(chain, tmp_path, rc)
    if refusal is not None:
        assert code == 3 and refusal in log, log
        assert "CHAIN_START" not in log
    else:
        assert RUNNING not in log and UNKNOWN not in log, log
        # past the guard: the stub checkout has no scripts to freeze
        assert code == 3 and (
            "SC_ABORTED freeze" in log or "another GPU job is running" in log
        ), log
