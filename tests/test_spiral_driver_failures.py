"""Exercise shell entry points with tiny local stand-ins, without GPU/data access."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "repro/spiral_render"


def executable(path, body):
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)
    return path


def run(script, *args, cwd=None, **env):
    return subprocess.run(
        ["bash", str(script), *map(str, args)], cwd=cwd,
        env={**os.environ, **env}, capture_output=True, text=True, timeout=10,
    )


@pytest.mark.parametrize("kind", ["no_args", "missing_arm", "missing_strips"])
def test_score_rejects_missing_inputs(tmp_path, kind):
    arm = tmp_path / "arm"
    if kind == "missing_strips":
        arm.mkdir()
    args = [] if kind == "no_args" else [arm]
    result = run(SCRIPTS / "score_arms.sh", *args)
    assert result.returncode != 0, result.stdout


def test_score_uses_the_preflight_interpreter(tmp_path):
    arm = tmp_path / "arm"
    (arm / "meshes/ink").mkdir(parents=True)
    (arm / "meshes/ink/strip.jpg").touch()
    (arm / "spiral-fitting").mkdir()
    scorer = executable(tmp_path / "scorer", 'mkdir -p "$5"\necho \'{}\' > "$5/metrics.json"\n')
    result = run(SCRIPTS / "score_arms.sh", arm, cwd=tmp_path, SCORE_VENV=scorer.name, VENV="/bin/false")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (arm / "ink_metric/metrics.json").exists()


def test_render_resolves_relative_workdir_and_interpreter(tmp_path):
    arm = tmp_path / "arm"
    (arm / "spiral-fitting").mkdir(parents=True)
    probe = executable(tmp_path / "renderer", 'test "$3" = "$EXPECTED_MESHES"\n')
    result = run(
        SCRIPTS / "run_render.sh", "arm", cwd=tmp_path,
        RENDER_VENV=probe.name, VENV="/bin/false", EXPECTED_MESHES=str(arm / "meshes"),
    )
    assert result.returncode == 0, result.stdout + result.stderr


def outer_fixture(tmp_path, render_rc=0, score_rc=0):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(SCRIPTS / "run_outer_arms.sh", scripts)
    executable(scripts / "run_render.sh", f"exit {render_rc}\n")
    executable(scripts / "score_arms.sh", f'touch "$1/scorer_called"\nexit {score_rc}\n')
    root = tmp_path / "output"
    arm = root / "outer_test"
    (arm / "meshes/w120_spliced_test").mkdir(parents=True)
    (arm / "meshes/ink").mkdir()
    (arm / "meshes/ink/old.jpg").touch()
    return scripts / "run_outer_arms.sh", root, arm


def test_failed_render_never_scores_leftover_strips(tmp_path):
    driver, root, arm = outer_fixture(tmp_path, render_rc=3)
    result = run(driver, root, "120", "120", f"test={arm / 'meshes'}")
    assert not (arm / "scorer_called").exists(), "failed render consumed stale JPEGs"
    assert result.returncode != 0


def test_outer_driver_reports_scoring_failure(tmp_path):
    driver, root, arm = outer_fixture(tmp_path, score_rc=1)
    result = run(driver, root, "120", "120", f"test={arm / 'meshes'}")
    assert (arm / "scorer_called").exists()
    assert result.returncode != 0, result.stdout


def test_outer_driver_reports_missing_meshes(tmp_path):
    driver, root, _ = outer_fixture(tmp_path)
    result = run(driver, root, "120", "120", f"missing={tmp_path / 'absent'}")
    assert result.returncode != 0, result.stdout


def test_snapshot_preserves_default_villa_location(tmp_path):
    # A frozen driver is outside the repository: ../../villa no longer refers to
    # the checkout. The snapshot launcher must pass the original location through.
    source = tmp_path / "repo/repro/spiral_render"
    source.mkdir(parents=True)
    villa = tmp_path / "repo/villa"
    villa.mkdir()
    shutil.copy(SCRIPTS / "run_snapshot.sh", source)
    executable(source / "probe.sh", 'test "$VILLA" = "$EXPECTED_VILLA"\n')
    root = tmp_path / "snapshots"
    root.mkdir()
    result = run(source / "run_snapshot.sh", root, "probe.sh", VILLA="", EXPECTED_VILLA=str(villa))
    assert result.returncode == 0, result.stdout + result.stderr


def test_preflight_checks_pinned_tree_not_moving_main(tmp_path):
    villa = tmp_path / "villa"
    villa.mkdir()

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(villa), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()

    git("init")
    for name in ("spiral-fitting/get_ink_metrics.py", "lasagna/fit.py", "vesuvius/src/init.py"):
        path = villa / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# SERIAL_FOLDS\n")
    git("add", ".")
    git("commit", "-m", "working pin")
    pin = git("rev-parse", "HEAD")
    shutil.rmtree(villa / "lasagna")
    git("add", "-A")
    git("commit", "-m", "moving tree lacks required path")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    executable(fakebin / "docker", "exit 0\n")
    env = dict(
        VILLA=str(villa), VILLA_REF=pin, RENDER_VENV="/bin/true", SCORE_VENV="/bin/true",
        PATH=f"{fakebin}:{os.environ['PATH']}", MIN_FREE_GB="0", ARMS_PER_STUDY="1",
    )
    result = run(SCRIPTS / "preflight.sh", **env)
    assert result.returncode == 0, result.stdout + result.stderr
    env["VILLA_REF"] = "origin/main"
    result = run(SCRIPTS / "preflight.sh", **env)
    assert result.returncode != 0
    assert "origin/main missing lasagna" in result.stdout


def test_preflight_rejects_failed_import_probe(tmp_path):
    # A killed/crashed interpreter can emit no module names; silence is not PASS.
    result = run(SCRIPTS / "preflight.sh", SCORE_VENV="/bin/false", RENDER_VENV="/bin/true")
    assert result.returncode != 0
    assert "SCORE_VENV import probe failed" in result.stdout
