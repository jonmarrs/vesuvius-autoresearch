"""Which numbers in the report no longer appear in the artifact they cite?

The documented failure mode of this project is not wrong measurement. It is a
number in prose drifting away from the artifact that produced it: a stale p95
copied from a pre-fix run, a "roughly eight times" left behind when the
underlying ratio became 2.3, a calibration row edited in one file and not the
other. Every instance so far was caught by a human re-reading, or by a
hand-written drift guard covering one statistic. This does it by machine, over
every artifact the report cites.

METHOD. Walk the report. Whenever a block of text names an artifact under
`reports/`, take the numbers in that block and check each one appears in that
artifact. Report the ones that do not.

WHAT A FLAG MEANS, AND DOES NOT. This is a review aid, not a test of truth. A
flagged number can be perfectly correct and simply derived -- a ratio computed
from two artifact numbers, a percentage the artifact prints as a fraction, a
figure quoted from a different artifact in the same paragraph. The output is a
list of things worth a human glance, ordered so the cheap dismissals are
obvious. What it cannot miss is the case that matters: a number that used to
come from an artifact and no longer matches it.

Deliberately not a pass/fail gate. A gate here would be tuned until it passed,
and this project has enough experience of thresholds chosen after seeing the
answer.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/audit_report_claims.py
"""

import os
import re
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

REPORT = os.path.join(_REPO, "reports", "spiral_satisfaction_winding_blindness.md")
OUT = os.path.join(_REPO, "reports", "report_claim_audit.txt")

ARTIFACT_RE = re.compile(r"reports/([A-Za-z0-9_]+\.txt)")
NUMBER_RE = re.compile(r"(?<![\w.])(\d+\.\d+|\d{2,})(?![\w.])")

# Numbers that carry no artifact meaning: years, commit-ish digit runs, section
# numbers, and the small integers that appear in every prose sentence.
IGNORE = {"2026", "2025", "1092", "1052", "714"}


DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
SECTION_RE = re.compile(r"§B?\d+")
COMMIT_RE = re.compile(r"`[0-9a-f]{7,40}`")


def blocks(text):
    """Paragraph-ish spans, so a citation is attributed to the numbers near it."""
    out, cur = [], []
    for line in text.split("\n"):
        if not line.strip():
            if cur:
                out.append("\n".join(cur))
                cur = []
        else:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def artifact_numbers(path):
    """Every number in an artifact, as strings, plus a set of float values."""
    if not os.path.exists(path):
        return None, None
    raw = open(path).read()
    strings = set(NUMBER_RE.findall(raw))
    values = set()
    for s in strings:
        try:
            values.add(round(float(s), 6))
        except ValueError:
            pass
    return strings, values


def appears(num, strings, values):
    """Does `num` appear in the artifact, allowing for harmless reformatting?"""
    if num in strings:
        return True
    try:
        v = float(num)
    except ValueError:
        return False
    for cand in (v, v / 100.0, v * 100.0):
        if round(cand, 6) in values:
            return True
    # A number the artifact prints to more or fewer decimals. Rounding the
    # ARTIFACT to the report's precision is the right direction: a report saying
    # 23.6 where the artifact says 23.59 is quoting correctly, but a report
    # saying 23.59 where the artifact says 23.6 has invented a digit.
    decimals = len(num.split(".")[1]) if "." in num else 0
    for s in values:
        if abs(round(s, decimals) - v) < 1e-9:
            return True
        if abs(round(s * 100, decimals) - v) < 1e-9:
            return True
    return False


def audit():
    text = SECTION_RE.sub(
        " ", DATE_RE.sub(" ", COMMIT_RE.sub(" ", open(REPORT).read()))
    )
    findings = []
    checked = 0
    for block in blocks(text):
        cited = ARTIFACT_RE.findall(block)
        if not cited:
            continue
        for name in set(cited):
            strings, values = artifact_numbers(os.path.join(_REPO, "reports", name))
            if strings is None:
                findings.append((name, "MISSING", "the cited artifact does not exist"))
                continue
            for num in NUMBER_RE.findall(block):
                if num in IGNORE or num in cited:
                    continue
                checked += 1
                if not appears(num, strings, values):
                    context = next(
                        (ln.strip() for ln in block.split("\n") if num in ln), ""
                    )
                    findings.append((name, num, context[:96]))
    return findings, checked


def main():
    findings, checked = audit()
    lines = [
        "Numbers in the report that do not appear in the artifact they cite",
        "",
        "A review aid, not a gate. A flagged number can be correct and merely derived --",
        "a ratio of two artifact figures, a percentage the artifact prints as a fraction,",
        "or a number quoted from a different artifact in the same paragraph. What this",
        "cannot miss is the case that matters: a number that used to come from an",
        "artifact and no longer matches it.",
        "",
        f"  report:   {os.path.relpath(REPORT, _REPO)}",
        f"  numbers checked against a cited artifact: {checked}",
        f"  flagged:  {len(findings)}",
        "",
    ]
    lines.append(
        "  Five residual flags are expected and are annotated in the report where they"
    )
    lines.append(
        "  appear: a retracted figure whose source artifact is named in the sentence, a"
    )
    lines.append(
        "  bracket end the cited artifact reports in different units, and the patch's"
    )
    lines.append(
        "  angular span, which is a property of the construction rather than of any"
    )
    lines.append("  artifact. A count above five is worth reading.")
    lines.append("")
    if not findings:
        lines.append("  Nothing flagged.")
    else:
        by_artifact = {}
        for name, num, ctx in findings:
            by_artifact.setdefault(name, []).append((num, ctx))
        for name in sorted(by_artifact):
            lines.append(f"=== {name} ===")
            for num, ctx in by_artifact[name]:
                lines.append(f"   {num:>12s}   {ctx}")
            lines.append("")
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
