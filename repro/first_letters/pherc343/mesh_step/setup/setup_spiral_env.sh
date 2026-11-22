#!/usr/bin/env bash
# Build the spiral-fit environment from villa 0fb38c45's own lock file (PyPI downloads only).
# Usage: setup_spiral_env.sh RUN_ROOT
set -euo pipefail
R=$1
unset UV_NO_SYNC
echo "ENV_START $(date -Is)"
UV_PROJECT_ENVIRONMENT="$R/venv_spiral" uv sync --project "$R/villa_src/volume-cartographer" \
    --package spiral --frozen --no-install-workspace --python 3.14
"$R/venv_spiral/bin/python" -I -c "import torch, zarr, edt, numpy, tensorstore; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'zarr', zarr.__version__, 'edt', edt.__version__ if hasattr(edt,'__version__') else '?', 'numpy', numpy.__version__)"
echo "ENV_EXIT 0 $(date -Is)"
