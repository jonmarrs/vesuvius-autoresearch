"""Run the launchers locally with tiny stand-ins; no Docker or GPU work."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "repro/spiral_render"


def executable(path, text):
    path.write_text("#!/bin/bash\nset -eu\n" + text)
    path.chmod(0o755)


def fixture(tmp_path):
    repo = tmp_path / "repo"
    scripts = repo / "repro/spiral_render"
    scripts.mkdir(parents=True)
    for name in (
        "run_interp_windows.sh",
        "smoke_surface_interpolation.sh",
        "artifacts.py",
    ):
        shutil.copy(SCRIPTS / name, scripts)
    (repo / "scripts").mkdir()
    for name in ("analyse_interp_windows.py", "interpolation_inputs.py"):
        shutil.copy(SCRIPTS.parents[1] / "scripts" / name, repo / "scripts")
    executable(scripts / "score_arms.sh", 'echo "$(dirname "$0")" >> "$SO/scores"\n')
    root = tmp_path / "data"
    flat = root / "detfit_up1/meshes/concat/w120-129_flat"
    flat.mkdir(parents=True)
    for axis in "xyz":
        (flat / f"{axis}.tif").write_text("surface")
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    executable(
        fakebin / "md5sum",
        """cat >/dev/null
if [ -f "$SO/changed" ]; then echo bad; else echo bfd9ef809c27930d553b778adc209dd9; fi
""",
    )
    executable(
        fakebin / "python",
        """case "$2" in
select)
  printf '%s\\n' 32768 40000 47000 54000 61000 68000 75000 82000
  exit "${SELECT_RC:-0}" ;;
strip) exit 0 ;;
esac
""",
    )
    executable(
        fakebin / "docker",
        """case "$*" in
*/opt/vcsrc/SAMPLER_SHA*)
  if [ "${BAD_SHA:-0}" = 1 ]; then echo bad; exit 0; fi
  case "$*" in
    *75c79ac5f*) echo 75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3 ;;
    *) echo f637f3b35208bafa7812b4d97fea45bf43d19edb ;;
  esac
  exit 0 ;;
esac
echo rendered >> "$SO/renders"
case "$*" in *'--surface-interpolation smooth'*) echo 'Surface interpolation: smooth' ;; esac
if [ "${CHANGE_FLAT:-0}" = 1 ]; then touch "$SO/changed"; fi
if [ "${CHANGE_SCORER:-0}" = 1 ]; then echo 'exit 9' > "$REPO/repro/spiral_render/score_arms.sh"; fi
while [ "$#" -gt 0 ]; do
  if [ "$1" = --tif-output ]; then
    for index in 00 01 02 03 04; do
      if [ "${MISSING_SLICE:-0}" != 1 ] || [ "$index" != 04 ]; then touch "$2/$index.tif"; fi
    done
    break
  fi
  shift
done
""",
    )
    env = {
        **os.environ,
        "SO": str(root),
        "REPO": str(repo),
        "PY": str(fakebin / "python"),
        "PATH": f"{fakebin}:{os.environ['PATH']}",
    }
    return scripts, root, env


def run(script, env):
    return subprocess.run(
        ["bash", str(script)], env=env, capture_output=True, text=True, timeout=20
    )


def test_failed_selector_cannot_start_a_study_even_after_printing_eight_rows(tmp_path):
    scripts, root, env = fixture(tmp_path)
    result = run(scripts / "run_interp_windows.sh", {**env, "SELECT_RC": "7"})
    assert result.returncode != 0
    assert "selection failed" in result.stdout
    assert not (root / "renders").exists()


def test_changed_flat_stops_before_rendering_the_paired_arm(tmp_path):
    scripts, root, env = fixture(tmp_path)
    result = run(scripts / "run_interp_windows.sh", {**env, "CHANGE_FLAT": "1"})
    assert result.returncode != 0
    assert (root / "renders").read_text().splitlines() == ["rendered"]
    assert "flat md5" in result.stdout


def test_direct_launch_freezes_all_helpers(tmp_path):
    scripts, root, env = fixture(tmp_path)
    result = run(scripts / "run_interp_windows.sh", {**env, "CHANGE_SCORER": "1"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "renders").read_text().splitlines() == ["rendered"] * 16
    assert (root / "scores").read_text().splitlines() == [
        str(root / "interp_windows")
    ] * 16
    assert (root / "interp_windows/interpolation_inputs.py").exists()
    python = Path(__file__).resolve().parents[1] / ".venv/bin/python"
    probe = subprocess.run(
        [str(python), str(root / "interp_windows/analyse_interp_windows.py"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert probe.returncode == 0, probe.stderr


@pytest.mark.parametrize(
    "failure,message", [("BAD_SHA", "image sha"), ("MISSING_SLICE", "MISSING_SLICE")]
)
def test_smoke_rejects_wrong_sampler_or_missing_output(tmp_path, failure, message):
    scripts, _, env = fixture(tmp_path)
    result = run(scripts / "smoke_surface_interpolation.sh", {**env, failure: "1"})
    assert result.returncode != 0
    assert message in result.stdout


def test_complete_smoke_finishes_with_three_arms(tmp_path):
    scripts, root, env = fixture(tmp_path)
    result = run(scripts / "smoke_surface_interpolation.sh", env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "renders").read_text().splitlines() == ["rendered"] * 3
    assert "SMOKE_DONE" in result.stdout
