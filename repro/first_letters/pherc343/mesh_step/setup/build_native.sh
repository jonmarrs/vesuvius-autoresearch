#!/usr/bin/env bash
# Build the three native modules into $R/native/build/vc and make that an importable package.
# nanobind is a build requirement that villa's lock file does not pin; it is installed here outside the
# locked environment and is not needed at run time.
set -euo pipefail
R=$1
unset UV_NO_SYNC
PY=$R/venv_spiral/bin/python
echo "NATIVE_START $(date -Is)"
uv pip install --python "$PY" --target "$R/native/nanobind_pkg" nanobind
NB=$(PYTHONPATH=$R/native/nanobind_pkg "$PY" -c "import nanobind; print(nanobind.__version__, nanobind.cmake_dir())")
echo "nanobind $NB"
cmake -S "$R/native" -B "$R/native/build" -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE="$PY" \
    -Dnanobind_DIR="${NB#* }" -DVC_PY_SRC="$R/villa_src/volume-cartographer/python/vc"
cmake --build "$R/native/build" -j 2
: > "$R/native/build/vc/__init__.py"
PYTHONPATH=$R/native/build "$PY" -I -c "
import sys; sys.path.insert(0, '$R/native/build')
import vc.track_store, vc.track_crossings, vc.spiral_sampling
print('native modules import:', [m for m in dir(vc.track_store) if not m.startswith('_')][:6])"
ls -la "$R/native/build/vc"
echo "NATIVE_EXIT 0 $(date -Is)"
