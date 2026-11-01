# October 2026 Progress Prize — filed engineering entry

**Submitted by the owner; verified by the Google Forms response receipt.**
The emailed copy is dated **October 29, 2026 at 9:40:33 p.m. Pacific**
(**October 30 at 04:40:33 UTC**), before the October 31, 11:59 p.m. Pacific
deadline. This is the receipt generation/delivery time; the receipt supplies
no separate form-submission timestamp or response ID.

The entry bundles the three October Villa merges **#2022, #2044 and #2155**.
All received answer fields match the prepared entry after CRLF-to-LF
normalization and trimming surrounding whitespace; paragraph boundaries are
preserved. The contribution answer is **371 words**. The terms response was
verified as agreed, and the requested emailed copy was received.

The [redacted filing record](../reports/evidence/october_prize_submission_2026-10-30.json)
retains the receipt times, public submitted fields, validation results and
hashes of the preserved receipt and text. The original email, submitted
personal fields and nine-file receipt archive are retained privately; email
addresses, account details and receipt message IDs are excluded here.

The [separate research entry](PRIZE_FILING_2026-10_RESEARCH_FORM_ANSWERS.md)
remains unsubmitted in this workflow. Earlier readiness snapshots and the
[frozen engineering preparation](PRIZE_FILING_2026-10_FORM_ANSWERS.md) remain
unchanged records of preparation; this file records the completed engineering
filing. No duplicate response or response edit was made for this record.
Villa #2141 and #2259 merged on October 30, after this response, and were
filed on October 31 as a [second response](PRIZE_FILING_2026-10_SECOND_SUBMITTED.md)
that names this one.

## URL field as received

```text
https://github.com/ScrollPrize/villa/pull/2022
https://github.com/ScrollPrize/villa/pull/2044
https://github.com/ScrollPrize/villa/pull/2155
https://github.com/jonmarrs/vesuvius-autoresearch
```

## Contribution as received

```text
(1) Which scroll data. PHerc. Paris 4 / Scroll 1, using Villa's published spiral-fitting data and ink scorer, including the outer w120–w129 strip and a smaller w010–w019 strip. The measured scorer runs used one RTX 4090.

(2) How this helps people read the scrolls. Three fixes merged into Villa this month make the existing spiral-fitting workflow usable and reproducible:

- #2022 (merged 2026-10-11): correct the autoresearch runner instructions to use the shipped CLI's flags. The old instructions failed to launch and could silently drop a requested configuration change or GPU selection.
- #2044 (merged 2026-10-11 Pacific): add opt-in --sequential-folds and average fold probabilities in place. On the real outer strip, stock scoring was OOM-killed 70 seconds in, at a peak of at least 27.6 GB; sequential scoring completed at 13.8 GB in 1,009 seconds under a 26 GiB memory limit. It allows that strip to be scored on the tested workstation without changing the scoring method.
- #2155 (merged 2026-10-21): fix the spiral-fitting README's NVIDIA pip command to install --group cuda. The old command installed neither track extraction backend on Linux x86-64; the corrected command selects the CUDA dependencies already used by the documented uv route.

(3) What this enables. Users can launch the documented runner with the intended variant and devices, score a large outer-winding strip within the measured memory limit, and install the GPU track-extraction dependencies by following the pip instructions. Sequential folds are optional and slower; the default concurrency is preserved.

(4) Evidence. The three linked PRs contain the reproduction commands and before/after evidence. #2022 checked the runner's generated commands and environment with its expensive subprocesses stubbed. #2044 ran the actual scorer on published scroll data: on the smaller strip, the three modes' counts agree within 0.005%, consistent with measured run-to-run variation. The averaging step itself was checked for bit-identical output; that is not a claim that the complete GPU scorer is deterministic. #2155 verified package selection with pip dry runs rather than claiming a new extraction benchmark.

The public Autoresearch repository preserves the patches and measurement records. The upstream fixes are released in Villa under its existing license. These changes use published models and data and introduce no new trained model or dataset requiring a separate release.
```
