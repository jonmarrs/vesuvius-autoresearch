import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

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
    pytest.importorskip("wandb")
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


def _fake_wandb(monkeypatch, fails):
    """A wandb whose init raises for the modes in ``fails``; records each try."""
    tried = []

    def init(**kwargs):
        tried.append(kwargs["mode"])
        if kwargs["mode"] in fails:
            raise RuntimeError(f"{kwargs['mode']} init failed")
        return SimpleNamespace(mode=kwargs["mode"])

    monkeypatch.setitem(sys.modules, "wandb", SimpleNamespace(init=init))
    monkeypatch.delenv("WANDB_MODE", raising=False)
    return tried


def test_a_failed_online_init_falls_back_to_offline(monkeypatch, capsys):
    tried = _fake_wandb(monkeypatch, fails={"online"})
    run = init_run(_Cfg(use_wandb=True))
    assert run.mode == "offline" and tried == ["online", "offline"]
    assert "falling back to offline" in capsys.readouterr().out


def test_a_failed_offline_init_leaves_the_run_untracked(monkeypatch, capsys):
    """It raised, before the first training step: the cycle crashed over
    tracking, which the module promises never happens."""
    tried = _fake_wandb(monkeypatch, fails={"online", "offline"})
    assert init_run(_Cfg(use_wandb=True)) is None
    assert tried == ["online", "offline"]
    assert "this run is not tracked" in capsys.readouterr().out


def test_wandb_missing_leaves_the_run_untracked(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "wandb", None)  # import raises ImportError
    assert init_run(_Cfg(use_wandb=True)) is None
    assert "cannot be imported" in capsys.readouterr().out


def test_train_logs_what_the_loop_selects_on():
    """train.py's validation log was wired on 2026-06-10, before the loop came
    to select on val_f1 gated by AP lift (2026-07-11), and never carried them.
    The end of train() needs CUDA and data, so this reads its source."""
    import ast

    source = Path(__file__).resolve().parents[1] / "scripts/training/train.py"
    keys = set()
    for node in ast.walk(ast.parse(source.read_text())):
        if (
            isinstance(node, ast.Call)
            and ast.unparse(node.func) == "wandb_tracking.log"
            and node.args
            and isinstance(node.args[0], ast.Dict)
        ):
            for key in node.args[0].keys:
                if isinstance(key, ast.Constant):
                    keys.add(key.value)
                elif key is None:  # a ** entry
                    keys.update(
                        k.value
                        for d in ast.walk(node.args[0])
                        if isinstance(d, ast.Dict)
                        for k in d.keys
                        if isinstance(k, ast.Constant)
                    )
    assert {
        "val/val_f1",
        "val/val_f1_threshold",
        "val/ap_prevalence_lift",
        "val/roc_auc",
        "val/is_success",
        "val/incumbent_val_f1",
    } <= keys
