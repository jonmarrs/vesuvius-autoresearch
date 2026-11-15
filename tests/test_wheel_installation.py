"""Build an sdist, install its wheel, and exercise it without a checkout.

Uses uv (the project's installer) and the locked setuptools in the full review
environment. Builds/installation are offline and do not sync that environment.
Only third-party site-package directories are exposed to the fresh runtime;
their editable-install hooks are not processed. No GPU or study data is needed.
"""

import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(command, cwd, env):
    run = subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True, timeout=120
    )
    assert run.returncode == 0, run.stdout + run.stderr
    return run.stdout


@pytest.fixture(scope="module")
def installed_wheel(tmp_path_factory):
    uv = shutil.which("uv")
    assert uv, "wheel checks require uv; see README.md's installation requirements"
    workspace = tmp_path_factory.mktemp("installed-wheel")
    project = workspace / "source"
    project.mkdir()
    for name in (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "vesuvius_model.py",
        "scroll_augmentations.py",
    ):
        shutil.copy2(ROOT / name, project / name)
    for name in ("src", "volume_cartographer_wrapper"):
        shutil.copytree(
            ROOT / name,
            project / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"),
        )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update(
        UV_CACHE_DIR=str(workspace / "uv-cache"),
        UV_PYTHON_DOWNLOADS="never",
        CUDA_VISIBLE_DEVICES="",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    distributions = workspace / "distributions"
    build = [
        uv,
        "build",
        "--offline",
        "--no-build-isolation",
        "--python",
        sys.executable,
    ]
    _run(
        [*build, str(project), "--sdist", "--out-dir", str(distributions)],
        workspace,
        env,
    )
    (sdist,) = distributions.glob("*.tar.gz")
    _run(
        [*build, str(sdist), "--wheel", "--out-dir", str(distributions)], workspace, env
    )
    (wheel,) = distributions.glob("*.whl")

    runtime = workspace / "runtime"
    _run(
        [uv, "venv", "--offline", "--python", sys.executable, str(runtime)],
        workspace,
        env,
    )
    python = runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    _run(
        [
            uv,
            "pip",
            "install",
            "--offline",
            "--no-index",
            "--no-deps",
            "--python",
            str(python),
            str(wheel),
        ],
        workspace,
        env,
    )
    site = Path(
        _run(
            [
                str(python),
                "-I",
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib'))",
            ],
            workspace,
            env,
        ).strip()
    )
    # Append raw dependency paths, without importing other environments' .pth
    # files (which may point editable imports at a different project checkout).
    dependencies = list(
        dict.fromkeys(
            str(Path(path).resolve())
            for path in sys.path
            if Path(path).name in {"site-packages", "dist-packages"}
        )
    )
    (site / "third_party_runtime.pth").write_text("\n".join(dependencies) + "\n")
    empty = workspace / "empty"
    empty.mkdir()
    return {"wheel": wheel, "python": python, "site": site, "cwd": empty, "env": env}


def _probe(wheel, body):
    preflight = """
        import importlib.util
        import sys
        from pathlib import Path
        site = Path(sys.argv[1]).resolve()
        assert importlib.util.find_spec('scripts') is None, 'checkout scripts leaked into runtime'
        def installed(module):
            assert Path(module.__file__).resolve().is_relative_to(site), module.__file__
    """
    return _run(
        [
            str(wheel["python"]),
            "-I",
            "-c",
            textwrap.dedent(preflight) + textwrap.dedent(body),
            str(wheel["site"]),
        ],
        wheel["cwd"],
        wheel["env"],
    )


def test_wheel_contains_runtime_sources_and_excludes_checkout_trees(installed_wheel):
    with zipfile.ZipFile(installed_wheel["wheel"]) as archive:
        files = set(archive.namelist())
    expected = {
        p.relative_to(ROOT / "src").as_posix() for p in (ROOT / "src").rglob("*.py")
    }
    expected.update(
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "volume_cartographer_wrapper").rglob("*.py")
    )
    expected.update({"vesuvius_model.py", "scroll_augmentations.py"})
    assert expected <= files, sorted(expected - files)
    with zipfile.ZipFile(installed_wheel["wheel"]) as archive:
        (license_file,) = (name for name in files if name.endswith("/licenses/LICENSE"))
        assert archive.read(license_file) == (ROOT / "LICENSE").read_bytes()
    assert not any(
        name.startswith(
            ("scripts/", "villa/", "tests/", "repro/", "reports/", "local_data/")
        )
        for name in files
    )


