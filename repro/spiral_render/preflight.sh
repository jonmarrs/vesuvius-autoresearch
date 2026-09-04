#!/usr/bin/env bash
# Check every prerequisite this pipeline needs, and say precisely which is missing.
#
# The README lists obstacles that each cost hours to find: a wrong scale writing a
# black strip, a missing PYTHONPATH, a stale container binary, an OOM with no
# message. Every one surfaced only partway through a two-hour render. This checks
# them up front so a fresh machine fails in seconds rather than at band 18.
#
# THE TRAP IT EXISTS FOR: `VENV` means two DIFFERENT interpreters.
#   run_render.sh  needs the FIT venv     (torch, CUDA)          -> RENDER_VENV
#   score_arms.sh  needs the SCORING venv (huggingface_hub,
#                                          nnunetv2, torch)      -> SCORE_VENV
# Setting VENV globally satisfies one and breaks the other; scoring then dies
# instantly on `No module named huggingface_hub` after the render has already run.
#
# Usage:  preflight.sh            checks defaults
#         RENDER_VENV=... SCORE_VENV=... VILLA=... preflight.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

RENDER_VENV="${RENDER_VENV:-${VENV:-/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python}}"
SCORE_VENV="${SCORE_VENV:-/home/jon/openclaw-workspace/Neo-VM/data/ink_scorer_venv/bin/python}"
VILLA="${VILLA:-/home/jon/openclaw-workspace/Neo-VM/villa-spiral}"
IMAGE="${VC_IMAGE:-vc-render:local}"
MIN_FREE_GB="${MIN_FREE_GB:-10}"

fail=0
ok()   { printf '  \033[32mok\033[0m   %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=1; }
warn() { printf '  warn %s\n' "$1"; }

echo "spiral render/score preflight"
echo

echo "interpreters (these are DIFFERENT and must not be conflated)"
if [ -x "$RENDER_VENV" ]; then
  if "$RENDER_VENV" -c "import torch" 2>/dev/null; then
    ok "RENDER_VENV has torch  ($RENDER_VENV)"
  else bad "RENDER_VENV lacks torch  ($RENDER_VENV)"; fi
else bad "RENDER_VENV not executable: $RENDER_VENV"; fi

if [ -x "$SCORE_VENV" ]; then
  missing=$("$SCORE_VENV" - <<'PY' 2>/dev/null
mods = []
for m in ("huggingface_hub", "nnunetv2", "torch", "numpy", "PIL"):
    try: __import__(m)
    except Exception: mods.append(m)
print(",".join(mods))
PY
)
  if [ -z "$missing" ]; then ok "SCORE_VENV has huggingface_hub, nnunetv2, torch  ($SCORE_VENV)"
  else bad "SCORE_VENV missing: $missing  ($SCORE_VENV)"; fi
else bad "SCORE_VENV not executable: $SCORE_VENV"; fi

[ "$RENDER_VENV" = "$SCORE_VENV" ] && bad "RENDER_VENV and SCORE_VENV are the SAME path; they need different environments"

echo
echo "villa checkout (renders extract origin/main; fits run the WORKING TREE)"
if [ -d "$VILLA/.git" ]; then
  ok "villa checkout at $VILLA  (worktree $(git -C "$VILLA" rev-parse --short HEAD 2>/dev/null), origin/main $(git -C "$VILLA" rev-parse --short origin/main 2>/dev/null))"
  for t in spiral-fitting lasagna vesuvius/src; do
    git -C "$VILLA" cat-file -e "origin/main:$t" 2>/dev/null && ok "  origin/main has $t" || bad "  origin/main missing $t"
  done
else bad "no villa checkout at $VILLA"; fi

echo
echo "container tooling"
if command -v docker >/dev/null 2>&1; then
  if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    ok "image $IMAGE present"
    docker run --rm --entrypoint sh "$IMAGE" -c 'vc_tifxyz2obj --help 2>&1 | grep -q -- --keep' 2>/dev/null \
      && ok "  vc_tifxyz2obj accepts --keep (the rebuilt binary, not the stale published one)" \
      || bad "  vc_tifxyz2obj lacks --keep; rebuild from repro/spiral_render/Dockerfile"
  else bad "image $IMAGE missing; build it from repro/spiral_render/Dockerfile"; fi
else bad "docker not on PATH"; fi

echo
echo "patch and wrappers"
if [ -f "$HERE/serial_folds.patch" ]; then
  tmp=$(mktemp -d); mkdir -p "$tmp/spiral-fitting"
  if git -C "$VILLA" show "origin/main:spiral-fitting/get_ink_metrics.py" > "$tmp/spiral-fitting/get_ink_metrics.py" 2>/dev/null \
     && (cd "$tmp" && patch -p1 --batch --dry-run -i "$HERE/serial_folds.patch" >/dev/null 2>&1); then
    ok "serial_folds.patch applies to villa origin/main"
  else bad "serial_folds.patch does NOT apply; the villa pin has moved under it"; fi
  rm -rf "$tmp"
else bad "serial_folds.patch missing"; fi
[ -x "$HERE/bin/vc_render_tifxyz" ] && ok "bin/ wrappers present and executable" || bad "bin/ wrappers missing or not executable"

echo
echo "resources"
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  ok "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)"
else warn "no GPU visible; the lasagna flatten will be very slow"; fi
free_gb=$(df -BG --output=avail "$HERE" 2>/dev/null | tail -1 | tr -dc '0-9')
[ "${free_gb:-0}" -ge "$MIN_FREE_GB" ] && ok "disk: ${free_gb}G free (need >= ${MIN_FREE_GB}G per arm)" \
  || bad "disk: only ${free_gb}G free; an arm needs about ${MIN_FREE_GB}G"
tot_gb=$(free -g | awk '/^Mem:/{print $2}')
[ "${tot_gb:-0}" -ge 30 ] && ok "RAM: ${tot_gb}G (an outer render peaks near 26G)" \
  || warn "RAM ${tot_gb}G; outer renders peak near 26G and have been OOM-killed at 32G"

echo
[ "$fail" -eq 0 ] && echo "PREFLIGHT PASS" || echo "PREFLIGHT FAIL — fix the above before starting a multi-hour render"
exit "$fail"
