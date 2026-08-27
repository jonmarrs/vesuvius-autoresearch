"""Do the paths and commits our reports cite still exist?

`scripts/audit_report_claims.py` checks that a number in prose still matches the
artifact beside it. This checks the other half of a citation: that the thing
cited is still there at all.

WHY IT IS WORTH CHECKING. This repository has already lost three months to
exactly this rot. The June script reorganisation moved the villa-baseline
launchers into `scripts/training/` and `scripts/inference/`, and everything that
referred to the old locations kept referring to them: the tests failed on a
missing file for three months, and the launchers themselves resolved
PROJECT_ROOT one directory too shallow. Nothing pointed at the stale references
because nothing was looking. A report that cites `scripts/foo.py` after `foo.py`
has moved is the same defect in a document instead of in code, and it is worse
there, because a reader cannot run a document and see it fail.

WHAT IT CHECKS. Every backticked path in `reports/*.md` and `docs/*.md` that
looks like a repository file, and every backticked commit hash. Paths are
checked on disk. Commits are checked for reachability from `main`, because a
commit that exists only in a reflog or on a deleted branch is not something a
reader can look up.

WHAT IT DELIBERATELY DOES NOT DO. It does not fail a build. A stale reference in
a dated planning document from May is a historical record, not a defect, and a
gate that forced those to be edited would be destroying the record to satisfy a
tool. The output separates live documents from dated ones so that judgement
stays with a reader.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/audit_doc_references.py
"""

import os
import re
import subprocess
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

OUT = os.path.join(_REPO, "reports", "doc_reference_audit.txt")

BACKTICK_RE = re.compile(r"`([^`\n]+)`")
PATHISH_RE = re.compile(
    r"^(scripts|src|tests|reports|docs|configs|models|repro|tools|villa)/[\w./\-=]+$"
)
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
# A dated filename is a record of what was true then, not a claim about now.
DATED_RE = re.compile(r"20\d\d-\d\d")


def cited(path):
    """Backticked paths and commit hashes in one document."""
    text = open(path).read()
    paths, shas = set(), set()
    for tok in BACKTICK_RE.findall(text):
        tok = tok.strip()
        if tok.endswith("...") or "..." in tok:
            continue  # an elided path in prose is not a citation
        if PATHISH_RE.match(tok):
            paths.add(tok.split("#")[0].split(":")[0])
        elif SHA_RE.match(tok) and not tok.isdigit():
            shas.add(tok)
    return paths, shas


VILLA = os.path.join(_REPO, "villa")


def _is_ancestor(sha, ref, cwd):
    try:
        r = subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, ref],
            cwd=cwd,
            capture_output=True,
            timeout=30,
        )
        return r.returncode == 0
    except Exception:
        return False


def _exists(sha, cwd):
    try:
        r = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
            cwd=cwd,
            capture_output=True,
            timeout=30,
        )
        return r.returncode == 0
    except Exception:
        return False


def where(sha):
    """Which repository a cited commit belongs to, if any.

    The first version of this checked only this repository's `main` and reported
    21 unreachable commits, most of which are villa's -- our pin `ced62390e`,
    upstream `6847063f`, and the villa commits the older review documents cite.
    A tool that calls those broken is a tool nobody reads twice. Submodule
    commits are a different repository's history, not dangling references.
    """
    if _is_ancestor(sha, "main", _REPO):
        return "this repo"
    if os.path.isdir(VILLA) and _exists(sha, VILLA):
        return "villa submodule"
    if _exists(sha, _REPO):
        return "this repo, not on main"
    return None


def audit():
    docs = []
    for folder in ("reports", "docs"):
        d = os.path.join(_REPO, folder)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.endswith(".md"):
                docs.append(os.path.join(folder, name))

    missing_paths, missing_shas, n_paths, n_shas = [], [], 0, 0
    for rel in docs:
        paths, shas = cited(os.path.join(_REPO, rel))
        n_paths += len(paths)
        n_shas += len(shas)
        for p in sorted(paths):
            if not os.path.exists(os.path.join(_REPO, p)):
                missing_paths.append((rel, p))
        for s in sorted(shas):
            origin = where(s)
            if origin is None or origin == "this repo, not on main":
                missing_shas.append((rel, s, origin or "nowhere"))
    return docs, missing_paths, missing_shas, n_paths, n_shas


def main():
    docs, missing_paths, missing_shas, n_paths, n_shas = audit()
    live = [(d, x) for d, x in missing_paths if not DATED_RE.search(d)]
    dated = [(d, x) for d, x in missing_paths if DATED_RE.search(d)]

    lines = [
        "Do the paths and commits our reports cite still exist?",
        "",
        "The other half of a citation: not whether the number still matches, but whether",
        "the thing cited is still there. This repository lost three months to that rot",
        "once already, when a script reorganisation left every reference to the old",
        "locations pointing at nothing and no one was looking.",
        "",
        f"  documents scanned:        {len(docs)}",
        f"  paths cited:              {n_paths}",
        f"  commits cited:            {n_shas}",
        f"  paths that do not exist:  {len(missing_paths)}"
        f"  ({len(live)} in live documents, {len(dated)} in dated ones)",
        f"  commits unreachable:      {len(missing_shas)}",
        "",
    ]
    if live:
        lines.append("=== Stale paths in live documents ===")
        lines.append("  These are worth fixing: a reader following them finds nothing.")
        for d, p in live:
            lines.append(f"   {d:52s} {p}")
        lines.append("")
    if dated:
        lines.append("=== Stale paths in dated documents ===")
        lines.append(
            "  A dated document records what was true on its date. These are history,"
        )
        lines.append("  not defects, and editing them would destroy the record.")
        for d, p in dated:
            lines.append(f"   {d:52s} {p}")
        lines.append("")
    if missing_shas:
        lines.append("=== Commits not reachable from main ===")
        lines.append(
            "  A commit on a deleted branch or in a reflog is not something a reader can"
        )
        lines.append(
            "  look up, even though it may resolve locally. Commits belonging to the villa"
        )
        lines.append(
            "  submodule are a different repository's history and are not listed."
        )
        for d, s, origin in missing_shas:
            lines.append(f"   {d:52s} {s:42s} {origin}")
        lines.append("")
    if not missing_paths and not missing_shas:
        lines.append("  Every cited path and commit resolves.")
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
