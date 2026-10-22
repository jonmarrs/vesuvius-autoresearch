"""Dry-run smoke tests for the three villa-baseline launchers.

These tests confirm each launcher emits a marker JSON, surfaces the correct
non-submittable / submittable flags, and never invokes a real subprocess in
default mode. They do NOT spend GPU; --execute is never set.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _script(name: str) -> Path:
    """Locate a launcher under scripts/, wherever it currently lives.

    The launchers moved out of scripts/ on 2026-06-02 and this file kept
    pointing at scripts/<name>, so every test here has been failing on a
    missing file ever since -- handing the `check=True` subprocess a path that
    does not exist. The move took three commits, and the break lands in two of
    them: 4d9388e1 renamed launch_neural_tracing.py into scripts/inference/,
    while a0a1b10b only ADDED copies of the three training launchers under
    scripts/training/ (926 insertions, 0 deletions) and c4be4c17 is what
    deleted the originals. So neural-tracing broke at 4d9388e1 and the other
    three at c4be4c17. Resolving the name means the next reorganisation cannot
    silently re-break them.
    """
    hits = sorted((REPO_ROOT / "scripts").rglob(name))
    assert len(hits) == 1, f"expected exactly one {name} under scripts/, found {hits}"
    return hits[0]


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    """Runs with check=True, so a non-zero exit raises here rather than being
    asserted by each caller -- those `assert proc.returncode == 0` lines were
    unreachable."""
    return subprocess.run(
        [sys.executable, str(_script(script)), *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def test_launch_gp_winner_writes_baseline_marker(tmp_path):
    config_out = tmp_path / "gp.yaml"
    _run(
        "launch_gp_winner.py",
        "--config-out",
        str(config_out),
        "--output-dir",
        str(tmp_path / "ckpt"),
        "--model-name",
        "gp_smoke",
        "--marker-out",
        str(tmp_path / "gp_marker.json"),
    )
    marker = tmp_path / "gp_marker.json"
    assert marker.exists()
    data = json.loads(marker.read_text())
    assert data["submittable"] is False
    assert data["patch_size"] == [16, 256, 256]
    assert data["executed"] is False
    assert config_out.exists()


def test_launch_mutex_writes_marker_and_blocks_execute_without_data(tmp_path):
    data_path = tmp_path / "mutex_data"  # intentionally empty
    config_out = tmp_path / "mutex.yaml"
    _run(
        "launch_mutex.py",
        "--data-path",
        str(data_path),
        "--config-out",
        str(config_out),
        "--model-name",
        "mutex_smoke",
        "--marker-out",
        str(tmp_path / "mutex_marker.json"),
    )
    marker = tmp_path / "mutex_marker.json"
    data = json.loads(marker.read_text())
    assert data["submittable"] is None  # patch size alone cannot certify a model
    assert data["window_px_within_limit"] is True  # default patch=64
    assert data["runtime_verified"] is False
    assert data["data_prepared"] is False
    assert data["executed"] is False


def test_launch_finetune_lejepa_uses_submittable_patch_and_finds_pretrain(tmp_path):
    config_out = tmp_path / "ft.yaml"
    _run(
        "launch_finetune_lejepa.py",
        "--config-out",
        str(config_out),
        "--output-dir",
        str(tmp_path / "ckpt"),
        "--model-name",
        "ft_smoke",
        "--marker-out",
        str(tmp_path / "ft_marker.json"),
    )
    marker = tmp_path / "ft_marker.json"
    data = json.loads(marker.read_text())
    assert data["patch_size"] == [32, 64, 64]
    assert data["submittable"] is True
    assert data["executed"] is False
    assert config_out.exists()
    # In this repo's known state there is a LeJEPA pretrain checkpoint and the
    # labeled Paris2Fr47 fragment; both should be auto-resolved. Both are
    # gitignored local files and the standard suite runs without data, so each is
    # asserted found where it is here, and named as a blocker where it is not.
    runs = REPO_ROOT / "checkpoints"
    has_checkpoint = any(runs.glob("lejepa_foundation_v1*/*_final.pth")) or any(
        runs.glob("lejepa_foundation_v1*/*_epoch*.pth")
    )
    fragment = REPO_ROOT / "local_data" / "PHercParis2Fr47"
    has_fragment = (fragment / "surface_volume").is_dir() and (
        fragment / "inklabels.png"
    ).exists()
    assert bool(data["pretrained_lejepa_checkpoint"]) is has_checkpoint, (
        "the LeJEPA pretrain ckpt must be found exactly when one is here"
    )
    assert bool(data["labeled_volumes"]) is has_fragment, (
        "PHercParis2Fr47 must be found exactly when it is here"
    )
    assert any("LeJEPA" in b for b in data["blockers"]) is not has_checkpoint
    assert any("PHercParis2Fr47" in b for b in data["blockers"]) is not has_fragment
    assert data["ready"] is (has_checkpoint and has_fragment)


def test_launch_finetune_lejepa_flags_non_submittable_when_patch_too_large(tmp_path):
    config_out = tmp_path / "ft_big.yaml"
    _run(
        "launch_finetune_lejepa.py",
        "--config-out",
        str(config_out),
        "--output-dir",
        str(tmp_path / "ckpt"),
        "--model-name",
        "ft_smoke_big",
        "--patch",
        "32",
        "128",
        "128",
        "--marker-out",
        str(tmp_path / "ft_big_marker.json"),
    )
    marker = tmp_path / "ft_big_marker.json"
    data = json.loads(marker.read_text())
    assert data["patch_size"] == [32, 128, 128]
    assert data["submittable"] is False


def test_launch_neural_tracing_falls_back_to_the_hf_sentinel(tmp_path):
    """The contract changed on 2026-06-05 (318d6b85) and this test did not.

    It used to assert that a missing local checkpoint is a blocker. That commit
    made the launcher fall back to villa's HuggingFace sentinel
    `extrap_displacement_latest` instead, so a missing local checkpoint stops
    being a blocker by design. The test kept asserting the old contract and had
    no way to pass; it was masked by the path breakage that made every test in
    this file error before reaching its assertions.

    What is pinned now is the new contract: the launcher always resolves SOME
    checkpoint, wires it into the command, and never blocks on it.
    """
    # Loaded by path rather than via sys.path.insert: that insert was never
    # undone, and an entry left at index 0 decides which module a later bare
    # import gets (scripts/production_predict.py had a namesake in
    # scripts/inference/ until 2026-10-17).
    spec = importlib.util.spec_from_file_location(
        "_lnt_probe", REPO_ROOT / "scripts" / "inference" / "launch_neural_tracing.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if mod._find_neural_tracing_checkpoint() is not None:
        pytest.skip(
            "a local tracing checkpoint exists, so the sentinel fallback cannot "
            "be exercised; the assertion below would degrade to comparing the "
            "launcher against its own resolver"
        )

    marker_out = tmp_path / "trace.json"
    _run(
        "launch_neural_tracing.py",
        "--scroll-id",
        "0125",
        "--division",
        "div_100",
        "--marker-out",
        str(marker_out),
    )
    assert marker_out.exists()
    data = json.loads(marker_out.read_text())

    assert data["checkpoint"] == "extrap_displacement_latest"
    cmd = data["command"]
    assert cmd[cmd.index("--checkpoint_path") + 1] == "extrap_displacement_latest"
    assert not any("checkpoint" in b for b in data["blockers"])
    assert data["socket_path"].endswith(".sock")
    # `ready` is not asserted: it turns on whether this machine happens to have
    # the OME-zarr volume, which is not what this test is about.


# villa's model module, as the launcher reads it: parsed for its sentinel names,
# never imported (it needs torch, and this one would raise).
_FAKE_TRACING_MODELS = """raise RuntimeError("imported")

