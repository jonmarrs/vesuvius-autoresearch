"""Sample a running render's working set, so the next study can predict the wall.

2026-09-15: `curbase_s8`'s render needs a **32.8 G working set** (23.6 G resident +
9.3 G paged out) on a box with 31.3 G of RAM. It therefore pages continuously: band
intervals went 6, 9, 3, 5, then **29** minutes, and the renderer's own ETA moved from
183 to 329 minutes and kept moving. Swap keeps it alive -- `curbase_s7` was OOM-killed
three times without it -- but swap buys survival, not speed.

The discriminator is NOT band count, which was the obvious first guess and is wrong:
`s6` rendered fine with 36 bands, `s7` died with 35, `s8` has 37. It is the working
set, which varies with the mesh extents a fit happens to produce.

**Nothing currently records that number**, so whether an arm's render will fit is
discovered two hours into it. This samples RSS + swap of the live render against
wall-clock and band number, appending one line a minute. Read-only, one /proc read
per sample, safe to run alongside a render that is already thrashing.

With a few arms logged, "will this fit" becomes answerable from the meshes before a
3-hour fit is spent on an arm whose render cannot run at a usable speed.

  setsid nohup ./.venv/bin/python scripts/sample_render_footprint.py \
      --out /path/spiral_out/render_footprint.tsv >/dev/null 2>&1 & disown
"""

import argparse
import re
import sys
import time
from pathlib import Path

BAND_RE = re.compile(r"band (\d+)/(\d+)")


def render_pid() -> int | None:
    """The containerised band renderer, by executable -- every stage shares it."""
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            if (p / "comm").read_text().strip().startswith("vc_render_tifxy"):
                return int(p.name)
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
    return None


def footprint(pid: int) -> tuple[float, float] | None:
    """(resident GB, swapped GB). Both, because resident alone FALLS as a render
    thrashes harder -- reading it alone would suggest memory pressure easing."""
    try:
        rss = swap = 0
        for line in (Path("/proc") / str(pid) / "status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1])
            elif line.startswith("VmSwap:"):
                swap = int(line.split()[1])
        return rss / 1048576, swap / 1048576
    except (
        FileNotFoundError,
        PermissionError,
        ProcessLookupError,
        OSError,
        ValueError,
    ):
        return None


def current_band(log: Path | None) -> str:
    if not log or not log.exists():
        return ""
    try:
        text = log.read_text(errors="replace").replace("\r", "\n")
    except OSError:
        return ""
    hits = BAND_RE.findall(text)
    return f"{hits[-1][0]}/{hits[-1][1]}" if hits else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--log", default=None, help="render log, to tag samples with a band"
    )
    ap.add_argument("--interval", type=float, default=60.0)
    ap.add_argument("--max-hours", type=float, default=48.0)
    # EACH BAND SPAWNS A FRESH vc_render_tifxyz, so there are gaps of seconds to
    # minutes with no such process while a render is perfectly healthy. The first
    # version exited on the first gap and silently stopped collecting 41 minutes
    # into an 88-minute render -- the failure looked exactly like success.
    ap.add_argument(
        "--gone-for",
        type=int,
        default=15,
        help="consecutive absent samples before concluding the render "
        "has finished (default 15, i.e. 15 min at the 60s interval)",
    )
    args = ap.parse_args()

    out = Path(args.out)
    log = Path(args.log) if args.log else None
    if not out.exists():
        out.write_text("iso\tpid\telapsed_s\trss_gb\tswap_gb\tworking_gb\tband\n")

    start = time.time()
    seen = False
    missing = 0
    while time.time() - start < args.max_hours * 3600:
        pid = render_pid()
        if pid is None:
            missing += 1
            # Only conclude the render is over after a RUN of absences: a single
            # gap is the normal handover between bands.
            if seen and missing >= args.gone_for:
                print(f"no renderer for {missing} samples; sampler exiting")
                return 0
        else:
            seen = True
            missing = 0
            fp = footprint(pid)
            if fp:
                rss, swp = fp
                with out.open("a") as f:
                    f.write(
                        f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{pid}\t"
                        f"{time.time() - start:.0f}\t{rss:.2f}\t{swp:.2f}\t"
                        f"{rss + swp:.2f}\t{current_band(log)}\n"
                    )
        time.sleep(args.interval)
    print("max-hours reached; sampler exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
