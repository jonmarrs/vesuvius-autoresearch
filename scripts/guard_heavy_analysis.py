"""Refuse to start a memory-heavy analysis while a render is in flight.

`repro/spiral_render/preflight.sh` has said for weeks that headroom during a
render is about 1 GB and that nothing heavy should be started alongside one. That
warning is prose addressed to a human, and on 2026-09-14 it did not stop a
four-arm volume-map comparison from driving available RAM to 0 GB while
`curbase_s7` was rendering. The render survived on luck; an OOM would have cost a
3-hour fit and a 2-hour render. This turns the warning into a check.

**Detection matches the villa venv interpreter, not a stage name.** Diagnosing that
same near-miss, a check that grepped `cmdline` for `render_ink|run_render` reported
nothing alive while the render was healthy -- the pipeline was in its `lasagna`
flatten stage at the time. Every stage runs the same interpreter, so that is what
is matched. This is the third variant of the pgrep lesson: match something common
to the whole job, not a substring of one phase of it.

Usage, from a script that is about to load several arms:

    ./.venv/bin/python scripts/guard_heavy_analysis.py --need-gb 6 || exit 1

or in Python:  from guard_heavy_analysis import require_headroom
"""

import argparse
import sys
from pathlib import Path

VILLA_VENV_MARK = "villa-spiral/spiral-fitting/.venv"
DEFAULT_NEED_GB = 6.0


def render_in_flight() -> list[tuple[int, str]]:
    """Live villa-venv interpreters, whatever pipeline stage they are in."""
    found = []
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            cmd = (
                (p / "cmdline")
                .read_bytes()
                .replace(b"\0", b" ")
                .decode(errors="replace")
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        if VILLA_VENV_MARK in cmd:
            found.append((int(p.name), cmd.strip()[:70]))
    return found


def free_gb() -> float:
    """MemAvailable, which accounts for reclaimable cache; MemFree does not."""
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1048576
    raise SystemExit("cannot read MemAvailable from /proc/meminfo")


def require_headroom(need_gb: float = DEFAULT_NEED_GB, force: bool = False) -> bool:
    """True if it is safe to proceed. Prints why when it is not."""
    procs = render_in_flight()
    avail = free_gb()
    if not procs:
        print(f"guard: no render in flight, {avail:.1f}G available -- proceeding")
        return True
    print(
        f"guard: RENDER IN FLIGHT ({len(procs)} villa process(es)), "
        f"{avail:.1f}G available, need {need_gb:.1f}G"
    )
    for pid, cmd in procs[:3]:
        print(f"         pid {pid}  {cmd}")
    if avail >= need_gb:
        print("guard: headroom is sufficient -- proceeding, but keep the load small")
        return True
    if force:
        print(
            "guard: OVERRIDDEN with --force. An OOM here costs the render AND the fit."
        )
        return True
    print(
        "guard: REFUSING. Wait for the render to finish, or pass --force if you have\n"
        "       a specific reason and accept losing the in-flight arm."
    )
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--need-gb", type=float, default=DEFAULT_NEED_GB)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    return 0 if require_headroom(args.need_gb, args.force) else 1


if __name__ == "__main__":
    sys.exit(main())
