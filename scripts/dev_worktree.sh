#!/bin/bash
# dev_worktree.sh: a worktree that tests its own code while the loop runs in main.
#
#   scripts/dev_worktree.sh add <branch> [base]   # .claude/worktrees/<branch>, base origin/main
#   scripts/dev_worktree.sh remove <branch>
#
# The loop trains from the main checkout, so other work happens in a worktree.
# This one shares the main checkout's .venv, local_data, checkpoints and models
# (symlinks; the gitignored data the tests and doc guards read) and gets
# villa as a linked worktree of the submodule at the pinned commit (shared
# objects, no network), so tests and hooks that read villa/ work.
#
# Run Python there with UV_NO_SYNC=1 (or `uv run --no-sync`). A syncing
# `uv run` re-points the shared .venv's editable install at the worktree, and
# the loop's spawned DataLoader workers would then import the worktree's code.
set -euo pipefail

usage() {
    echo "usage: $0 add <branch> [base] | remove <branch>" >&2
    exit 2
}

cmd="${1:-}"
name="${2:-}"
[ -n "$cmd" ] && [ -n "$name" ] || usage
common="$(git -C "$(dirname "$0")" rev-parse --path-format=absolute --git-common-dir)"
MAIN="$(dirname "$common")"
WT="$MAIN/.claude/worktrees/$name"

case "$cmd" in
add)
    git -C "$MAIN" worktree add -b "$name" "$WT" "${3:-origin/main}"
    ln -s "$MAIN/.venv" "$WT/.venv"
    ln -s "$MAIN/local_data" "$WT/local_data"
    ln -s "$MAIN/checkpoints" "$WT/checkpoints"
    ln -s "$MAIN/models" "$WT/models"
    pin="$(git -C "$WT" ls-tree HEAD villa | awk '{print $3}')"
    git -C "$MAIN/villa" worktree add --detach "$WT/villa" "$pin"
    echo "Worktree ready: $WT (villa at ${pin:0:9})."
    echo "Run Python there with UV_NO_SYNC=1."
    ;;
remove)
    # Each step refuses rather than discard local changes. Removing villa's
    # worktree deletes villa/; the empty directory is what an unpopulated
    # submodule looks like, and without it the outer worktree reads as modified.
    git -C "$MAIN/villa" worktree remove "$WT/villa"
    mkdir "$WT/villa"
    rm "$WT/.venv" "$WT/local_data" "$WT/checkpoints" "$WT/models"
    git -C "$MAIN" worktree remove "$WT"
    ;;
*)
    usage
    ;;
esac
