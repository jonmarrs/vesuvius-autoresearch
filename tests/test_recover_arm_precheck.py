"""Guards on the recovery script's precheck.

Two defects this encodes, both found by reading rather than by a failed recovery:

1. **VILLA was never set.** `setup_workdir.sh` defaults it to `.../Neo-VM/villa-spiral`,
   but the consensus chain exported the SUBMODULE, and they are not interchangeable
   -- `villa-spiral` does not contain `be09a8503` at all. Unset, a recovery passed
   the precheck and then died ~30s later inside setup_workdir with "unknown
   revision": loud, but only after the operator believed it had started.
2. **An unpinned VILLA_REF was silent.** Following a moving ref is how the corpus
   got split across two render trees in the first place.

The ref check runs BEFORE the capacity check, so these are deterministic on any
machine regardless of free memory or what happens to be running.
"""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "repro" / "spiral_render" / "recover_arm.sh"
ARGS = ["/tmp/nonexistent_spiral_out", "120", "129", "curbase_s7"]


def _run(env_extra: dict) -> subprocess.CompletedProcess:
    import os

    env = dict(os.environ)
    env.pop("VILLA", None)
    env.pop("VILLA_REF", None)
    env.update(env_extra)
    return subprocess.run(
        [str(SCRIPT), *ARGS], capture_output=True, text=True, env=env, timeout=120
    )


def test_script_exists_and_is_executable():
    assert SCRIPT.exists() and SCRIPT.stat().st_mode & 0o111


def test_refuses_a_ref_absent_from_the_chosen_checkout():
    """The regression: villa-spiral lacks be09a8503, so recovery would die late."""
    r = _run(
        {
            "VILLA": "/home/jon/openclaw-workspace/Neo-VM/villa-spiral",
            "VILLA_REF": "be09a8503",
        }
    )
    assert r.returncode == 1
    assert "does not resolve in" in r.stderr
    assert "not a substitute" in r.stderr


def test_warns_when_the_ref_is_unpinned():
    """A moving ref is what split the corpus across two render trees."""
    r = _run({})
    assert "MOVING ref" in r.stderr
    assert "not comparable" in r.stderr


def test_accepts_the_ref_in_the_checkout_that_has_it():
    """Must get PAST the ref check; it may still stop on capacity, which is fine."""
    r = _run({"VILLA_REF": "be09a8503"})
    out = r.stdout + r.stderr
    assert "does not resolve in" not in out
    assert "resolves in" in out


def test_defaults_villa_to_the_submodule_not_villa_spiral():
    src = SCRIPT.read_text()
    assert 'VILLA="${VILLA:-$REPO/villa}"' in src
    assert "export VILLA" in src
