import torch

from scripts.auxiliary_manager import AuxiliaryConfig, AuxiliaryManager


def test_auxiliary_manager_warns_when_enabled_tasks_have_no_outputs(capsys):
    manager = AuxiliaryManager(AuxiliaryConfig(enabled=True, task_types=["surface_normals"]))
    outputs = {"ink_2d": torch.zeros(1, 1, 4, 4)}
    targets = {"ink_2d": torch.zeros(1, 1, 4, 4)}

    loss = manager.compute_losses(outputs, targets)
    captured = capsys.readouterr()

    assert torch.is_tensor(loss)
    assert loss.item() == 0.0
    assert "auxiliary tasks are enabled" in captured.out


def test_auxiliary_manager_returns_tensor_when_disabled():
    manager = AuxiliaryManager(AuxiliaryConfig(enabled=False))
    outputs = {"ink_2d": torch.zeros(1, 1, 4, 4)}

    loss = manager.compute_losses(outputs, {})

    assert torch.is_tensor(loss)
    assert loss.device == outputs["ink_2d"].device
    assert loss.item() == 0.0
