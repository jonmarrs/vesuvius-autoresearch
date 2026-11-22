#!/bin/bash
# Environment for the PHerc. 343 reproduction: villa 0fb38c45 venv (the recipe's ink/Dockerfile route), then the
# four public checkpoints, sha256-checked by the recipe's own fetch script.
set -euo pipefail
B=/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_repro
V=/home/jon/openclaw-workspace/Neo-VM/projects/villa-wt-ink-0fb38c45
R=$B/src/repo
cd "$B/work"
test "$(git -C "$V" rev-parse HEAD)" = 0fb38c45b488e192566ea83ae36369cb6db92652
python3 -I "$V/lasagna/scripts/bootstrap_venv.py" --venv "$B/venv" --backend cu130 --project "$V/lasagna"
uv pip install --python "$B/venv/bin/python" tifffile zarr numpy numcodecs opencv-python-headless safetensors scipy
"$B/venv/bin/python" -I -c "import vesuvius.ink_detection.inference.infer as m, cv2, zarr, torch, numpy, tifffile, scipy; print(m.__file__, cv2.__version__, zarr.__version__, torch.__version__, torch.version.cuda, torch.cuda.is_available(), numpy.__version__, tifffile.__version__, scipy.__version__)"
PY="$B/venv/bin/python" bash "$R/ink/scripts/fetch_checkpoints.sh" "$R/ink/models.tsv" "$B/ckpt"
echo SETUP_DONE
