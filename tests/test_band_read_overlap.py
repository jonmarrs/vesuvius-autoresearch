"""The band read's FL_OVERLAP=1: the renders in the background while Studio reads each rendered winding. Run on
stand-ins for render_one, studio and gate, which log when each starts and ends."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "repro/first_letters/eligible_band/run_studio_band.sh"


def _block(text: str, head: str) -> str:
    start = text.index(head)
    return text[start : text.index("\n}\n", start) + 3]


def _read(tmp_path, render_fails=(), studio_fails=(), renderer_dies_at=None):
    """Runs render_and_read on four windings; returns (stdout, gates, events, LIVE after)."""
    fn = _block(SCRIPT.read_text(), "render_and_read() {")
    die = (
        f'[ "$1" = {renderer_dies_at} ] && kill -9 "$BASHPID"'
        if renderer_dies_at
        else ":"
    )
    script = f"""
R="{tmp_path}"; ARM=a; OUT="{tmp_path}/out"; mkdir -p "$OUT" "$R/logs"
LIVE=(w1 w2 w3 w4)
FL_OVERLAP_POLL=0.02
EV="{tmp_path}/events"
gate() {{ echo "$2 $3" >> "{tmp_path}/gates"; }}
render_one() {{
  {die}
  echo "render_start $1" >> "$EV"; sleep 0.3
  case " {" ".join(render_fails)} " in *" $1 "*) echo "render_end $1" >> "$EV"; return 3 ;; esac
  touch "$R/rendered_$1"; echo "render_end $1" >> "$EV"
}}
studio() {{
  [ -e "$R/rendered_$1" ] || return 9  # Studio never reads a winding before its render is done
  echo "studio_start $1" >> "$EV"; sleep 0.1
  case " {" ".join(studio_fails)} " in *" $1 "*) return 4 ;; esac
  echo "studio_end $1" >> "$EV"
}}
{fn}
render_and_read
echo "LIVE=${{LIVE[*]}}"
"""
    run = subprocess.run(
        ["bash", "-uc", script], capture_output=True, text=True, timeout=60
    )
    assert run.returncode == 0, run.stderr
    gates = (
        (tmp_path / "gates").read_text().split("\n")
        if (tmp_path / "gates").exists()
        else []
    )
    events = (tmp_path / "events").read_text().split("\n")
    live = run.stdout.strip().split("\n")[-1].removeprefix("LIVE=").split()
    return run.stdout, [g for g in gates if g], [e for e in events if e], live


def test_studio_reads_while_the_renders_go_on_and_only_what_was_rendered(tmp_path):
    out, gates, events, live = _read(tmp_path, render_fails=("w2",))
    assert sorted(gates) == sorted(
        ["studio_render_w1 0", "studio_render_w2 3", "studio_render_w3 0", "studio_render_w4 0",
         "studio_studio_w1 0", "studio_studio_w3 0", "studio_studio_w4 0"]
    )  # fmt: skip
    assert live == ["w1", "w3", "w4"]
    assert "FAILED render w2" in out
    assert "render: 3 windings go on" in out and "studio: 3 windings go on" in out
    # the overlap: Studio read w1 before the last render ended
    assert events.index("studio_start w1") < events.index("render_end w4")
    # the renders keep their order, and Studio reads in the same order
    assert [e.split()[1] for e in events if e.startswith("render_start")] == [
        "w1",
        "w2",
        "w3",
        "w4",
    ]
    assert [e.split()[1] for e in events if e.startswith("studio_start")] == [
        "w1",
        "w3",
        "w4",
    ]
    for w in ("w1", "w3", "w4"):
        assert events.index(f"render_end {w}") < events.index(f"studio_start {w}")


def test_a_failed_read_is_recorded_and_dropped_as_in_the_serial_read(tmp_path):
    out, gates, _, live = _read(tmp_path, studio_fails=("w3",))
    assert "studio_studio_w3 4" in gates and "FAILED studio w3" in out
    assert live == ["w1", "w2", "w4"]
    assert "studio: 3 windings go on" in out and "render: 4 windings go on" in out


def test_windings_left_unrendered_when_the_renderer_stops_are_not_read(tmp_path):
    out, gates, _, live = _read(tmp_path, renderer_dies_at="w3")
    assert live == ["w1", "w2"]
    assert "FAILED render w3 (the renderer stopped first)" in out
    assert "FAILED render w4 (the renderer stopped first)" in out
    assert not any(
        g.startswith(("studio_studio_w3", "studio_studio_w4")) for g in gates
    )


def test_overlap_is_off_unless_asked_and_a_bad_value_stops_the_read(tmp_path):
    text = SCRIPT.read_text()
    block = text[
        text.index('case "${FL_OVERLAP:-0}" in') : text.index(
            "esac", text.index('case "${FL_OVERLAP:-0}" in')
        )
        + 4
    ]
    for value, code in (("", 0), ("0", 0), ("1", 0), ("2", 2), ("yes", 2)):
        run = subprocess.run(["bash", "-uc", f'FL_OVERLAP="{value}"; [ -z "$FL_OVERLAP" ] && unset FL_OVERLAP\n{block}'],
                             capture_output=True, text=True)  # fmt: skip
        assert run.returncode == code, (value, run.stderr)
    tail = text[text.index('if [ "${FL_OVERLAP:-0}" = 1 ]; then') :]
    assert (
        tail.index("render_and_read")
        < tail.index("for_each render render_one")
        < tail.index("for_each studio studio")
    )
    # the serial read is the same two lines as before
    assert "else\n  for_each render render_one\n  for_each studio studio\nfi" in tail


def test_both_reads_log_and_gate_each_winding_under_the_same_names():
    text = SCRIPT.read_text()
    serial = _block(text, "for_each() {")
    overlap = _block(text, "render_and_read() {")
    assert (
        '"$R/logs/studio_${ARM}_${step}_$w.log"' in serial
        and 'gate "$ARM" "studio_${step}_$w"' in serial
    )
    for step in ("render", "studio"):
        assert f'"$R/logs/studio_${{ARM}}_{step}_$w.log"' in overlap
        assert f'gate "$ARM" "studio_{step}_$w"' in overlap
    assert 'echo "$step: ${#LIVE[@]} windings go on $(date -Is)"' in serial
    assert "windings go on $(date -Is)" in overlap


# --- the done list starts empty, a winding is matched by its whole name, the last look, and the wait for the renderer


def _overlap(tmp_path, live=("w1", "w2", "w3", "w4"), before=""):
    """render_and_read with the same stand-ins as _read, on the windings `live`, after the shell lines `before`."""
    fn = _block(SCRIPT.read_text(), "render_and_read() {")
    script = f"""
