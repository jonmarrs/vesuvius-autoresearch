#!/usr/bin/env python3
"""Rewrite reports/villa_pr_state.json from the GitHub API.

The prize filing states how many of our villa PRs merged, are pending and were
auto-closed. Those counts drift every time upstream acts, and on 2026-09-22 the
submit-ready text still read "zero pending" while #1842 had been open for three
days. tests/test_filing_pr_counts_match_gh.py binds the prose to this artifact,
so refresh it before filing and let the tests say whether the text still holds.

Note what the artifact deliberately records: ``reviews`` and ``comments_human``
are 0 for every PR here, the four merged ones included. villa merges without a
review record, so neither field separates "ignored" from "accepted", and citing
reviews==0 as evidence of neglect is a mistake this file exists to prevent.

    python scripts/refresh_villa_pr_state.py [--repo ScrollPrize/villa] [--since 1700]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_OUT = _REPO / "reports/villa_pr_state.json"
_BOTS = {"vercel", "github-actions"}


def _gh(args: list[str]) -> object:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"gh failed: {' '.join(args)}\n{r.stderr.strip()}")
    return json.loads(r.stdout)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="ScrollPrize/villa")
    ap.add_argument(
        "--since",
        type=int,
        default=1700,
        help="lowest PR number to include (the campaign the filing describes)",
    )
    a = ap.parse_args()

    listing = _gh(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            a.repo,
            "--author",
            "@me",
            "--state",
            "all",
            "--limit",
            "200",
            "--json",
            "number",
        ]
    )
    nums = sorted(p["number"] for p in listing if p["number"] >= a.since)
    if not nums:
        sys.exit(f"no PRs >= {a.since} found for @me on {a.repo}")

    prs: dict[str, dict] = {}
    for n in nums:
        d = _gh(
            [
                "gh",
                "pr",
                "view",
                str(n),
                "--repo",
                a.repo,
                "--json",
                "number,state,mergedAt,createdAt,title,reviews,comments",
            ]
        )
        human = [c for c in d["comments"] if c["author"]["login"] not in _BOTS]
        prs[str(n)] = {
            "state": d["state"],
            "mergedAt": d["mergedAt"],
            "createdAt": d["createdAt"],
            "reviews": len(d["reviews"]),
            "comments_total": len(d["comments"]),
            "comments_human": len(human),
            "title": d["title"],
        }

    by = lambda st: sorted(int(k) for k, v in prs.items() if v["state"] == st)  # noqa: E731
    out = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": f"gh pr view --repo {a.repo} (per PR)",
        "scope": f"PRs numbered >= {a.since} (the spiral-fitting campaign the filing describes)",
        "caveat": (
            "reviews==0 and comments_human==0 hold for ALL of these, INCLUDING the ones that "
            "merged. villa merges without a review record, so neither field distinguishes "
            "'never looked at' from 'accepted'. The only discriminator is who closed it: a "
            "maintainer merge vs the 14-day inactivity bot. Do not cite reviews:0 as evidence."
        ),
        "total": len(prs),
        "merged": by("MERGED"),
        "open": by("OPEN"),
        "closed_unmerged": by("CLOSED"),
        "prs": prs,
    }
    out["n_merged"] = len(out["merged"])
    out["n_open"] = len(out["open"])
    out["n_closed_unmerged"] = len(out["closed_unmerged"])
    _OUT.write_text(json.dumps(out, indent=2) + "\n")

    print(f"wrote {_OUT.relative_to(_REPO)}")
    print(f"  total={out['total']}  merged={out['n_merged']} {out['merged']}")
    print(
        f"  open={out['n_open']} {out['open']}  closed_unmerged={out['n_closed_unmerged']} {out['closed_unmerged']}"
    )
    if any(v["reviews"] for v in prs.values()):
        print(
            "  NOTE: a PR now carries a review record; the negative check in the tests assumes none do"
        )


if __name__ == "__main__":
    main()
