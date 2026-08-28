#!/usr/bin/env bash
# Job status without self-matching, which bit twice:
#   1. `pgrep -f fetch_patches.sh` typed at a shell matches that SHELL's own
#      command line, reporting a never-started job as RUNNING.
#   2. `ps -eo args= | grep -F "<pattern>"` matches the GREP's own argv.
# pgrep excludes itself, and this script's argv does not contain the patterns,
# so calling pgrep from in here is safe where typing it at a shell is not.
D="$(cd "$(dirname "$0")" && pwd)"
st() { pgrep -f -- "bash $D/$1" > /dev/null && echo RUNNING || echo "not running"; }
n()  { [ -f "$1" ] && wc -l < "$1" || echo 0; }
printf "%-14s %-12s %s\n" "metas sweep:" "$(st fetch_metas.sh)"     "$(ls -1 "$D/metas" 2>/dev/null|wc -l)/89237"
printf "%-14s %-12s %s\n" "chain:"       "$(st run_after_sweep.sh)" ""
printf "%-14s %-12s %s\n" "patch fetch:" "$(st fetch_patches.sh)"   "$(ls -1 "$D/verified_patches" 2>/dev/null|wc -l) dirs"
printf "%-14s %-12s %s\n" "misses:"      "" "metas=$(n "$D/metas_misses.txt") patches=$(n "$D/patch_misses.txt")"
