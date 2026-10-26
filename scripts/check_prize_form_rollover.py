"""Before filing, check the month's form against villa's Progress Prize rollovers.

villa's `scrollprize.org/docs/34_prizes.md` links one form, and an automated PR,
"Progress Prize rollover YYYY-MM", replaces that link and the deadline with the
next month's. #2301 opened 2026-10-25, six days before October's deadline. If a
rollover merges before filing, the page links a form for the next month, and
the filing-day step "re-read the form URL at current upstream" leads there.

This records every rollover PR (when it opened and merged, and the deadline and
form it put in), then fetches the form being filed and the form of every rollover
still open. The form being filed must answer HTTP 200 and not redirect to
`/closedform`; anything else exits 1, and the filer checks the page by hand.

Usage:  python3 scripts/check_prize_form_rollover.py --form <the month's form URL> [--out record.json]
"""

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request

REPO = "ScrollPrize/villa"
TITLE = re.compile(r"^Progress Prize rollover \d{4}-\d{2}$")
DEADLINE = re.compile(r"next deadline is (.*?)!")
FORM = re.compile(r"\[Submission Form\]\((.*?)\)")


def gh(*args):
    return subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True
    ).stdout


def first(lines, pattern):
    return next(
        (m.group(1) for line in lines for m in [pattern.search(line)] if m), None
    )


def rollover(number):
    pr = json.loads(
        gh(
            "pr",
            "view",
            str(number),
            "-R",
            REPO,
            "--json",
            "number,state,createdAt,mergedAt,mergedBy,title,url",
        )
    )
    diff = gh("pr", "diff", str(number), "-R", REPO).splitlines()
    added = [
        line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")
    ]
    removed = [
        line[1:] for line in diff if line.startswith("-") and not line.startswith("---")
    ]
    return {
        "number": pr["number"],
        "url": pr["url"],
        "title": pr["title"],
        "state": pr["state"],
        "created_at": pr["createdAt"],
        "merged_at": pr["mergedAt"],
        "merged_by": (pr.get("mergedBy") or {}).get("login"),
        "deadline_before": first(removed, DEADLINE),
        "deadline_after": first(added, DEADLINE),
        "form_before": first(removed, FORM),
        "form_after": first(added, FORM),
    }


def form(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", "replace")
        status, final = response.status, response.geturl()
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    return {
        "url": url,
        "http_status": status,
        "final_url": final,
        "title": title.group(1).strip() if title else None,
        "accepting_responses": status == 200
        and not final.split("?")[0].endswith("/closedform"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--form", required=True, help="the form for the month being filed")
    ap.add_argument("--out", help="write the record here (default: stdout)")
    args = ap.parse_args()

    found = json.loads(
        gh(
            "search",
            "prs",
            "--repo",
            REPO,
            "Progress Prize rollover",
            "--limit",
            "100",
            "--json",
            "number,title",
        )
    )
    numbers = sorted(row["number"] for row in found if TITLE.match(row["title"]))
    rows = [rollover(n) for n in numbers]
    pending = [row for row in rows if row["state"] == "OPEN"]
    record = {
        "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(
            timespec="seconds"
        ),
        "repository": REPO,
        "path": "scrollprize.org/docs/34_prizes.md",
        "rollover_prs": rows,
        "filing_form": form(args.form),
        "open_rollover_forms": {
            str(row["number"]): form(row["form_after"]) for row in pending
        },
    }
    text = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)

    filing = record["filing_form"]
    print(
        f"{filing['title']!r}: accepting responses = {filing['accepting_responses']}",
        file=sys.stderr,
    )
    for row in pending:
        print(
            f"villa #{row['number']} OPEN: would link {row['form_after']}",
            file=sys.stderr,
        )
    merged_away = [
        row for row in rows if row["merged_at"] and row["form_before"] == args.form
    ]
    for row in merged_away:
        print(
            f"villa #{row['number']} MERGED {row['merged_at']}: the page no longer links this form",
            file=sys.stderr,
        )
    return 0 if filing["accepting_responses"] else 1


if __name__ == "__main__":
    sys.exit(main())
