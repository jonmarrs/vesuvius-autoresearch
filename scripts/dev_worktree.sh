#!/bin/bash
# dev_worktree.sh: a worktree that tests its own code while the loop runs in main.
#
#   scripts/dev_worktree.sh add <branch> [base]   # .claude/worktrees/<branch>, base origin/main
#   scripts/dev_worktree.sh remove <branch>
#   scripts/dev_worktree.sh repair <branch>       # a worktree added without #119's fix (below)
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
    echo "usage: $0 add <branch> [base] | remove <branch> | repair <branch>" >&2
    exit 2
}

cmd="${1:-}"
name="${2:-}"
[ -n "$cmd" ] && [ -n "$name" ] || usage
common="$(git -C "$(dirname "$0")" rev-parse --path-format=absolute --git-common-dir)"
MAIN="$(dirname "$common")"
# A branch name, so never a path out of .claude/worktrees (`../..` would make
# WT the main checkout, whose villa repair would then rewrite).
git -C "$MAIN" check-ref-format --branch "$name" >/dev/null 2>&1 || {
    echo "not a branch name: $name" >&2
    exit 2
}
WT="$MAIN/.claude/worktrees/$name"
LINKS=".venv local_data checkpoints models" # the main checkout's, linked

# With extensions.worktreeConfig on, a linked worktree reads core.worktree from
# villa's shared config: an absorbed submodule's ../../../villa, which from a
# linked worktree is villa's git directory. Git then lists every file as
# deleted, and a checkout or clean in villa/ would write to or empty that
# directory. So each villa worktree gets its own, in its config.worktree. Only
# then: without the extension, git refuses --worktree once villa has a second
# worktree. Git reads extensions.* from the repository's own config only.
villa_needs_own_worktree() {
    [ "$(git -C "$MAIN/villa" config --local --bool extensions.worktreeConfig || true)" = true ]
}

