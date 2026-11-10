"""The declared environment must execute Villa's configured source augmentations."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"pynrrd": "1.1.3", "fft-conv-pytorch": "1.2.0"}


def test_source_augmentation_imports_are_declared_and_locked():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = {
        canonicalize_name(requirement.name): requirement
        for text in project["project"]["dependencies"]
        for requirement in [Requirement(text)]
    }
    packages = tomllib.loads((ROOT / "uv.lock").read_text())["package"]
    root = next(
        package for package in packages if package["name"] == "vesuvius-autoresearch"
    )
    direct = {dependency["name"] for dependency in root["dependencies"]}
    for name, minimum in REQUIRED.items():
        assert name in requirements, f"source augmentation import needs declared {name}"
        assert minimum in requirements[name].specifier
        assert name in direct, f"lock must include direct dependency {name}"
        (locked,) = [package for package in packages if package["name"] == name]
        assert locked["version"] in requirements[name].specifier


def _probe_recipe(seed, result_path, configured=False):
    """Fresh-process probe; call real transforms, never a trainer/model/loader."""
    import copy
    import hashlib
    import importlib.util
    import inspect
    import random
    import traceback
    from dataclasses import asdict

    import numpy as np
    import torch

    attempts = []
    assert not torch.cuda.is_initialized()

    def no_cuda(*args, **kwargs):
        attempts.append("cuda initialization")
        raise AssertionError("CPU augmentation must not initialize CUDA")

    torch.cuda._lazy_init = no_cuda
    torch.cuda.init = no_cuda
    if hasattr(torch._C, "_cuda_init"):
        torch._C._cuda_init = no_cuda
    torch.cuda.is_available = lambda: False
    torch.cuda.device_count = lambda: 0
    config_path = ROOT / "config.json"
    config_bytes = config_path.read_bytes()
    record = {
        "seed": seed,
        "configured_json": configured,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "dependency_specs": {
            name: str(importlib.util.find_spec(name))
            for name in ("nrrd", "fft_conv_pytorch")
        },
    }
    try:
        from scripts.training import train
        from scripts.training.config import ExperimentConfig

        config = (
            ExperimentConfig.from_json(config_bytes.decode())
            if configured
            else ExperimentConfig(
                aug_mode="batchgeneratorsv2",
                patch_size=32,
                num_layers=16,
                use_ridges=False,
                use_wandb=False,
            )
        )
        settings_before = copy.deepcopy(asdict(config))
        assert (
            config.aug_mode == "batchgeneratorsv2" and not config.disable_augmentation
        )
        record["pipeline_import_error"] = train.TRAINING_TRANSFORMS_IMPORT_ERROR
        original = train.create_training_transforms
        calls = {"construct": 0, "sample": 0}

        def observe_constructor(shape):
            calls["construct"] += 1
            assert original is not None, train.TRAINING_TRANSFORMS_IMPORT_ERROR
            pipeline = original(shape)

            class ObservedPipeline:
                def __call__(self, **sample):
                    calls["sample"] += 1
                    return pipeline(**sample)

            return ObservedPipeline()

        def no_fallback(*args, **kwargs):
            raise AssertionError("configured Villa recipe must not fall back")

        if original is not None:
            record["pipeline_source"] = inspect.getfile(original)
            train.create_training_transforms = observe_constructor
        train._bg2_aug_cache.clear()
        train._get_villa_aug = no_fallback
        fallback_before = train.AUGMENTATION_FALLBACKS.copy()
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        shape = (
            2,
            2 if config.use_ridges else 1,
            config.num_layers,
            config.patch_size,
            config.patch_size,
        )
        x = torch.rand(shape, device="cpu")
        ink = (torch.rand(2, 1, *shape[-2:], device="cpu") > 0.5).float()
        fiber = ink.unsqueeze(2).clone()
        output = train.apply_augmentations(x, ink, fiber, 1, 2, config)
        expected = (x.shape, ink.shape, fiber.shape)
        for index, (value, size) in enumerate(zip(output, expected, strict=True)):
            assert value.device.type == "cpu" and value.shape == size
            assert value.dtype == torch.float32 and torch.isfinite(value).all()
            if index:
                assert ((value >= 0) & (value <= 1)).all()
        assert calls == {"construct": 1, "sample": 2}
        assert fallback_before == train.AUGMENTATION_FALLBACKS
        assert asdict(config) == settings_before
        assert not attempts and not torch.cuda.is_initialized()
        record.update(
            success=True,
            shape=list(shape),
            output_shapes=[list(value.shape) for value in output],
            calls=calls,
            fallback_before=fallback_before,
            fallback_after=train.AUGMENTATION_FALLBACKS.copy(),
            settings_unchanged=True,
        )
    except Exception as exc:
        record.update(
            success=False,
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
    record.update(
        cuda_initialization_attempts=len(attempts),
        cuda_initialized=torch.cuda.is_initialized(),
        config_file_unchanged=config_path.read_bytes() == config_bytes,
    )
    Path(result_path).write_text(json.dumps(record, indent=2) + "\n")
    assert record["success"], record


def test_real_source_augmentation_executes_without_fallback_or_cuda(tmp_path):
    result_path = tmp_path / "recipe.json"
    command = [
        sys.executable,
        "-c",
        "import runpy,sys; probe=runpy.run_path(sys.argv[1]); probe['_probe_recipe'](41,sys.argv[2],True)",
        str(Path(__file__).resolve()),
        str(result_path),
    ]
    env = os.environ.copy()
    env.update(
        CUDA_VISIBLE_DEVICES="",
        PYTHONDONTWRITEBYTECODE="1",
        WANDB_MODE="offline",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    result = subprocess.run(
        command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=90
    )
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads(result_path.read_text())
    assert record["success"] and record["calls"] == {"construct": 1, "sample": 2}
    assert record["configured_json"] and record["settings_unchanged"]
    assert (
        record["cuda_initialization_attempts"] == 0 and record["config_file_unchanged"]
    )
