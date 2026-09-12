#!/usr/bin/env bash
# Extract BOTH caches with the committed extractor, then run the pre-registered
# seed-agreement control.
#
# The extractor imports villa's fit code (kornia, torch extensions), so it must
# run in the SPIRAL-FITTING venv. The detector and comparator need only numpy and
# run in the autoresearch venv. Mixing the two is what broke the first attempt.
set -u
O=/home/jon/openclaw-workspace/Neo-VM/spiral_out
R=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
S=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1
B=$(ls -d $O/*baseline01 | head -1); Z=$(ls -d $O/*seed02 | head -1)

extract() {  # run_dir out_pkl
  cd "$S"
  FIT_SPIRAL_PATCH_LOAD_WORKERS=1 CUDA_VISIBLE_DEVICES=0 \
    uv run python "$R/scripts/extract_winding_indices.py" \
      --run "$1" --dataset "$D" --out "$2" 2>&1 | tail -2
}
echo "### extracting baseline01"; extract "$B" "$O/wi_baseline01.pkl"
echo "### extracting seed02";     extract "$Z" "$O/wi_seed02.pkl"
cd "$R"
echo "### detector on baseline01"; uv run python scripts/detect_sheet_switches.py --cache $O/wi_baseline01.pkl --json-out $O/flags_baseline01_v2.json 2>&1 | head -4
echo "### detector on seed02";     uv run python scripts/detect_sheet_switches.py --cache $O/wi_seed02.pkl     --json-out $O/flags_seed02.json     2>&1 | head -4
echo "### SEED AGREEMENT"
uv run python scripts/compare_switch_flags.py --a $O/flags_baseline01_v2.json --b $O/flags_seed02.json