case "$cmd" in
add)
    # Git creates the branch before it refuses a path in use, and a second add
    # then stops on the branch. It accepts an empty directory.
    if [ -L "$WT" ] || { [ -e "$WT" ] && { [ ! -d "$WT" ] || [ ! -r "$WT" ] || [ -n "$(ls -A "$WT")" ]; }; }; then
        echo "$WT already exists" >&2
        exit 1
    fi
    # So a branch that exists below is one this add made.
    if git -C "$MAIN" show-ref --verify --quiet "refs/heads/$name"; then
        echo "a branch named $name already exists" >&2
        exit 1
    fi
    # Whatever stops add from here, an error or a signal (on which bash runs
    # this with $? 0), says how to undo what it made.
    added=
    undo_add() {
        [ -z "$added" ] || return 0
        local steps=()
        if [ -e "$WT/.git" ]; then
            steps+=("$(printf '%q remove %q' "$0" "$name")")
        fi
        if git -C "$MAIN" show-ref --verify --quiet "refs/heads/$name"; then
            steps+=("$(printf 'git -C %q branch -D %q' "$MAIN" "$name")")
        fi
        if [ ${#steps[@]} -gt 0 ]; then
            local IFS=$'\n'
            echo "add stopped part-way. Undo it with, in order:" >&2
            echo "${steps[*]}" >&2
        fi
    }
    trap undo_add EXIT
    git -C "$MAIN" worktree add -b "$name" "$WT" "${3:-origin/main}"
    for link in $LINKS; do
        ln -s "$MAIN/$link" "$WT/$link"
    done
    pin="$(git -C "$WT" ls-tree HEAD villa | awk '{print $3}')"
    git -C "$MAIN/villa" worktree add --detach "$WT/villa" "$pin"
    if villa_needs_own_worktree; then
        git -C "$WT/villa" config --worktree core.worktree "$WT/villa"
    fi
    added=1
    echo "Worktree ready: $WT (villa at ${pin:0:9})."
    echo "Run Python there with UV_NO_SYNC=1."
    ;;
remove)
    # Refuse rather than discard local changes, and before changing anything: a
    # refusal once villa's worktree and the links are gone would leave a
    # worktree that is neither usable nor removable here.
    # Its own top level: inside another worktree, git answers for that one.
    own="$(git -C "$WT" rev-parse --absolute-git-dir 2>/dev/null || true)"
    top="$(git -C "$WT" rev-parse --show-toplevel 2>/dev/null || true)"
    case "$own" in
    "$common"/worktrees/*) [ -n "$top" ] && [ "$top" -ef "$WT" ] || own= ;;
    *) own= ;;
    esac
    if [ -z "$own" ]; then
        echo "no worktree at $WT" >&2
        exit 1
    fi
    if [ -e "$own/locked" ]; then
        echo "$WT is locked (git worktree unlock)" >&2
        exit 1
    fi
    if [ -d "$own/modules" ]; then
        echo "$WT has submodule repositories of its own ($own/modules)" >&2
        exit 1
    fi
    # git worktree remove deletes ignored files unasked, and the links' names
    # are ignored: anything there but a link would go with the worktree.
    exclude=()
    for link in $LINKS; do
        if [ -e "$WT/$link" ] && [ ! -L "$WT/$link" ]; then
            echo "$WT/$link is not the link to the main checkout's $link" >&2
            exit 1
        fi
        exclude+=(":(top,exclude)$link")
    done
    # What git worktree remove refuses, but for villa's files, which villa's own
    # remove checks, and the links, which go first: before 2026-10-13 no pattern
    # ignored a link. =all also hides a staged villa pointer, which git refuses.
    changes="$(git -C "$WT" status --porcelain --ignore-submodules=all -- . "${exclude[@]}")"
    if [ -n "$changes" ]; then
        echo "$WT has changes (git -C $WT status):" >&2
        echo "$changes" | sed -n 1,5p >&2
        exit 1
    fi
    if ! git -C "$WT" diff --cached --quiet --ignore-submodules=none -- villa; then
        echo "$WT has a staged villa pointer (git -C $WT diff --cached villa)" >&2
        exit 1
    fi
    villa_git="$(git -C "$MAIN/villa" rev-parse --path-format=absolute --git-common-dir)"
    villa_own="$(git -C "$WT/villa" rev-parse --absolute-git-dir 2>/dev/null || true)"
    case "$villa_own" in
    "$villa_git"/worktrees/*)
        git -C "$MAIN/villa" worktree remove "$WT/villa"
        ;;
    *)
        # Already removed, or never added (an add that stopped part-way).
        if [ -n "$(ls -A "$WT/villa" 2>/dev/null)" ]; then
            echo "$WT/villa is not one of villa's worktrees" >&2
            exit 1
        fi
        ;;
    esac
    # Removing villa's worktree deletes villa/; the empty directory is what an
    # unpopulated submodule looks like, and without it the outer worktree reads
    # as modified. Each step is skipped when done, so a remove stopped between
    # steps resumes.
    [ -d "$WT/villa" ] || mkdir "$WT/villa"
    for link in $LINKS; do
        if [ -L "$WT/$link" ]; then
            rm "$WT/$link"
        fi
    done
    git -C "$MAIN" worktree remove "$WT"
    ;;
repair)
    # A worktree added by this script without #119's fix (merged 2026-10-17
    # 23:12 PDT) has no core.worktree of its own: in its villa/, `git rev-parse
    # --show-toplevel` names villa's git directory. add cannot make it again,
    # since its branch exists; this sets core.worktree in place.
    villa_git="$(git -C "$MAIN/villa" rev-parse --path-format=absolute --git-common-dir)"
    own="$(git -C "$WT/villa" rev-parse --absolute-git-dir 2>/dev/null || true)"
    case "$own" in
    "$villa_git"/worktrees/*) ;;
    *)
        echo "no villa worktree at $WT/villa" >&2
        exit 1
        ;;
    esac
    if ! villa_needs_own_worktree; then
        echo "Nothing to repair: villa has no extensions.worktreeConfig."
        exit 0
    fi
    git -C "$WT/villa" config --worktree core.worktree "$WT/villa"
    top="$(git -C "$WT/villa" rev-parse --show-toplevel)"
    [ "$top" -ef "$WT/villa" ] || {
        echo "repair failed: $WT/villa still reports $top as its work tree" >&2
        exit 1
    }
    echo "Repaired: $WT/villa is its own work tree."
    # Changes made while it was broken, staged ones included, show here.
    changes="$(git -C "$WT/villa" status --short)"
    if [ -n "$changes" ]; then
        echo "Its villa/ has changes (git -C $WT/villa status):"
        echo "$changes" | sed -n 1,5p
    fi
    ;;
*)
    usage
    ;;
esac
