"""Recover which villa tree an arm rendered from, for arms predating VILLA_SHA.

`setup_workdir.sh` only started recording `VILLA_SHA` on 2026-09-14. Arms rendered
before that left no direct record, and their work dirs are deleted after scoring,
so the extracted tree cannot be hashed either. But two things survive:

* `sequence_<arm>.log` carries `[render] <arm> <ISO timestamp>` -- the moment
  `setup_workdir.sh` resolved the ref;
* the villa checkout's **reflog for `origin/main`** records every fetch that moved
  it, with timestamps.

Intersecting the two recovers the SHA. This is reconstruction, not a record, so it
is validated against the arms that DO carry a logged `VILLA_SHA`: if the method
cannot reproduce those, it is not trusted for the others. As of 2026-09-14 it
reproduces `curbase_s6` (bfef6abe0) and `curbase_s7` (be09a8503) exactly.

Why it matters: a study comparing arms rendered from different trees is confounded
unless those trees are equivalent on the render path. Pair this with
`check_render_equivalence.py`, which answers whether the difference can matter.

Usage:
  ./.venv/bin/python scripts/reconstruct_render_provenance.py curbase_s1 curbase_s2
  ... --spiral-out DIR --villa DIR
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RENDER_RE = re.compile(
    r"^\[render\]\s+(\S+)\s+(\d{4}-\d{2}-\d{2}T[\d:]{8}[+-]\d{2}:\d{2})"
)
REFLOG_RE = re.compile(r"^(\w+) \S+@\{([\d-]+ [\d:]+ [+-]\d{4})\}")


def reflog(villa: str) -> list[tuple[datetime, str]]:
    """(when origin/main became this sha, sha), oldest first."""
    out = subprocess.run(
        ["git", "-C", villa, "reflog", "show", "origin/main", "--date=iso"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot read reflog in {villa}: {out.stderr.strip()}")
    moves = []
    for line in out.stdout.splitlines():
        m = REFLOG_RE.match(line)
        if m:
            moves.append(
                (datetime.strptime(m.group(2), "%Y-%m-%d %H:%M:%S %z"), m.group(1))
            )
    return sorted(moves)


def render_start(spiral_out: str, arm: str) -> datetime | None:
    p = Path(spiral_out) / f"sequence_{arm}.log"
    if not p.exists():
        return None
    for line in p.read_text(errors="replace").splitlines():
        m = RENDER_RE.match(line)
        if m and m.group(1) == arm:
            return datetime.fromisoformat(m.group(2))
    return None


def logged(spiral_out: str, arm: str) -> tuple[str | None, str | None]:
    """(sha, ref) as actually recorded. The REF decides whether reconstruction
    even applies: an arm built with an explicit VILLA_REF never consulted
    origin/main, so intersecting its render time with the reflog is meaningless.
    Validating the method against a PINNED arm reports a mismatch that is an
    artefact of the check, not of the method -- which is how this was found."""
    sha = ref = None
    for log in Path(spiral_out).glob(f"*{arm}*.log"):
        for line in log.read_text(errors="replace").splitlines():
            if "[setup_workdir] villa" in line and "->" in line:
                head, tail = line.rsplit("->", 1)
                sha = tail.strip()[:9]
                ref = head.split("villa", 1)[1].strip()
    f = Path(spiral_out) / f"work_{arm}" / "VILLA_SHA"
    if sha is None and f.exists():
        sha = f.read_text().strip()[:9]
    return sha, ref


def resolve(moves: list[tuple[datetime, str]], when: datetime) -> tuple[str, str]:
    """The sha origin/main held at `when`, plus the margin to the next move."""
    prior = [(t, s) for t, s in moves if t <= when]
    if not prior:
        return "?", "no reflog entry that old"
    t0, sha = prior[-1]
    later = [t for t, _ in moves if t > when]
    margin = f"held from {t0:%m-%d %H:%M}" + (
        f", next move in {(later[0] - when).total_seconds() / 60:.0f} min"
        if later
        else ""
    )
    return sha[:9], margin


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+")
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument(
        "--villa",
        default="/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa",
    )
    args = ap.parse_args()

    moves = reflog(args.villa)
    print(
        f"origin/main reflog: {len(moves)} moves, "
        f"{moves[0][0]:%Y-%m-%d} to {moves[-1][0]:%Y-%m-%d}\n"
    )
    print(f"{'arm':<14}{'render start':<22}{'sha':<11}{'source':<14}note")

    checked = failed = 0
    for arm in args.arms:
        when = render_start(args.spiral_out, arm)
        truth, ref = logged(args.spiral_out, arm)
        pinned = ref is not None and ref != "origin/main"
        if when is None:
            print(
                f"{arm:<14}{'-':<22}{truth or '?':<11}"
                f"{'logged' if truth else '-':<14}no [render] line in sequence log"
            )
            continue
        sha, note = resolve(moves, when)
        if truth and pinned:
            src, note, sha = "logged (pinned)", f"VILLA_REF={ref}; reflog N/A", truth
        elif truth:
            checked += 1
            ok = truth.startswith(sha) or sha.startswith(truth)
            failed += not ok
            src = "logged+checked" if ok else "MISMATCH"
            note = note if ok else f"reconstructed {sha}, logged {truth}"
            sha = truth
        else:
            src = "reconstructed"
            if "next move in" in note:
                mins = float(note.rsplit("next move in", 1)[1].split()[0])
                if mins < 60:
                    note += "  <-- TIGHT, verify by hand"
        print(f"{arm:<14}{when:%Y-%m-%d %H:%M:%S}     {sha:<11}{src:<14}{note}")

    print()
    if failed:
        print(
            f"METHOD FAILED on {failed}/{checked} arm(s) with a logged SHA. "
            "Do NOT trust the reconstructed rows."
        )
        return 1
    if checked:
        print(
            f"method reproduces all {checked} logged SHA(s); reconstructed rows "
            "carry the same validation."
        )
    else:
        print(
            "no arm with a logged SHA was passed, so nothing validated the method. "
            "Include one that has VILLA_SHA before trusting these."
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
