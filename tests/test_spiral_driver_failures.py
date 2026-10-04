"""Exercise shell entry points with tiny local stand-ins, without GPU/data access."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "repro/spiral_render"
VALID_METRICS = {
    "summary": {"total_pixels": 100, "total_fg_pixels": 0},
    "strips": [{"total_pixels": 100, "fg_pixels": 0}],
}


def executable(path, body):
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)
    return path


def run(script, *args, cwd=None, **env):
    return subprocess.run(
        ["bash", str(script), *map(str, args)],
        cwd=cwd,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=10,
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
    scorer = executable(
        tmp_path / "scorer",
        'mkdir -p "$5"\ncat > "$5/metrics.json" <<\'JSON\'\n'
        + json.dumps(VALID_METRICS)
        + "\nJSON\n",
    )
    result = run(
        SCRIPTS / "score_arms.sh",
        arm,
        cwd=tmp_path,
        SCORE_VENV=scorer.name,
        VENV="/bin/false",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (arm / "ink_metric/metrics.json").exists()


def test_render_resolves_relative_workdir_and_interpreter(tmp_path):
    arm = tmp_path / "arm"
    (arm / "spiral-fitting").mkdir(parents=True)
    probe = executable(tmp_path / "renderer", 'test "$3" = "$EXPECTED_MESHES"\n')
    result = run(
        SCRIPTS / "run_render.sh",
        "arm",
        cwd=tmp_path,
        RENDER_VENV=probe.name,
        VENV="/bin/false",
        EXPECTED_MESHES=str(arm / "meshes"),
    )
    assert result.returncode == 0, result.stdout + result.stderr


def outer_fixture(tmp_path, render_rc=0, score_rc=0):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(SCRIPTS / "run_outer_arms.sh", scripts)
    shutil.copy(SCRIPTS / "artifacts.py", scripts)
    executable(scripts / "run_render.sh", f"exit {render_rc}\n")
    executable(
        scripts / "score_arms.sh", f'touch "$1/scorer_called"\nexit {score_rc}\n'
    )
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


@pytest.mark.parametrize("content", ["{}", "null", '{"summary":'])
def test_outer_driver_rejects_invalid_completion_artifact(tmp_path, content):
    driver, root, arm = outer_fixture(tmp_path, render_rc=1)
    (arm / "ink_metric").mkdir()
    (arm / "ink_metric/metrics.json").write_text(content)
    result = run(driver, root, "120", "120", f"test={arm / 'meshes'}")
    assert result.returncode != 0, result.stdout
    assert "already scored" not in result.stdout


def test_outer_driver_rejects_wrong_windings_with_correct_count(tmp_path):
    driver, root, arm = outer_fixture(tmp_path)
    (arm / "meshes/w120_spliced_test").rename(arm / "meshes/w121_spliced_test")
    result = run(driver, root, "120", "120", f"test={arm / 'meshes'}")
    assert result.returncode != 0
    assert not (arm / "scorer_called").exists()


def test_outer_driver_does_not_resume_scores_from_another_winding_range(tmp_path):
    driver, root, arm = outer_fixture(tmp_path)
    (arm / "meshes/w120_spliced_test").rename(arm / "meshes/w121_spliced_test")
    (arm / "ink_metric").mkdir()
    (arm / "ink_metric/metrics.json").write_text(json.dumps(VALID_METRICS))
    result = run(driver, root, "120", "120", f"test={arm / 'meshes'}")
    assert result.returncode != 0, result.stdout
    assert "already scored" not in result.stdout


def test_outer_driver_skips_coherent_completed_arm(tmp_path):
    driver, root, arm = outer_fixture(tmp_path, render_rc=1)
    (arm / "ink_metric").mkdir()
    (arm / "ink_metric/metrics.json").write_text(json.dumps(VALID_METRICS))
    result = run(driver, root, "120", "120", f"test={arm / 'meshes'}")
    assert result.returncode == 0, result.stdout
    assert "already scored" in result.stdout


def sequence_fixture(tmp_path, fit_body=None, retry_body="exit 1\n"):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(SCRIPTS / "run_arm_sequence.sh", scripts)
    shutil.copy(SCRIPTS / "artifacts.py", scripts)
    executable(scripts / "run_with_retry.sh", retry_body)
    root = tmp_path / "output"
    root.mkdir()
    if fit_body is not None:
        executable(root / "fit_test.sh", fit_body)
    villa = tmp_path / "villa"
    (villa / ".git").mkdir(parents=True)
    return scripts / "run_arm_sequence.sh", root, villa


def test_sequence_reports_missing_fit_script(tmp_path):
    driver, root, villa = sequence_fixture(tmp_path)
    result = run(driver, root, "120", "120", "test", VILLA=str(villa))
    assert result.returncode != 0, result.stdout


def test_sequence_failed_fit_does_not_wait_for_meshes(tmp_path):
    driver, root, villa = sequence_fixture(tmp_path, fit_body="exit 7\n")
    # A synchronous failed fit used to enter the one-hour mesh wait.
    result = run(driver, root, "120", "120", "test", VILLA=str(villa))
    assert result.returncode != 0, result.stdout
    assert "rc=7" in result.stdout


def test_sequence_reports_render_failure(tmp_path):
    driver, root, villa = sequence_fixture(tmp_path)
    (root / "some_patch_test/meshes/fitted_test/w120_spliced_test").mkdir(parents=True)
    result = run(driver, root, "120", "120", "test", VILLA=str(villa))
    assert result.returncode != 0, result.stdout


def test_sequence_requires_requested_windings_not_just_count(tmp_path):
    driver, root, villa = sequence_fixture(
        tmp_path, retry_body='touch "$2/retry_called"\n'
    )
    (root / "some_patch_test/meshes/fitted_test/w121_spliced_test").mkdir(parents=True)
    result = run(driver, root, "120", "120", "test", VILLA=str(villa))
    assert result.returncode != 0
    assert not (root / "retry_called").exists()


def test_sequence_success_after_fitting_and_scoring(tmp_path):
    driver, root, villa = sequence_fixture(
        tmp_path,
        fit_body='mkdir -p "$(dirname "$0")/some_patch_test/meshes/fitted_test/w120_spliced_test"\n',
        retry_body='mkdir -p "$2/outer_test/ink_metric" "$2/outer_test/meshes/w120_spliced_test"\ncat > "$2/outer_test/ink_metric/metrics.json" <<\'JSON\'\n'
        + json.dumps(VALID_METRICS)
        + "\nJSON\n",
    )
    result = run(driver, root, "120", "120", "test", VILLA=str(villa))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[ok] test scored" in result.stdout


def test_sequence_rejects_ambiguous_fit_directories(tmp_path):
    driver, root, villa = sequence_fixture(tmp_path)
    for prefix in ("a", "b"):
        (root / f"{prefix}_patch_test/meshes/fitted_test/w120_spliced_test").mkdir(
            parents=True
        )
    result = run(driver, root, "120", "120", "test", VILLA=str(villa))
    assert result.returncode != 0
    assert "ambiguous" in result.stderr


def test_successful_fit_with_missing_meshes_times_out_as_failure(tmp_path):
    driver, root, villa = sequence_fixture(tmp_path, fit_body="exit 0\n")
    result = run(
        driver, root, "120", "120", "test", VILLA=str(villa), FIT_MESH_WAIT_SECONDS="0"
    )
    assert result.returncode != 0
    assert "meshes never appeared" in result.stdout


@pytest.mark.parametrize("snapshot_rc", [0, 7])
def test_retry_requires_successful_exit_and_valid_metrics(tmp_path, snapshot_rc):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("run_with_retry.sh", "artifacts.py"):
        shutil.copy(SCRIPTS / name, scripts)
    root = tmp_path / "output"
    root.mkdir()
    executable(
        scripts / "run_snapshot.sh",
        'mkdir -p "$1/outer_test/ink_metric" "$1/outer_test/meshes/w120_spliced_test"\ncat > "$1/outer_test/ink_metric/metrics.json" <<\'JSON\'\n'
        + json.dumps(VALID_METRICS)
        + f"\nJSON\nexit {snapshot_rc}\n",
    )
    result = run(
        scripts / "run_with_retry.sh",
        "1",
        root,
        "120",
        "120",
        "test=unused",
        RETRY_WAIT_FIRST="0",
    )
    assert result.returncode == (0 if snapshot_rc == 0 else 1), result.stdout


def test_score_rejects_success_exit_with_invalid_metrics(tmp_path):
    arm = tmp_path / "arm"
    (arm / "meshes/ink").mkdir(parents=True)
    (arm / "meshes/ink/strip.jpg").touch()
    (arm / "spiral-fitting").mkdir()
    scorer = executable(
        tmp_path / "scorer", 'mkdir -p "$5"\necho \'{}\' > "$5/metrics.json"\n'
    )
    result = run(SCRIPTS / "score_arms.sh", arm, SCORE_VENV=str(scorer))
    assert result.returncode != 0, result.stdout
    assert not (arm / "ink_metric/metrics.json").exists()


def test_snapshot_preserves_default_villa_location(tmp_path):
    # A frozen driver is outside the repository: ../../villa no longer refers to
    # the checkout. The snapshot launcher must pass the original location through.
    source = tmp_path / "repo/repro/spiral_render"
    source.mkdir(parents=True)
    villa = tmp_path / "repo/villa"
    villa.mkdir()
    shutil.copy(SCRIPTS / "run_snapshot.sh", source)
    executable(
        source / "probe.sh",
        'test "$VILLA" = "$EXPECTED_VILLA" && test "$REPO" = "$EXPECTED_REPO"\n',
    )
    root = tmp_path / "snapshots"
    root.mkdir()
    result = run(
        source / "run_snapshot.sh",
        root,
        "probe.sh",
        VILLA="",
        REPO="",
        EXPECTED_VILLA=str(villa),
        EXPECTED_REPO=str(tmp_path / "repo"),
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_preflight_checks_pinned_tree_not_moving_main(tmp_path):
    villa = tmp_path / "villa"
    villa.mkdir()

    def git(*args):
        return subprocess.check_output(
            [
                "git",
                "-C",
                str(villa),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                *args,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

    git("init")
    for name in (
        "spiral-fitting/get_ink_metrics.py",
        "lasagna/fit.py",
        "vesuvius/src/init.py",
    ):
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
    env = {
        "VILLA": str(villa),
        "VILLA_REF": pin,
        "RENDER_VENV": "/bin/true",
        "SCORE_VENV": "/bin/true",
        "PATH": f"{fakebin}:{os.environ['PATH']}",
        "MIN_FREE_GB": "0",
        "ARMS_PER_STUDY": "1",
    }
    result = run(SCRIPTS / "preflight.sh", **env)
    assert result.returncode == 0, result.stdout + result.stderr
    env["VILLA_REF"] = "origin/main"
    result = run(SCRIPTS / "preflight.sh", **env)
    assert result.returncode != 0
    assert "origin/main missing lasagna" in result.stdout


def test_preflight_rejects_failed_import_probe(tmp_path):
    # A killed/crashed interpreter can emit no module names; silence is not PASS.
    result = run(
        SCRIPTS / "preflight.sh", SCORE_VENV="/bin/false", RENDER_VENV="/bin/true"
    )
    assert result.returncode != 0
    assert "SCORE_VENV import probe failed" in result.stdout
