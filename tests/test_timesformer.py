import torch

from vesuvius_model import VesuviusConfig, VesuviusTimeSformer


def test_timesformer_forward_shapes_cpu():
    config = VesuviusConfig(
        patch_size=64,
        num_layers=4,
        batch_size=1,
        base_feat=64,
        num_blocks=8,
        num_heads=6,
        dropout=0.1,
        in_channels=1,
    )
    model = VesuviusTimeSformer(config).eval()
    x = torch.randn(1, 1, 4, 64, 64)

    with torch.no_grad():
        ink, fiber, qc, proj, st = model(
            x,
            return_fiber=True,
            return_qc=True,
            return_proj=True,
            return_st=True,
        )

    assert ink.shape == (1, 1, 64, 64)
    assert fiber.shape == (1, 1, 4, 64, 64)
    assert qc.shape == (1, 1)
    assert proj.shape == (1, 16)
    assert st.shape == (1, 6, 4, 64, 64)
