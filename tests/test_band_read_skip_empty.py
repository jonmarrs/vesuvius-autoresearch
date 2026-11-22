"""The band read's STUDIO_SKIP_EMPTY: Studio through studio_fast.py --skip-empty (finding 132), otherwise the winner's
inference.py. The studio step is run with stand-in pythons that record their command lines."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "repro/first_letters/eligible_band/run_studio_band.sh"


def _block(text: str, head: str, end: str) -> str:
    start = text.index(head)
    return text[start : text.index(end, start) + len(end)]


def _studio_argv(tmp_path, skip, tiling="winner"):
    text = SCRIPT.read_text()
    tiling_case = _block(text, 'case "${STUDIO_TILING:-winner}" in', "esac")
    runner_case = _block(text, 'case "${STUDIO_SKIP_EMPTY:-0}" in', "esac")
    studio = _block(text, "studio() {", "\n}\n")
    stub = tmp_path / "python"
    stub.write_text('#!/bin/bash\nprintf "%s\\n" "$PWD" "$@" > "$ARGV_OUT"\n')
    stub.chmod(0o755)
    (tmp_path / "code").mkdir(exist_ok=True)
    script = f"""
ROOT=/repo; CODE="{tmp_path}/code"; ENV="{tmp_path}/env"; mkdir -p "$ENV/bin"; cp "{stub}" "$ENV/bin/python"
PYW=/bin/true; WEIGHTS=/w.safetensors; R="{tmp_path}"; ARM=a; SLICES=18; OUT="{tmp_path}/out"
export ARGV_OUT="{tmp_path}/argv"
STUDIO_TILING="{tiling}"; STUDIO_SKIP_EMPTY="{skip}"; [ -z "$STUDIO_SKIP_EMPTY" ] && unset STUDIO_SKIP_EMPTY
{tiling_case}
{runner_case}
{studio}
studio w010
"""
    run = subprocess.run(["bash", "-uc", script], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    lines = (tmp_path / "argv").read_text().split("\n")[:-1]
    return lines[0], lines[1:]


def test_by_default_the_read_runs_the_winners_inference_py_as_before(tmp_path):
    for skip in ("", "0"):
        cwd, argv = _studio_argv(tmp_path, skip)
        assert cwd == str(tmp_path / "code")
        assert argv == ["inference.py", "--input", f"{tmp_path}/out/planes/w010.npy", "--output",
                        f"{tmp_path}/out/maps/w010.npy", "--checkpoint", "/w.safetensors", "--stride", "64",
                        "--blend", "hann", "--batch-size", "32"]  # fmt: skip


def test_the_skip_runs_studio_fast_with_the_winners_file_command_and_batch_size(
    tmp_path,
):
    cwd, argv = _studio_argv(tmp_path, "1")
    assert cwd == str(tmp_path / "code")
    assert argv == ["-I", "/repo/repro/first_letters/pherc0211_control/studio_fast.py", "run", "--code",
                    str(tmp_path / "code"), "--skip-empty", "--input", f"{tmp_path}/out/planes/w010.npy", "--output",
                    f"{tmp_path}/out/maps/w010.npy", "--checkpoint", "/w.safetensors", "--stride", "64", "--blend",
                    "hann", "--batch-size", "32"]  # fmt: skip


def test_the_published_tiling_passes_through_either_runner(tmp_path):
    _, plain = _studio_argv(tmp_path, "0", tiling="published")
    _, skip = _studio_argv(tmp_path, "1", tiling="published")
    assert "--stride" not in plain and "--stride" not in skip
    assert plain[-2:] == skip[-2:] == ["--batch-size", "32"]


def test_a_bad_value_stops_the_read_before_anything_runs():
    block = _block(SCRIPT.read_text(), 'case "${STUDIO_SKIP_EMPTY:-0}" in', "esac")
    for value, code in (("0", 0), ("1", 0), ("2", 2), ("yes", 2)):
        run = subprocess.run(["bash", "-uc", f'ROOT=/r; CODE=/c; STUDIO_SKIP_EMPTY="{value}"\n{block}'],
                             capture_output=True, text=True)  # fmt: skip
        assert run.returncode == code, value


def test_studio_fast_takes_the_same_defaults_as_the_winners_file():
    """With the published tiling neither runner gets --stride or --blend, so their defaults must agree."""
    text = (ROOT / "repro/first_letters/pherc0211_control/studio_fast.py").read_text()
    assert 'r.add_argument("--stride", type=int, default=96)' in text
    assert 'r.add_argument("--blend", default="none", choices=["none", "hann"])' in text
    assert '"cuda", args.batch_size, "bf16", args.stride, args.blend' in text
    start = SCRIPT.read_text().index("READ_START")
    assert (
        "skip_empty=${STUDIO_SKIP_EMPTY:-0}" in SCRIPT.read_text()[start : start + 200]
    )
