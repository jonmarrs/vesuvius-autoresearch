import unittest

import torch
from scripts.auxiliary_manager import AuxiliaryConfig, AuxiliaryManager


class TestAuxiliaryManager(unittest.TestCase):
    def test_disabled_manager(self):
        config = AuxiliaryConfig(enabled=False)
        manager = AuxiliaryManager(config)

        self.assertEqual(manager.get_target_specs(), {})

        outputs = {"ink_2d": torch.randn(1, 1, 64, 64)}
        targets = {"ink_2d": torch.randn(1, 1, 64, 64)}

        loss = manager.compute_losses(outputs, targets)
        self.assertEqual(loss.item(), 0.0)
        self.assertFalse(loss.requires_grad)

    def test_enabled_manager_specs(self):
        config = AuxiliaryConfig(
            enabled=True,
            task_types=["surface_normals", "structure_tensor"],
            weights={"surface_normals": 0.1, "structure_tensor": 0.2},
        )
        manager = AuxiliaryManager(config)

        specs = manager.get_target_specs()
        self.assertIn("aux_surface_normals", specs)
        self.assertIn("aux_structure_tensor", specs)
        self.assertEqual(specs["aux_surface_normals"]["weight"], 0.1)
        self.assertEqual(specs["aux_structure_tensor"]["weight"], 0.2)

    def test_compute_losses(self):
        config = AuxiliaryConfig(
            enabled=True,
            task_types=["surface_normals"],
            weights={"surface_normals": 1.0},
        )
        manager = AuxiliaryManager(config)

        # Create mock outputs and targets
        # Loss should be 1.0 * MSE(ones, zeros) = 1.0 * 1.0 = 1.0
        outputs = {"aux_surface_normals": torch.ones(1, 1, 4, 4)}
        targets = {"aux_surface_normals": torch.zeros(1, 1, 4, 4)}

        loss = manager.compute_losses(outputs, targets)
        self.assertAlmostEqual(loss.item(), 1.0)
        self.assertTrue(loss.device.type in ["cpu", "cuda"])

    def test_missing_outputs_warning(self):
        config = AuxiliaryConfig(enabled=True, task_types=["non_existent"])
        manager = AuxiliaryManager(config)

        outputs = {"ink_2d": torch.zeros(1, 1, 4, 4)}
        targets = {"ink_2d": torch.zeros(1, 1, 4, 4)}

        # Should return 0.0 and not crash
        loss = manager.compute_losses(outputs, targets)
        self.assertEqual(loss.item(), 0.0)


if __name__ == "__main__":
    unittest.main()
