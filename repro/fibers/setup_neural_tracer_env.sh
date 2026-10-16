#!/usr/bin/env bash
# docs/preregistration/2026-10-16_neural_fiber_tracer_entrant.md -- the isolated environment villa's neural fiber
# tracer runs in: villa's vesuvius package at the pinned commit, synced from villa's own lockfile (Python 3.14,
# torch >= 2.12, extra "models"), plus the pinned checkpoint in the Hugging Face cache. Nothing here touches this
# repository's .venv. Idempotent.
set -euo pipefail
REPO="${REPO:-/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch}"
T="${T:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer}"
VILLA_SHA=ccb431818fa68059138f2c964ae299fc474ff116
REPO_ID=scrollprize/fiber_single_small
REVISION=451182558cb3270cfc2ddf967acbd4f36b9b816b
mkdir -p "$T"
if [ ! -d "$T/villa" ]; then
  # A linked worktree of the submodule: shared objects, no network.
  git -C "$REPO/villa" worktree add --detach --no-checkout "$T/villa" "$VILLA_SHA"
fi
# vesuvius/ and the three local sources its lockfile names.
git -C "$T/villa" sparse-checkout set vesuvius segmentation/models/batchgeneratorsv2 \
  segmentation/models/arch/nnunet volume-cartographer
git -C "$T/villa" checkout --detach "$VILLA_SHA"
[ "$(git -C "$T/villa" rev-parse HEAD)" = "$VILLA_SHA" ] || { echo "villa worktree is not at $VILLA_SHA" >&2; exit 2; }
# volume-cartographer is a C++ (CMake) build. The tracer imports its bindings only lazily, for the vcz1 codec and
# the VESUVIUS_CT_READER=vc3d reader; these cubes are blosc-compressed and read with the default reader. So it is
# resolved from the lockfile but not installed; an import of `vc` would fail loudly, not silently.
( cd "$T/villa/vesuvius" && UV_PROJECT_ENVIRONMENT="$T/venv" \
    uv sync --frozen --extra models --no-install-package volume-cartographer ) 2>&1 | tail -5
"$T/venv/bin/python" - "$REPO_ID" "$REVISION" <<'EOF'
import hashlib, sys
from pathlib import Path
import torch
from huggingface_hub import snapshot_download
folder = Path(snapshot_download(sys.argv[1], revision=sys.argv[2], allow_patterns=["*.pt"]))
for f in sorted(folder.glob("*.pt")):
    print(f.name, hashlib.sha256(f.read_bytes()).hexdigest())
print("torch", torch.__version__, "cuda", torch.version.cuda, "available", torch.cuda.is_available())
import vesuvius.neural_tracing.tracers.fibers.tracing.volume  # noqa: F401  (imports, no GPU work)
print("tracer imports OK")
EOF
