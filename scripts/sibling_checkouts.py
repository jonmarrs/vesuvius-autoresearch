"""Where this repo's sibling checkouts (../scrollgt, ../inkdelta, ../inkagree) live.

They sit beside the main checkout. A linked worktree lives inside it, at
.claude/worktrees/<branch>, so a path built from the worktree's own parent finds
nothing. Build sibling paths from main_checkout() instead.
"""

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def main_checkout(repo: Path = _REPO) -> Path:
    """The main working tree of ``repo``: itself, unless it is a linked worktree.

    A linked worktree's .git is a file, "gitdir: <main>/.git/worktrees/<name>", and
    that directory's commondir names the main checkout's .git.
    """
    dot_git = repo / ".git"
    if not dot_git.is_file():
        return repo
    gitdir = Path(dot_git.read_text().split("gitdir:", 1)[1].strip())
    gitdir = (repo / gitdir).resolve()
    commondir = gitdir / "commondir"
    if not commondir.is_file():
        return repo  # a submodule's .git file, not a worktree's
    return (gitdir / commondir.read_text().strip()).resolve().parent
