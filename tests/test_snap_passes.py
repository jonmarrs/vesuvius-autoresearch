"""run_snap.sh's FL_SNAP_PASSES (finding 134): pass k snaps pass k - 1, the last pass writes snap_ARM, and with one pass
the snap is the one every earlier finding ran. The pass loop is run with a stand-in snap_pass."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "repro/first_letters/eligible_band/run_snap.sh"


def _loop(tmp_path, passes, fail_at=None):
    text = SNAP.read_text()
    case = text[
        text.index("PASSES=${FL_SNAP_PASSES:-1}") : text.index("\nsnap_pass() {")
    ]
    loop = text[
        text.index("rc=0\nIN=$MESHES") : text.index(
            "if [ $rc -eq 0 ]; then\n  while read -r w;"
        )
    ]
    fail = f'[ "$2" = "$OUT{fail_at}" ] && return 1' if fail_at is not None else ":"
    script = f"""
R="{tmp_path}"; ARM=a; OUT="$R/work/snap_a"; MESHES="$R/fit"; MANIFEST="$R/work/snap_chunks_a.json"
mkdir -p "$R/work"
FL_SNAP_PASSES="{passes}"; [ -z "$FL_SNAP_PASSES" ] && unset FL_SNAP_PASSES
{case}
snap_pass() {{ echo "PASS $1 $2 $3"; {fail}; mkdir -p "$2"; }}
{loop}
echo "rc=$rc"
"""
    run = subprocess.run(["bash", "-uc", script], capture_output=True, text=True)
    return run.returncode, run.stdout.split("\n"), run.stderr


def test_one_pass_is_the_snap_of_every_earlier_finding(tmp_path):
    for passes in ("", "1"):
        code, out, _ = _loop(tmp_path / passes, passes)
        r = tmp_path / passes
        assert code == 0
        assert [o for o in out if o.startswith("PASS")] == [
            f"PASS {r}/fit {r}/work/snap_a {r}/work/snap_chunks_a.json"
        ]
        assert "rc=0" in out


def test_each_pass_snaps_the_one_before_and_the_last_writes_the_arms_snap(tmp_path):
    code, out, _ = _loop(tmp_path, "3")
    w = f"{tmp_path}/work"
    assert code == 0 and "rc=0" in out
    assert [o for o in out if o.startswith("PASS")] == [
        f"PASS {tmp_path}/fit {w}/snap_a.pass1 {w}/snap_chunks_a.json",
        f"PASS {w}/snap_a.pass1 {w}/snap_a.pass2 {w}/snap_chunks_a.pass2.json",
        f"PASS {w}/snap_a.pass2 {w}/snap_a {w}/snap_chunks_a.pass3.json",
    ]


def test_a_failed_pass_stops_the_snap(tmp_path):
    code, out, _ = _loop(tmp_path, "3", fail_at=".pass2")
    assert "rc=1" in out
    assert (
        len([o for o in out if o.startswith("PASS")]) == 2
    )  # the third pass never runs


def test_the_pass_count_is_one_to_five_and_a_pass_is_run_once(tmp_path):
    for value, code in (("0", 2), ("6", 2), ("x", 2), ("5", 0)):
        assert _loop(tmp_path / value, value)[0] == code, value
    (tmp_path / "again" / "work" / "snap_a.pass1").mkdir(parents=True)
    code, _, err = _loop(tmp_path / "again", "2")
    assert code == 2 and "exists" in err


def test_the_one_pass_commands_are_unchanged():
    """The pass runs the commands the snap ran before: the online chunk fetch, the offline check, then the batches."""
    text = SNAP.read_text()
    body = text[
        text.index("snap_pass() {") : text.index("\n}\n", text.index("snap_pass() {"))
    ]
    i = body.index(
        'snap_chunks.py" "$1" "$LIST" "$SURF" "$BUCKET_SURF/$SURF_NAME" "$3" || return 1'
    )
    j = body.index(
        'snap_chunks.py" "$1" "$LIST" "$SURF" "$BUCKET_SURF/$SURF_NAME" "$3" --offline || return 1'
    )
    k = body.index('split -l "${SNAP_BATCH:-12}"')
    m = body.index('snap_meshes.py" "$1" "$SCROLL" "$2"')
    assert i < j < k < m
    assert '--windings "$batch" --procs "${PROCS:-3}"' in body
