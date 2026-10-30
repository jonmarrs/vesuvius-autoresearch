# Design and architecture review — the owner's #297 and #298 (streaming CLI on public CT, October filing)

Date: 2026-10-30. Baseline: `62905f3a` (main after #298).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 01:12–05:12 UTC firings. I reviewed both PRs myself; they are records, JSON and one
verification script.
- **#297** runs the fiber filter CLI before and after #295's streaming change on one public Scroll-1 CT cube on
  CPU, and records a fresh October readiness snapshot.
- **#298** records the filed October engineering entry: a document of the received answers and a redacted JSON
  record that binds them to the private receipt by hash.

## What changed

- **The filed entry is bound to its record and to the frozen preparation**
  (`tests/test_october_prize_submission_record.py`).
  - Nothing tied #298's document of the received answers to its record, or either to the prepared entry the
    record says they match.
  - The new test checks that:
    - the document's URL and contribution blocks are the record's public fields;
    - the record's two text hashes are the hashes of those fields;
    - the fields are the frozen preparation as typed into the form (one line per paragraph or list item,
      without emphasis or code marks), at 371 words;
    - the preparation is still its recorded bytes;
    - the receipt time, the deadline and the filed document's quoted times agree.
  - Changing one word in either document fails the matching check. It passes on #298's records: there was no
    discrepancy to fix.

## Verified, no change needed

- **#297's evidence is what the report says.**
  - Every figure in `reports/fiber_cli_public_ct_cpu_2026-10-30.md` matches its JSON record:
    - peak RSS 589.8 against 472.7 MiB (ridges) and 576.3 against 472.9 MiB (vesselness), 19.8% and 17.9%
      lower, which the report gives as about 18–20%;
    - the four wall times;
    - identical output hashes for each filter;
    - `success` and `source_and_inputs_unchanged` both true, from source `ebf29aab`.
  - The raw archive's hash and its 16 members' hashes match the record.
  - The archived harness is the committed `repro/fibers/verify_filter_cli_public_ct.py`, and the archived
    historical CLI is `f2efeda9`'s `cli.py`. The archive's `report.json` agrees with the record field by field.
  - The historical CLI imports only `vesuvius_autoresearch.fibers` and its `detection` module. Both are
    byte-identical between `f2efeda9` and the measured source, so it ran with the same filter math.
- **#297's script.**
  - Each CLI runs under its own measuring wrapper, so the wrapper's `RUSAGE_CHILDREN` peak is that CLI's alone.
  - The 4 GiB address-space limit applies to the CLI.
  - Comparisons pair each filter's historical and streaming runs.
  - An output directory inside the checkout or containing the input is refused. The exit code is 0 only when
    both pairs are byte-identical and the sources and inputs are unchanged.
  - Ruff and mypy are clean on it.
- **#297's readiness snapshot.** The plan's figures match the snapshot JSON: the form check (HTTP 200, the
  expected title, accepting responses) at 03:19:15 UTC, the deadline (October 31, 23:59 PDT = November 1,
  06:59 UTC), the archive with every member checked, and "91 passed". Its two test commands here give 86
  passed and 5 skipped, and 58 passed. The 5 skips need the ScrollGT, inkdelta and inkagree checkouts beside
  this repository.
- **#298's record.**
  - The record's contribution and URL hashes are the hashes of its public fields (LF, one trailing newline).
  - The document shows exactly those fields, and the contribution has 371 words.
  - The receipt's UTC and Pacific times are the same instant (04:40:33 UTC, 21:40:33 PDT), before the deadline.
  - Both prepared answer documents still have the bytes the record and the October 28 source commit give.
  - The filed contribution is not the prepared markdown verbatim: it is that markdown without bold and code
    marks, one line per paragraph or list item. That rendering matches it exactly. The record says the
    answers match "the prepared entry" without saying which copy; the October 28 copy-ready archive it names
    is not committed.

## Observations for the owner (not changed)

- **The October 28 copy-ready archive is not in the repository.** The record names it as the preparation, so
  its match with the received answers cannot be rechecked here. The new test checks them against the committed
  markdown instead.
- **#297's wall times are single unflushed observations.** The report says so, and the conclusions are limited
  to output parity and peak RSS.

## Verification

- **The new test** gives 4 passed, and fails when either document is edited.
- **#297's filing and engineering test commands** give 86 passed and 5 skipped (the sibling checkouts), and 58
  passed.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on the new script and test. Mypy is clean over the
  whole repository (842 files).
- **The standard suite** gives the same 43 failures as before, from `s3fs`, `numba`, `jsonschema` and Villa
  files absent here. The same 2 modules cannot be collected (`tensorstore`, `s3fs`).
- **The doc audit** finds no new unresolved reference. `test_live_documents_stay_clean` lists the same 20 Villa
  and model paths as before.
