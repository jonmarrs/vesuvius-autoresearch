"""Check the filing's claims about upstream state against GitHub, before filing.

`tests/test_filing_numbers_match_sources.py` binds every *figure* in the filing to
a json artifact. The claims about upstream -- how many PRs are merged, how many
issues are open, how many have gone unanswered -- are not figures in artifacts.
They are live GitHub state, and they go stale whenever a maintainer acts or we
open something. Two of them were stale on 2026-09-14: the tally still said "two
merged, two pending" after #1780 was opened, and "five have zero comments" after a
contributor commented on #1655.

**A claim this script cannot locate is an ERROR, never a pass.** If the filing is
reworded so a pattern stops matching, the honest outcome is a loud failure telling
the filer to re-check by hand. Silently passing on text it failed to find is the
same defect as a path an equivalence checker forgot to look at, and that one shipped.

Usage:  ./.venv/bin/python scripts/check_filing_upstream_claims.py
        ... --filing docs/PRIZE_FILING_2026-09_SUBMIT.md
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "ScrollPrize/villa"
AUTHOR = "jonmarrs"
WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def gh(*args: str) -> list[dict]:
    out = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise SystemExit(f"gh failed: {' '.join(args)}\n{out.stderr.strip()}")
    parsed: list[dict] = json.loads(out.stdout)
    return parsed


def word(m: str) -> int:
    return WORDS[m.lower()] if m.lower() in WORDS else int(m)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--filing", default="docs/PRIZE_FILING_2026-09_SUBMIT.md")
    ap.add_argument(
        "--since",
        type=int,
        default=1700,
        help="lowest PR number in scope; the filing describes the spiral-fitting campaign",
    )
    args = ap.parse_args()
    text = Path(args.filing).read_text()

    prs = gh(
        "pr",
        "list",
        "--repo",
        REPO,
        "--author",
        AUTHOR,
        "--state",
        "all",
        "--limit",
        "50",
        "--json",
        "number,state",
    )
    issues = gh(
        "issue",
        "list",
        "--repo",
        REPO,
        "--author",
        AUTHOR,
        "--state",
        "open",
        "--limit",
        "50",
        "--json",
        "number,comments",
    )

    # Scope from LIVE GitHub, never from what the filing happens to mention.
    # Until 2026-09-22 this filtered the live PRs down to the ones already cited
    # in the text, which made every count below circular: a PR the filing left
    # out simply vanished from the check. It passed cleanly on a filing that
    # said "zero pending" while two PRs were open, because neither was cited.
    cited = {int(n) for n in re.findall(r"#(\d{3,5})", text)}
    by_num = {p["number"]: p["state"] for p in prs}
    scope_prs = {n: s for n, s in by_num.items() if n >= args.since}
    merged = sorted(n for n, s in scope_prs.items() if s == "MERGED")
    openpr = sorted(n for n, s in scope_prs.items() if s == "OPEN")
    closedpr = sorted(n for n, s in scope_prs.items() if s == "CLOSED")
    uncited = sorted(n for n in scope_prs if n not in cited)
    n_open_iss = len(issues)
    n_silent = sum(1 for i in issues if len(i["comments"]) == 0)

    print(
        f"live: in-scope PRs (>= {args.since}) merged={merged} open={openpr} closed={closedpr}"
    )
    print(f"live: open issues={n_open_iss}, of which zero-comment={n_silent}\n")

    checks: list[tuple[str, bool, str]] = []
    unlocatable: list[str] = []

    def claim(name: str, pattern: str, expect) -> None:
        m = re.search(pattern, text, re.I)
        if not m:
            unlocatable.append(name)
            return
        got = tuple(word(g) for g in m.groups())
        exp = expect if isinstance(expect, tuple) else (expect,)
        checks.append((name, got == exp, f"filing says {got}, live is {exp}"))

    claim(
        "merged/pending tally",
        r"(\w+) merged fixes?, (\w+) awaiting review, (\w+) (?:auto-)?closed",
        (len(merged), len(openpr), len(closedpr)),
    )
    checks.append(
        (
            "every live PR is cited",
            not uncited,
            f"in-scope PRs missing from the filing: {uncited}",
        )
    )
    claim(
        "total PRs vs merged",
        r"This is (\w+) PRs against a merged total of (\w+)",
        (len(scope_prs), len(merged)),
    )
    claim(
        "open issues and silence",
        r"(\w+) villa issues are open from us and (\w+) have\s+zero comments",
        (n_open_iss, n_silent),
    )

    for num, state in sorted(scope_prs.items()):
        row = re.search(rf"\|\s*\**#{num}\**\s*\|\s*\**([A-Za-z]+)\**", text)
        if not row:
            unlocatable.append(f"table row for #{num}")
            continue
        said = row.group(1).upper()
        checks.append(
            (f"#{num} row", said == state, f"filing says {said}, live is {state}")
        )

    bad = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"  {'ok  ' if ok else 'STALE'} {name:<28} {'' if ok else detail}")
    for name in unlocatable:
        print(f"  ERROR could not locate claim: {name}")

    if unlocatable:
        print(
            "\nFAIL: a claim could not be located. The filing may have been "
            "reworded; re-check those by hand. Not treated as a pass."
        )
        return 2
    if bad:
        print(f"\nFAIL: {len(bad)} claim(s) stale. Update the filing before pasting.")
        return 1
    print("\nPASS: every upstream claim in the filing matches GitHub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
