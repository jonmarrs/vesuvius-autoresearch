#!/usr/bin/env python3
"""Run quick smoke tests across the autoresearch code paths.

Forces CPU so it doesn't contend with a running training process.
Target wall-clock: under two minutes. Output is structured for direct
copy into a TEST_REPORT Verification section.

  uv run python scripts/smoke_test.py
  uv run python scripts/smoke_test.py --list-only
  SMOKE_TEST_TRACEBACK=1 uv run python scripts/smoke_test.py  # show full tracebacks

Exit 0 if all tests pass or are skipped due to missing data; exit 1
if any test fails.
"""

import argparse
import os
import sys
import time
import traceback

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch  # noqa: E402

TRAIN_URI = "local_data/PHercParis2Fr47/surface_volume.zarr"
TRAIN_INKLABELS = "local_data/PHercParis2Fr47/inklabels.png"
TRAIN_MASK = "local_data/PHercParis2Fr47/mask.png"


class SkipTest(Exception):
    pass


RESULTS = []


def _run(name, fn):
    t0 = time.perf_counter()
    try:
        fn()
    except SkipTest as exc:
        dt = time.perf_counter() - t0
        RESULTS.append((name, "SKIP", dt, str(exc)))
        print(f"SKIP: {name} — {exc}")
        return
    except Exception as exc:
        dt = time.perf_counter() - t0
        RESULTS.append((name, "FAIL", dt, f"{type(exc).__name__}: {exc}"))
        print(f"FAIL: {name} ({dt:.2f}s) — {type(exc).__name__}: {exc}")
        if os.environ.get("SMOKE_TEST_TRACEBACK"):
            traceback.print_exc()
        return
    dt = time.perf_counter() - t0
    RESULTS.append((name, "PASS", dt, ""))
    print(f"PASS: {name} ({dt:.2f}s)")


# -- Tests --


def test_imports():
    import ensemble_predict  # noqa: F401

    import predict  # noqa: F401
    import train  # noqa: F401
    import vesuvius_autoresearch.core.model_wrappers as model_wrappers
    import vesuvius_autoresearch.core.vesuvius_loader as vesuvius_loader  # noqa: F401

    assert hasattr(model_wrappers, "GenericMultiTaskWrapper")
    assert hasattr(model_wrappers, "build_inference_model")


def test_build_resenc_unet():
    from vesuvius_autoresearch.core.model_wrappers import build_inference_model

    m = build_inference_model(
        architecture="resenc_unet", base_feat=32, use_ridges=False
    )
    n = sum(p.numel() for p in m.parameters())
    assert n > 0
    assert n < 50_000_000, f"unexpectedly large model ({n} params)"


def test_build_gated_unet():
    from vesuvius_autoresearch.core.model_wrappers import build_inference_model

    m = build_inference_model(
        architecture="gated_unet",
        base_feat=32,
        num_blocks=4,
        num_heads=4,
        patch_size=64,
    )
    assert sum(p.numel() for p in m.parameters()) > 0

    # Exercise the full forward + backward across every head. A param-count
    # check alone misses decoder shape/channel bugs that only surface at
    # runtime (e.g. the fusion2 spatial mismatch and qc_head dim mismatch).
    x = torch.randn(2, 1, 16, 64, 64)
    ink, fiber, qc, proj, st = m(
        x, return_fiber=True, return_qc=True, return_proj=True, return_st=True
    )
    assert ink.shape == (2, 1, 64, 64), f"unexpected ink shape {tuple(ink.shape)}"
    loss = sum(t.float().mean() for t in (ink, fiber, qc, proj, st))
    loss.backward()
    assert torch.isfinite(loss), "gated_unet produced a non-finite smoke loss"


def test_multi_task_heads_dummy_default():
    from vesuvius_autoresearch.core.model_wrappers import build_inference_model

    m = build_inference_model(
        architecture="resenc_unet", base_feat=32, use_ridges=False
    )
    x = torch.randn(2, 1, 16, 64, 64)
    ink, fiber, qc, proj, st = m(
        x,
        return_fiber=True,
        return_qc=True,
        return_proj=True,
        return_st=True,
    )
    assert qc.abs().max().item() == 0.0, "dummy qc head should output zero"
    assert st.abs().max().item() == 0.0, "dummy st head should output zero"


def test_multi_task_heads_real_outputs():
    from vesuvius_autoresearch.core.model_wrappers import build_inference_model

    m = build_inference_model(
        architecture="resenc_unet",
        base_feat=32,
        use_ridges=True,
        multi_task_heads=True,
    )
    x = torch.randn(2, 2, 16, 64, 64)
    ink, fiber, qc, proj, st = m(
        x,
        return_fiber=True,
        return_qc=True,
        return_proj=True,
        return_st=True,
    )
    assert fiber.abs().max().item() > 0, "real fiber head should be non-zero"
    assert st.abs().max().item() > 0, "real st head should be non-zero"
    # Real gradient flows through backbone via fiber loss.
    loss = fiber.pow(2).mean()
    loss.backward()
    bb_grad = None
    for p in m.model.parameters():
        if p.grad is not None and p.grad.abs().max().item() > 0:
            bb_grad = p.grad
            break
    assert bb_grad is not None, (
        "backbone should receive non-zero gradient from fiber loss"
    )


