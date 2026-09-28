"""Evidence for reports/control_sensitivity.md (2026-09-27). Which villa tree does the villa-spiral-current copy hold? For every file under
spiral-fitting/, lasagna/, vesuvius/src/ that differs between d8c5f488a and be09a8503,
compare the copy's git blob hash to each tree's blob."""

import hashlib
import json
import subprocess
from pathlib import Path

COPY = Path("/home/jon/openclaw-workspace/Neo-VM/villa-spiral-current")
OLD, NEW = "d8c5f488a", "be09a8503"


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def blob(p: Path):
    if not p.is_file():
        return "absent"
    b = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


cmp = gh(f"repos/ScrollPrize/villa/compare/{OLD}...{NEW}")
print(f"{OLD}..{NEW}: {cmp['ahead_by']} commits, {len(cmp['files'])} files")
counts = {}
for f in cmp["files"]:
    fn = f["filename"]
    if not fn.startswith(("spiral-fitting/", "lasagna/", "vesuvius/src/")):
        continue
    new = f["sha"] if f["status"] != "removed" else "absent"
    o = gh(f"repos/ScrollPrize/villa/contents/{fn}?ref={OLD}")
    old = o["sha"] if o else "absent"
    h = blob(COPY / fn)
    tag = "OLD" if h == old else "NEW" if h == new else "NEITHER"
    counts[tag] = counts.get(tag, 0) + 1
    print(f"{tag:8} {fn}")
print(counts)

# --- per-arm render work dirs
SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
files = []
for f in cmp["files"]:
    fn = f["filename"]
    if fn.startswith(("spiral-fitting/", "lasagna/", "vesuvius/src/")):
        o = gh(f"repos/ScrollPrize/villa/contents/{fn}?ref={OLD}")
        files.append((fn, o["sha"] if o else "absent", f["sha"] if f["status"] != "removed" else "absent"))
arms = sorted(d.name for d in SO.glob("outer_*") if d.is_dir() and d.name.startswith(("outer_curbase", "outer_nosamecur", "outer_anchor10")))
for a in arms:
    c = {}
    for fn, old, new in files:
        h = blob(SO / a / fn)
        t = "OLD" if h == old else "NEW" if h == new else "NEITHER"
        c[t] = c.get(t, 0) + 1
    sha = (SO / a / "VILLA_SHA").read_text().strip() if (SO / a / "VILLA_SHA").is_file() else "-"
    print(f"{a:28} {c}  VILLA_SHA={sha}")
