# The claims auditor was checking one report, and said so in a way that read wider

**2026-09-18.** Tooling, not a finding.

## What it looked like

`audit_report_claims.py` prints `numbers checked against a cited artifact: 58`. That reads as a
property of the repository. It is a property of **one file**: `REPORT` is hardcoded to
`reports/spiral_satisfaction_winding_blindness.md`, of whose 248 blocks 22 cite an artifact. No other
report was examined.

## How it surfaced

Adding JSON artifacts for five new reports left the count at **exactly 58, before and after** —
verified by stashing the artifacts and re-running. That is what exposed it, and it also means a claim
in the commit that added them was wrong: **"the auditor now sees them" was false.** The auditor could
not see them and still cannot bind their numbers. The reproducibility win in that commit was real; the
auditing win was not.

## What changed

* **Repository-wide scope reported.** The tool now audits every report and prints coverage alongside
  its single-report figure: **5 reports citing an artifact of 108, 77 numbers checked, 13 flagged.**
* **A date bug fixed.** `DATE_RE` ended in `\b`, which does not match between `13` and `_`. Every
  registration filename is `2026-09-13_something.md`, so those dates survived and leaked `09` and `13`
  into the number scan — **six of the flags were that and nothing else.** It also made eight reports
  appear to cite an artifact when they were citing a registration.
* **Reports carry their artifact.** The five new mechanism reports now name the JSON they came from
  and the script that regenerates it.

## The 16 previously-invisible flags: all benign

Extending the scope surfaced 16 flags in reports the tool had never read. Reviewed individually:
six were the date-fragment bug; four sit inside a **correction block** in `fiber_connectivity_eval.md`
that names superseded figures deliberately (`"not the 0.686-0.875 quoted below"`); the rest are
derived ratios and a narrative `band 12 of 35`. **No stale claim was found.**

## The limitation left in place, deliberately

The auditor binds numbers **within a block that cites an artifact**. The new reports cite theirs in a
standalone line, so their numbers still are not bound. Making them bind would mean restructuring
reports around the tool's block model.

That is not worth doing, because the stronger guarantee already exists:
`scripts/analyse_placement_mechanism.py` **reproduces every published number exactly**, which is a
better check than string-matching a report against a JSON file. The citation is there for a human
reader.