def test_best_model_loads():
    if not os.path.exists("best_model.pt"):
        raise SkipTest("best_model.pt not present")
    from train import load_shape_compatible_state
    from vesuvius_autoresearch.core.model_wrappers import build_inference_model

    chk = torch.load("best_model.pt", map_location="cpu", weights_only=False)
    sc = chk.get("config", {})
    m = build_inference_model(
        architecture=sc.get("architecture", "resenc_unet"),
        patch_size=sc.get("patch_size", 64),
        num_layers=sc.get("num_layers", 16),
        base_feat=sc.get("base_feat", 64),
        num_blocks=sc.get("num_blocks", 16),
        num_heads=sc.get("num_heads", 8),
        dropout=sc.get("dropout", 0.0),
        use_ridges=sc.get("use_ridges", False),
        multi_task_heads=sc.get("multi_task_heads", False),
    )
    skipped = load_shape_compatible_state(m, chk["model_state_dict"], "best_model.pt")
    n_skipped = len(skipped) if hasattr(skipped, "__len__") else 0
    # Allow a small tolerance for stale state-dict keys (e.g. removed aux modules).
    assert n_skipped <= 8, (
        f"too many skipped tensors ({n_skipped}) — architecture drift"
    )


def test_dataloader_3tuple_sobel():
    if not (os.path.exists(TRAIN_URI) and os.path.exists(TRAIN_INKLABELS)):
        raise SkipTest("training URI / inklabels not present")
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    ds = VesuviusLabeledDataset(
        TRAIN_URI,
        TRAIN_INKLABELS,
        TRAIN_MASK if os.path.exists(TRAIN_MASK) else None,
        patch_size=64,
        num_layers=24,
        seed=42,
        use_ridges=False,
        require_ink=True,
        target_fiber_source="sobel_z",
    )
    item = ds[0]
    assert len(item) == 3, f"expected 3-tuple, got {len(item)}-tuple"
    patch, label, fiber = item
    assert patch.shape[-2:] == (64, 64)
    assert fiber.abs().max().item() == 0.0, (
        "sobel_z source should return zero placeholder"
    )


def test_dataloader_frangi_target():
    if not (os.path.exists(TRAIN_URI) and os.path.exists(TRAIN_INKLABELS)):
        raise SkipTest("training URI / inklabels not present")
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    ds = VesuviusLabeledDataset(
        TRAIN_URI,
        TRAIN_INKLABELS,
        None,
        patch_size=64,
        num_layers=24,
        seed=42,
        use_ridges=False,
        require_ink=True,
        target_fiber_source="frangi",
        target_fiber_sigma=2.0,
    )
    _, _, fiber = ds[0]
    assert fiber.abs().max().item() > 0, "frangi source should produce non-zero output"


def test_augmentations_albumentations():
    from train import ExperimentConfig, apply_augmentations

    config = ExperimentConfig()
    config.aug_mode = "albumentations"
    x = torch.rand(2, 1, 16, 64, 64)
    ink = torch.rand(2, 1, 64, 64)
    fiber = torch.rand(2, 1, 1, 64, 64)
    xa, ia, fa = apply_augmentations(
        x, ink, fiber, step=0, max_steps=100, config=config
    )
    assert xa.shape == x.shape
    assert ia.shape == ink.shape


def test_augmentations_bg2():
    from train import ExperimentConfig, apply_augmentations, create_training_transforms

    if create_training_transforms is None:
        raise SkipTest("create_training_transforms not available")
    config = ExperimentConfig()
    config.aug_mode = "batchgeneratorsv2"
    x = torch.rand(2, 1, 16, 64, 64)
    ink = torch.rand(2, 1, 64, 64)
    fiber = torch.rand(2, 1, 1, 64, 64)
    xa, ia, fa = apply_augmentations(
        x, ink, fiber, step=0, max_steps=100, config=config
    )
    assert xa.shape == x.shape


def test_bandit_templates():
    import run_autoresearch_loop as r

    families = sorted(set(t["family"] for t in r.tweak_templates))
    for dead in ("auxiliary", "iterative", "foundation"):
        assert dead not in families, (
            f"dead family '{dead}' resurfaced in tweak_templates"
        )
    for t in r.tweak_templates:
        if "applies_when" in t:
            assert callable(t["applies_when"]), (
                f"applies_when not callable on {t['attr']}"
            )
    # Sanity: the four villa-borrow axes from 2026-05-19/20 are present.
    attrs = {t["attr"] for t in r.tweak_templates}
    for expected in ("aug_mode", "target_fiber_source", "multi_task_heads"):
        assert expected in attrs, f"expected bandit axis '{expected}' missing"


TESTS = [
    ("imports", test_imports),
    ("build_resenc_unet", test_build_resenc_unet),
    ("build_gated_unet", test_build_gated_unet),
    ("multi_task_heads_dummy_default", test_multi_task_heads_dummy_default),
    ("multi_task_heads_real_outputs", test_multi_task_heads_real_outputs),
    ("best_model_loads", test_best_model_loads),
    ("dataloader_3tuple_sobel", test_dataloader_3tuple_sobel),
    ("dataloader_frangi_target", test_dataloader_frangi_target),
    ("augmentations_albumentations", test_augmentations_albumentations),
    ("augmentations_bg2", test_augmentations_bg2),
    ("bandit_templates", test_bandit_templates),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--list-only", action="store_true", help="Print test names and exit."
    )
    args = p.parse_args()
    if args.list_only:
        for name, _ in TESTS:
            print(name)
        return 0

    t_start = time.perf_counter()
    for name, fn in TESTS:
        _run(name, fn)

    total = time.perf_counter() - t_start
    n_pass = sum(1 for _, status, _, _ in RESULTS if status == "PASS")
    n_skip = sum(1 for _, status, _, _ in RESULTS if status == "SKIP")
    n_fail = sum(1 for _, status, _, _ in RESULTS if status == "FAIL")

    print()
    print(
        f"--- {n_pass}/{len(RESULTS)} passed, {n_skip} skipped, {n_fail} failed in {total:.1f}s ---"
    )
    if n_fail:
        print("Failures:")
        for name, status, _, msg in RESULTS:
            if status == "FAIL":
                print(f"  {name}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