_CHECKPOINT_SENTINELS = {
    "extrap_displacement_latest": {"repo_id": "scrollprize/extrap_displacement_latest"},
    "copy_displacement_latest": {"repo_id": "scrollprize/copy_displacement_latest"},
}
"""


@pytest.fixture
def tracing_launcher(tmp_path, monkeypatch):
    """The tracing launcher loaded in-process, with its project root, trace
    service and villa model module in tmp_path, and tmp_path the working
    directory."""
    spec = importlib.util.spec_from_file_location(
        "_lnt_unit", REPO_ROOT / "scripts" / "inference" / "launch_neural_tracing.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    service = tmp_path / "trace_service.py"
    service.write_text("")
    (tmp_path / "nets").mkdir()
    (tmp_path / "nets" / "models.py").write_text(_FAKE_TRACING_MODELS)
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mod, "TRACE_SERVICE", service)
    monkeypatch.chdir(tmp_path)
    return mod


def _checkpoint_files(*paths, start=1_000_000_000):
    """Empty checkpoint files, each modified a second after the one before."""
    for age, path in enumerate(paths):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
        os.utime(path, (start + age, start + age))


def test_the_newest_local_tracing_checkpoint_is_launched(tracing_launcher, tmp_path):
    base = tmp_path / "checkpoints" / "neural_tracing"
    # A name orders the iterations of one run, not the runs: run_b's sorts last
    # but was written first.
    older = base / "run_b" / "ckpt_000900.pth"
    newer = base / "run_a" / "ckpt_000100.pth"
    other = base / "run_c" / "model.pt"  # a .pth is preferred, however new a .pt
    _checkpoint_files(older, newer, other)
    (base / "run_d" / "ckpt_000999.pth").mkdir(parents=True)  # newest, not a file
    assert tracing_launcher._find_neural_tracing_checkpoint() == newer


def test_local_tracing_checkpoints_keep_their_base_and_suffix_order(
    tracing_launcher, tmp_path
):
    find = tracing_launcher._find_neural_tracing_checkpoint
    assert find() is None
    first = tmp_path / "checkpoints" / "neural_tracing"
    second = tmp_path / "checkpoints" / "rowcol_cond"
    _checkpoint_files(second / "a.pth")
    assert find() == second / "a.pth"
    # The first base that holds any checkpoint wins, even with only a .pt older
    # than the second base's .pth.
    _checkpoint_files(first / "b.pt", start=0)
    assert find() == first / "b.pt"
    # Equal modification times: the greatest path.
    _checkpoint_files(first / "x" / "c.pth", start=5)
    _checkpoint_files(first / "y" / "c.pth", start=5)
    assert find() == first / "y" / "c.pth"


def _resolvable_checkpoints(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "ckpt_000001.pth").write_bytes(b"")
    (tmp_path / "model.pth").write_bytes(b"")
    (tmp_path / "empty").mkdir()
    (tmp_path / "weights_only").mkdir()
    (tmp_path / "weights_only" / "model.pth").write_bytes(b"")
    (tmp_path / "nested" / "sub").mkdir(parents=True)
    (tmp_path / "nested" / "sub" / "ckpt_000001.pth").write_bytes(b"")


def _launch_tracing(launcher, tmp_path, monkeypatch, *extra):
    (tmp_path / "volume").mkdir(exist_ok=True)
    marker = tmp_path / "marker.json"
    argv = ["launch_neural_tracing.py", "--volume-zarr", str(tmp_path / "volume")]
    argv += ["--marker-out", str(marker), "--socket-path", str(tmp_path / "trace.sock")]
    monkeypatch.setattr(sys, "argv", argv + list(extra))
    assert launcher.main() == 0
    data = json.loads(marker.read_text())
    cmd = data["command"]
    assert cmd[cmd.index("--checkpoint_path") + 1] == data["checkpoint"]
    return data


@pytest.mark.parametrize(
    "checkpoint, passed, blocker",
    [
        # villa's sentinels, stripped as villa strips them
        ("extrap_displacement_latest", "extrap_displacement_latest", None),
        (" copy_displacement_latest\n", "copy_displacement_latest", None),
        # anything else is a path, passed absolute (<tmp> is the working directory)
        ("model.pth", "<tmp>/model.pth", None),
        (" model.pth ", "<tmp>/model.pth", None),
        ("run", "<tmp>/run", None),
        ("<tmp>/run", "<tmp>/run", None),
        ("missing.pth", "<tmp>/missing.pth", "checkpoint not found"),
        ("runs/missing", "<tmp>/runs/missing", "checkpoint not found"),
        ("ckpt_000100", "<tmp>/ckpt_000100", "checkpoint not found"),
        ("extrap_displacment_latest", "<tmp>/extrap_displacment_latest", "not found"),
        ("empty", "<tmp>/empty", "holds no ckpt_*.pth"),
        ("weights_only", "<tmp>/weights_only", "holds no ckpt_*.pth"),
        ("nested", "<tmp>/nested", "holds no ckpt_*.pth"),  # villa does not recurse
        (" ", " ", "checkpoint is empty"),
    ],
)
def test_an_explicit_checkpoint_that_cannot_load_blocks_the_launch(
    tracing_launcher, tmp_path, monkeypatch, checkpoint, passed, blocker
):
    _resolvable_checkpoints(tmp_path)
    checkpoint = checkpoint.replace("<tmp>", str(tmp_path))
    data = _launch_tracing(
        tracing_launcher, tmp_path, monkeypatch, "--checkpoint", checkpoint
    )
    assert data["checkpoint"] == passed.replace("<tmp>", str(tmp_path))
    if blocker is None:
        assert data["blockers"] == [] and data["ready"] is True
    else:
        assert len(data["blockers"]) == 1 and blocker in data["blockers"][0]
        assert data["ready"] is False


def test_a_typed_sentinel_is_checked_against_the_names_villa_holds(
    tracing_launcher, tmp_path, monkeypatch
):
    data = _launch_tracing(
        tracing_launcher, tmp_path, monkeypatch, "--checkpoint", "extrap_displacment"
    )
    assert data["blockers"] == [
        "checkpoint not found: extrap_displacment (villa's sentinel names: "
        "copy_displacement_latest, extrap_displacement_latest)"
    ]
    (tmp_path / "nets" / "models.py").unlink()
    data = _launch_tracing(
        tracing_launcher,
        tmp_path,
        monkeypatch,
        "--checkpoint",
        "copy_displacement_latest",
    )
    assert data["checkpoint"] == str(tmp_path / "copy_displacement_latest")
    assert "(villa's sentinel names: none could be read)" in data["blockers"][0]


def test_the_fallback_sentinel_is_one_villa_still_holds(
    tracing_launcher, tmp_path, monkeypatch
):
    data = _launch_tracing(tracing_launcher, tmp_path, monkeypatch)
    assert data["checkpoint"] == "extrap_displacement_latest"
    assert data["blockers"] == [] and data["ready"] is True
    models = tmp_path / "nets" / "models.py"
    models.write_text(models.read_text().replace("extrap_", "extrap_v2_"))
    data = _launch_tracing(tracing_launcher, tmp_path, monkeypatch)
    assert len(data["blockers"]) == 1
    assert data["blockers"][0].startswith(
        "checkpoint not found: extrap_displacement_latest (villa's sentinel names: "
        "copy_displacement_latest, extrap_v2_displacement_latest)"
    )
    assert data["ready"] is False


def test_the_launcher_reads_the_sentinels_of_villas_own_model_module():
    """The fallback names a sentinel the villa checkout holds, read from its real
    model module (the tests above use a stand-in)."""
    spec = importlib.util.spec_from_file_location(
        "_lnt_villa", REPO_ROOT / "scripts" / "inference" / "launch_neural_tracing.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not (mod.TRACE_SERVICE.parent / "nets" / "models.py").is_file():
        pytest.skip("villa's neural_tracing model module is not in this checkout")
    assert "extrap_displacement_latest" in mod._checkpoint_sentinels()


def _git(*args):
    """git in this repository, or a skip: no git, or a checkout that is not this
    repository's own (an unpacked copy inside another repository would answer for
    that one)."""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        pytest.skip("git is not installed")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != REPO_ROOT:
        pytest.skip("not this repository's git checkout")
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)


def _untracked_and_ignored(name, written_to):
    """No tracked file of this name anywhere, and where it is written is ignored."""
    tracked = _git("ls-files", "--", f":(glob)**/{name}")
    assert tracked.returncode == 0 and tracked.stdout == ""
    assert _git("check-ignore", "-q", written_to).returncode == 0


@pytest.mark.parametrize(
    "launcher, runner",
    [
        ("launch_gp_winner.py", "_gp_winner_runner.py"),
        ("launch_finetune_lejepa.py", "_finetune_lejepa_runner.py"),
    ],
)
def test_a_generated_runner_names_its_launcher_and_stays_out_of_git(
    tmp_path, launcher, runner
):
    """The runners are generated with this machine's paths on every run, into
    scripts/ (ignored). The June reorg committed one copy of each under
    scripts/training/, naming the launchers' old paths, which nothing ran."""
    path = _script(launcher)
    spec = importlib.util.spec_from_file_location(f"_{runner[1:-3]}_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.write_runner(tmp_path / runner, tmp_path)
    first = (tmp_path / runner).read_text().splitlines()[0]
    assert f"Invoked by {path.relative_to(REPO_ROOT)}." in first
    _untracked_and_ignored(runner, f"scripts/{runner}")


def test_the_proofreader_config_stays_out_of_git():
    """launch_proofreader.py writes it into the working directory (the repository
    root: it runs only beside villa/) on every launch. Three May commits had swept
    a copy in, which an ignore line alone would not have untracked."""
    _untracked_and_ignored("proofreader_config.json", "proofreader_config.json")
