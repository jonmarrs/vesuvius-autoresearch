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


def test_an_offline_init_that_fails_is_not_retried_as_a_fallback(monkeypatch, capsys):
    tried = _fake_wandb(monkeypatch, fails={"offline"})
    monkeypatch.setenv("WANDB_MODE", "offline")
    assert init_run(_Cfg(use_wandb=True)) is None
    assert tried == ["offline"]
    assert "falling back" not in capsys.readouterr().out


def test_a_tracking_error_mid_run_is_reported_once_not_raised(monkeypatch, capsys):
    """wandb.log raising (its service gone, say) ended the run; the validation
    log and image come before run_result.json, so a scored cycle was lost."""
    from scripts import wandb_tracking

    def broken(*args, **kwargs):
        raise BrokenPipeError("wandb service gone")

    fake = SimpleNamespace(
        run=object(), log=broken, watch=broken, Image=lambda *a, **k: a
    )
    monkeypatch.setitem(sys.modules, "wandb", fake)
    monkeypatch.setattr(wandb_tracking, "_REPORTED", set())
    wandb_tracking.log({"train/total_loss": 0.5}, step=10)
    wandb_tracking.log({"train/total_loss": 0.4}, step=20)
    wandb_tracking.watch_model(object(), model=None)
    square = [[0.2, 0.7], [0.1, 0.9]]
    wandb_tracking.log_prediction_image(object(), square, square, 0.5)
    out = capsys.readouterr().out
    assert out.count("wandb log failed") == 1
    assert "wandb watch failed" in out and "wandb image log failed" in out


@pytest.mark.parametrize(
    "incumbent, logged", [(0.27, True), (float("-inf"), False), (float("nan"), False)]
)
def test_the_selection_metrics_are_logged_under_run_result_names(incumbent, logged):
    """The incumbent is -inf without one and NaN when it cannot be compared."""
    from scripts.wandb_tracking import selection_metrics

    got = selection_metrics(
        val_f1=0.28, threshold=0.4, lift=1.5, roc_auc=0.8, incumbent=incumbent,
        is_success=1,
    )  # fmt: skip
    expected = {
        "val/val_f1": 0.28,
        "val/val_f1_threshold": 0.4,
        "val/ap_prevalence_lift": 1.5,
        "val/roc_auc": 0.8,
        "val/is_success": True,
    }
    if logged:
        expected["val/incumbent_val_f1"] = incumbent
    assert got == expected
    assert (
        type(got["val/is_success"]) is bool
    )  # a numpy bool or 1 would be logged as given


def test_train_logs_its_selection_metrics_with_its_validation():
    """The end of train() needs CUDA and data, so this reads its source: the
    validation log carries selection_metrics, given train()'s own values."""
    import ast

    source = Path(__file__).resolve().parents[1] / "scripts/training/train.py"
    logs = [
        node.args[0]
        for node in ast.walk(ast.parse(source.read_text()))
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) == "wandb_tracking.log"
        and node.args
        and isinstance(node.args[0], ast.Dict)
    ]
    (validation,) = [
        d
        for d in logs
        if any(isinstance(k, ast.Constant) and k.value == "val/val_bpb" for k in d.keys)
    ]
    (call,) = [
        v for k, v in zip(validation.keys, validation.values, strict=True) if k is None
    ]
    assert ast.unparse(call.func) == "wandb_tracking.selection_metrics"
    assert {k.arg: ast.unparse(k.value) for k in call.keywords} == {
        "val_f1": "val_f1",
        "threshold": "val_f1_threshold",
        "lift": "ap_prevalence_lift",
        "roc_auc": "roc_auc",
        "incumbent": "best_previous_val_f1",
        "is_success": "is_improvement",
    }
