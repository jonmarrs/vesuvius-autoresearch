"""Record the state of our open villa PRs, the upstream facts the November draft's #2501 entry quotes, and the
orientation issue's replies, read with `gh` (read-only GitHub API calls). tests/test_november_prize_draft.py binds
the draft to the record.

usage: python3 -I scripts/record_villa_open_prs.py reports/evidence/villa_open_prs_YYYY-MM-DD.json
"""

import datetime as dt
import json
import re
import subprocess
import sys

REPO = "ScrollPrize/villa"


def gh(*args: str) -> dict:
    return json.loads(
        subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    )


def line_with(text: str, needle: str) -> str:
    hits = [ln.strip() for ln in text.splitlines() if needle in ln]
    if len(hits) != 1:
        raise SystemExit(f"{needle!r}: {len(hits)} lines")
    return hits[0]


def main(out: str) -> None:
    checked = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    prs = {}
    for n in (2463, 2465, 2501):
        p = gh(
            "pr",
            "view",
            str(n),
            "-R",
            REPO,
            "--json",
            "number,title,state,mergedAt,createdAt,author,comments",
        )
        reviews = [c for c in p["comments"] if c["author"]["login"] == "villa-review"]
        rec = [c for c in reviews if "I recommend merging." in c["body"]]
        prs[str(n)] = {
            "title": p["title"],
            "state": p["state"],
            "merged_at": p["mergedAt"],
            "created_at": p["createdAt"],
            "author": p["author"]["login"],
            "villa_review_recommends_merging_at": rec[-1]["createdAt"] if rec else None,
        }
    body = gh("pr", "view", "2501", "-R", REPO, "--json", "body")["body"]
    review = [
        c["body"]
        for c in gh("pr", "view", "2501", "-R", REPO, "--json", "comments")["comments"]
        if c["author"]["login"] == "villa-review"
    ][-1]
    issue = gh("issue", "view", "2107", "-R", REPO, "--json", "title,author,state")
    prior = gh("pr", "view", "2256", "-R", REPO, "--json", "author,state,closedAt")
    upstream = gh(
        "issue",
        "view",
        "2",
        "-R",
        "Nieuwlaar/pherc343-first-letters",
        "--json",
        "state,comments,createdAt",
    )
    pooled = {}
    for label in (
        "Same-index 4×4 mean, median of the 17 slices",
        "4-deep pool, median of the 17 slices",
    ):
        pooled[label] = float(
            re.search(r"\|\s*([0-9.]+)\s*\|\s*$", line_with(body, label)).group(1)
        )
    record = {
        "checked_at_utc": checked.isoformat().replace("+00:00", "Z"),
        "how": "scripts/record_villa_open_prs.py: gh pr view / gh issue view (read-only)",
        "prs": prs,
        "pr_2501": {
            "recomputed_level2_chunk_correlations": pooled,
            "reporter_auc_line": line_with(
                body, "The issue reporter reported an ink_9um AUC"
            ),
            "credit_line": line_with(body, "for the pixel evidence"),
            "review_port_and_renderer_line": line_with(review, "This PR ports"),
        },
        "orientation_issue": {
            "url": "https://github.com/Nieuwlaar/pherc343-first-letters/issues/2",
            **{k: (len(v) if k == "comments" else v) for k, v in upstream.items()},
        },
        "issue_2107": {
            "title": issue["title"],
            "author": issue["author"]["login"],
            "state": issue["state"],
        },
        "pr_2256": {
            "author": prior["author"]["login"],
            "author_name": prior["author"].get("name"),
            "state": prior["state"],
            "closed_at": prior["closedAt"],
        },
    }
    with open(out, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