R="{tmp_path}"; ARM=a; OUT="{tmp_path}/out"; mkdir -p "$OUT" "$R/logs"
LIVE=({" ".join(live)})
FL_OVERLAP_POLL=0.02
gate() {{ echo "$2 $3" >> "{tmp_path}/gates"; }}
render_one() {{ sleep 0.2; touch "$R/rendered_$1"; }}
studio() {{ [ -e "$R/rendered_$1" ] || return 9; }}
{before}
{fn}
render_and_read
echo "LIVE=${{LIVE[*]}}"
"""
    run = subprocess.run(
        ["bash", "-uc", script], capture_output=True, text=True, timeout=60
    )
    assert run.returncode == 0, run.stderr
    return run.stdout, run.stdout.strip().split("\n")[-1].removeprefix("LIVE=").split()


def test_a_done_list_left_from_before_is_emptied_first(tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "rendered.txt").write_text(
        "w1 0\n"
    )  # as if w1 were already rendered
    assert _overlap(tmp_path)[1] == ["w1", "w2", "w3", "w4"]


def test_a_winding_waits_for_its_own_name_not_one_it_begins(tmp_path):
    # w10 is rendered first; w1 must wait for its own line, not take w10's
    assert _overlap(tmp_path, live=("w10", "w1"))[1] == ["w10", "w1"]


def test_a_render_recorded_as_the_renderer_stops_is_still_read(tmp_path):
    # the reader's check of the renderer waits until the renderer has rendered everything and gone, so only the last
    # look at the done list can find w1
    before = """kill() {
  if [ "$1" = -0 ]; then while command kill -0 "$2" 2>/dev/null; do command sleep 0.01; done; return 1; fi
  command kill "$@"
}"""
    assert _overlap(tmp_path, before=before)[1] == ["w1", "w2", "w3", "w4"]


def test_the_read_waits_for_the_renderer_to_finish(tmp_path):
    # the renderer's count of what it rendered is slowed: it must still come before the read's own last line
    before = """awk() { if [ "$1" = '$2 == 0' ]; then command sleep 0.5; fi; command awk "$@"; }"""
    out, live = _overlap(tmp_path, before=before)
    assert out.index("render: 4 windings go on") < out.index("studio: 4 windings go on")
    assert live == ["w1", "w2", "w3", "w4"]