def test_installed_model_factory_and_volume_reader(installed_wheel):
    _probe(
        installed_wheel,
        """
        import numpy as np
        import torch
        import zarr
        import vesuvius_model
        import scroll_augmentations
        import volume_cartographer_wrapper.volume as volumes
        from vesuvius_autoresearch.core import model_wrappers, vesuvius_loader
        for module in (vesuvius_model, scroll_augmentations, volumes, model_wrappers, vesuvius_loader):
            installed(module)
        model = model_wrappers.build_inference_model(
            patch_size=16, num_layers=4, base_feat=4, num_blocks=1, num_heads=1,
        ).eval()
        with torch.inference_mode():
            output = model(torch.zeros(1, 1, 4, 16, 16))
        assert output.shape == (1, 1, 16, 16) and torch.isfinite(output).all()
        values = np.arange(4 * 8 * 8, dtype=np.uint16).reshape(4, 8, 8)
        zarr.array(values, store='ct.zarr', overwrite=True)
        reader = vesuvius_loader.FastVesuviusVolume('ct.zarr', use_ridges=False, strict_reads=True)
        assert isinstance(reader.vol, volumes.FastLocalVolume), type(reader.vol)
        np.testing.assert_allclose(reader.read_ct(0, 0, 0, 4, 8, 8), values.astype(np.float32) / 65535)
    """,
    )


def test_installed_importer_preserves_uint16_ct_without_scripts(installed_wheel):
    _probe(
        installed_wheel,
        """
        import numpy as np
        import zarr
        from PIL import Image
        from vesuvius_autoresearch.core import surface_volume_import as importer
        from vesuvius_autoresearch.core import new_artifacts
        installed(importer)
        installed(new_artifacts)
        source = Path('tiffs')
        source.mkdir()
        values = np.arange(8 * 10, dtype=np.uint16).reshape(8, 10) * 700
        values[-1, -1] = 65535
        for index in range(3):
            Image.fromarray(values).save(source / f'{index:02}.tif')
        labels = source / 'inklabels.png'
        Image.fromarray(np.full((8, 10), 255, np.uint8)).save(labels)
        plan = importer.plan_import(source, labels, 0, 3, aligned_labels=True)
        importer.write_plan(plan, 'import-plan.json')
        output = importer.build_import('import-plan.json', 'prepared')
        result = zarr.open(str(output / 'surface_volume.zarr'), mode='r')
        assert result.dtype == np.uint16 and result.shape == (3, 8, 10)
        np.testing.assert_array_equal(result[:], np.stack([values] * 3))
    """,
    )


def test_installed_fiber_cli_runs_outside_checkout(installed_wheel):
    _probe(
        installed_wheel,
        """
        import numpy as np
        from vesuvius_autoresearch.fibers import cli
        installed(cli)
        np.save('fiber-input.npy', np.zeros((8, 8, 8), np.float32))
    """,
    )
    _run(
        [
            str(installed_wheel["python"]),
            "-I",
            "-m",
            "vesuvius_autoresearch.fibers.cli",
            "--input",
            "fiber-input.npy",
            "--output",
            "fiber-response.npy",
            "--device",
            "cpu",
        ],
        installed_wheel["cwd"],
        installed_wheel["env"],
    )
    _probe(
        installed_wheel,
        """
        import numpy as np
        result = np.load('fiber-response.npy', allow_pickle=False)
        assert result.shape == (8, 8, 8) and not result.any()
    """,
    )


def test_installed_detector_cli_help(installed_wheel):
    _probe(
        installed_wheel,
        """
        from vesuvius_autoresearch.detector import cli
        installed(cli)
    """,
    )
    help_text = _run(
        [
            str(installed_wheel["python"]),
            "-I",
            "-m",
            "vesuvius_autoresearch.detector.cli",
            "--help",
        ],
        installed_wheel["cwd"],
        installed_wheel["env"],
    )
    assert "infer" in help_text and "eval" in help_text
