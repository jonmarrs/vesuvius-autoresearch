# Package and checkout workflows

Use an editable checkout for the research loop, the commands under `scripts/`,
and integrations that read the pinned Villa source tree. The README's `uv sync`
setup installs the local package alongside those checkout files.

The wheel includes `vesuvius_autoresearch.core`, `detector` and `fibers`, plus
`vesuvius_model`, `scroll_augmentations` and `volume_cartographer_wrapper`.
It supports library use and the packaged detector/fiber module entry points
from another working directory. Configuration files, trained checkpoints,
datasets, reports, research reproductions, orchestration scripts and Villa are
supplied separately.

Build distributions with Python 3.10 and uv:

```sh
uv build
```

To install the wheel in a separate environment whose dependencies have already
been provisioned:

```sh
uv pip install --python /path/to/environment/bin/python --no-deps dist/vesuvius_autoresearch-0.1.0-py3-none-any.whl
```

Without `--no-deps`, the installer resolves the wheel's declared requirements.
The checkout's `uv.lock` and Torch index configuration are separate from wheel
metadata; a wheel installation alone does not reproduce the locked CUDA setup.
The full environment remains large. Splitting CPU/GPU/research extras is a
separate review item.

## Verified installation behavior

The maintained [installation checks](../tests/test_wheel_installation.py) build
an sdist, build its wheel, and install it into a fresh environment. They run
isolated Python processes from an empty directory with checkout scripts absent
and require the project modules to come from the installed wheel. Third-party
CPU dependencies come from the review environment; their editable-install
hooks are not loaded. Build and installation steps run offline, without
syncing the existing environment.

The checks exercise:

- Inclusion of all runtime Python sources and the repository license.
- A small CPU `gated_unet` construction and forward pass through the inference
  factory, plus the existing local volume backend and uint16 normalization.
- The source-pinned TIFF/PNG importer through its Python API, including lossless
  uint16 CT publication without importing `scripts`.
- `python -m vesuvius_autoresearch.fibers.cli` on synthetic CPU input.
- `python -m vesuvius_autoresearch.detector.cli --help`.

These are synthetic installation checks. They do not validate a real fragment's
label registration, GPU capacity, all architectures, full training or detector
accuracy. The data importer still requires the caller to verify alignment.

## Workflows requiring an editable checkout

The research launchers, regional/production orchestration and their default
configuration files live in the checkout. Automatic training-patch discovery,
Villa-backed model architectures and optional Villa transforms/TTA also read
checkout-relative source files. Use an editable installation with the pinned
Villa submodule for those paths; the wheel does not bundle upstream code.

To run the installation checks in the full project environment:

```sh
uv run --no-sync python -m pytest tests/test_wheel_installation.py -q
```

They use uv and the locked setuptools already present in the full environment.
They are included in the curated validation registry. The minimal portable CI
profile remains independent of these scientific and build dependencies.

The runtime package/module list in `pyproject.toml` is explicit. When adding a
subpackage, update that list; the wheel payload check requires every runtime
Python source to be present. Keep checkout-only assets outside that payload.
