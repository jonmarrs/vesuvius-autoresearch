"""Before filing, check the month's form against villa's Progress Prize rollovers.

villa's `scrollprize.org/docs/34_prizes.md` links one form, and an automated PR,
"Progress Prize rollover YYYY-MM", replaces that link and the deadline with the
next month's. #2301 opened 2026-10-25, six days before October's deadline. If a
rollover merges before filing, the page links a form for the next month, and
the filing-day step "re-read the form URL at current upstream" leads there.

This records every rollover PR (when it opened and merged, and the deadline and
form it put in), then fetches the form being filed and the form of every rollover
still open. The form being filed must have the expected title, answer HTTP 200,
contain a response form and not redirect to `/closedform`; anything else exits
1. This checks the public page; the filer must still sign in and save a receipt.

Usage: python3 scripts/check_prize_form_rollover.py --form <URL> --expected-title 'October 2026 Progress Prizes' [--out record.json]
"""

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlsplit

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


class FormPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = []
        self.has_response_form = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag == "form":
            action = dict(attrs).get("action") or ""
            self.has_response_form |= urlsplit(action).path.endswith("/formResponse")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)


def form(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", "replace")
        status, final = response.status, response.geturl()
    page = FormPage()
    page.feed(html)
    return {
        "url": url,
        "http_status": status,
        "final_url": final,
        "title": "".join(page.title).strip() or None,
        "has_response_form": page.has_response_form,
        "accepting_responses": status == 200
        and not urlsplit(final).path.rstrip("/").endswith("/closedform")
        and page.has_response_form,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--form", required=True, help="the form for the month being filed")
    ap.add_argument(
        "--expected-title", required=True,
        help="exact title of the intended month's form",
    )
    ap.add_argument("--out", help="write the record here (default: stdout)")
    args = ap.parse_args()
    if not args.expected_title.strip():
        ap.error("--expected-title must not be empty")

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
        "expected_form_title": args.expected_title,
        "rollover_prs": rows,
        "filing_form": form(args.form),
        "open_rollover_forms": {
            str(row["number"]): form(row["form_after"]) for row in pending
        },
    }
    record["filing_form_title_matches"] = (
        record["filing_form"]["title"] == args.expected_title
    )
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
    if not record["filing_form_title_matches"]:
        print(f"Unexpected form title; expected {args.expected_title!r}", file=sys.stderr)
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
    ready = filing["accepting_responses"] and record["filing_form_title_matches"]
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
