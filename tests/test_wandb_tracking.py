import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wandb_tracking import build_run_config, init_run, wandb_enabled


@dataclass
class _Cfg:
    use_wandb: bool = False
    architecture: str = "resenc_unet"
    lr: float = 5e-5


def test_disabled_by_default():
    assert wandb_enabled(_Cfg()) is False


def test_enabled_when_flag_set():
    assert wandb_enabled(_Cfg(use_wandb=True)) is True


def test_env_disabled_overrides_flag(monkeypatch):
    monkeypatch.setenv("WANDB_MODE", "disabled")
    assert wandb_enabled(_Cfg(use_wandb=True)) is False


def test_build_run_config_flattens_dataclass():
    cfg = build_run_config(_Cfg(use_wandb=True, lr=1e-4))
    assert cfg["architecture"] == "resenc_unet"
    assert cfg["lr"] == 1e-4


def test_init_run_returns_none_when_disabled():
    # Must not touch wandb at all when disabled.
    assert init_run(_Cfg(use_wandb=False)) is None


def test_offline_run_end_to_end(tmp_path, monkeypatch):
    # Real offline init/log/finish must work without network or login.
    monkeypatch.setenv("WANDB_DIR", str(tmp_path))
    monkeypatch.setenv("WANDB_MODE", "offline")
    monkeypatch.setenv("WANDB_SILENT", "true")
    from scripts import wandb_tracking

    run = wandb_tracking.init_run(_Cfg(use_wandb=True), group="test-group")
    assert run is not None
    wandb_tracking.log({"val/skel_dist": 20.9, "val/centerline_dice": 0.198}, step=1)
    wandb_tracking.finish_run(run)
    # offline run files land under the wandb dir
    assert any(tmp_path.rglob("*.wandb")) or any(tmp_path.glob("wandb/offline-run-*"))
