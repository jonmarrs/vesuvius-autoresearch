# Design and architecture review — the owner's #202 and #203

Date: 2026-10-23. Baseline: `e22a8f87` (main after #204; the owner merged #202 and #203 before it).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 14:15, 15:21, 16:13 and 17:13 UTC firings.
- **#202** prepares the October prize filing:
  - concise form answers for the bundle of three merged villa fixes;
  - a final-week plan;
  - a readiness record;
  - a binding for finding 95 in the detailed draft.
- **#203** fixes the fiber downloader's silent skips. #204 took its downloader in place of round 109's.

## What changed

- **A doubled word in the submission text.** The form answer for villa #2044 said stock scoring "was
  OOM-killed 70 seconds in at at least 27.6 GB". It now reads "70 seconds in, at a peak of at least
  27.6 GB", which is what the PR record's "≥ 27.6 GB" means. The owner's test bound the old phrase
  and is updated with it.
  - The answer is now 371 words, not 368. The plan's count is updated and now bound.
- **#202's unbound figures are bound** in `tests/test_october_prize_form_answers.py`:
  - **"Used one RTX 4090" and "under a 26 GiB memory limit"** are the villa #2044 PR record's
    hardware and cgroup.
  - **"The three modes' counts agree within 0.005%"** is computed from that record's three
    w010–w019 counts (221,561, 221,570 and 221,564: 0.0041%).
  - **The draft's readiness note** is the readiness record:
    - "all 19 links in the pre-update draft returned HTTP 200" is its 19 URL checks, every one 200;
    - the plan's "All 19 pre-update links" likewise;
    - the form's title;
    - email and every question required except the optional Discord name.
  - **The plan's word count** is the answer's own.
- **#203's tests left four of its checks unpinned.** Four one-line mutants of the downloader passed
  them:
  - dropping the anchor-tag check, so a page's `<link>` or `<script>` would be fetched;
  - dropping `:` from the name check;
  - dropping the scheme check, so `file:outside.json` would fetch the folder's `outside.json`;
  - dropping DEL from the control characters.

  `tests/test_reference_annotation_downloads.py` gains these cases: an absolute path, an encoded
  colon, a scheme-only link and DEL among the skipped links, and a non-anchor test. All four mutants
  now fail. 14 of 16 downloader mutants fail a test. The two survivors cannot change behaviour:
  - the netloc check is implied by the path-separator check;
  - `"xb"` for `"wb"` cannot matter, because names are a set and the destination is always new.

## Verified, no change needed

- **#202's other figures:**
  - **The three merge dates** are the record's, as the owner's test checks.
  - **"All 31 existing number/version checks"** is the 31 tests that
    `tests/test_filing_2026_10_numbers.py` collected before #202.
  - **"59 passed"** is its four test files. Here they give 55 passed and 4 skipped, the skips being
    the absent sibling repositories.
  - **The memory figures** (70 s, 27.6 GB, 13.8 GB, 1,009 s) are bound by the owner's test.
- **#203's downloader:**
  - it decodes strictly;
  - it fetches each name quoted again;
  - it records every skipped `.json` link with a reason;
  - it does not claim "Downloaded all" when anything was skipped.

## Mutation counts in earlier rounds

The mutant runs here, and in rounds 106, 108 and 109, write each mutant and start a fresh pytest. Python
reuses a module's cached bytecode when the source has the same size and the same mtime second. So
two same-size mutants written within one second can run the first's bytecode, and a survivor can be
reported as killed. This round found one such false kill in its own first run.

Every surviving count is re-run with the cache cleared before each mutant:
- round 106's plane-spacing harness, 22 of 22;
- round 109's probe, 54 of 55;
- this round's downloader, 14 of 16.

Round 108's probe counts were superseded by round 109's.

## Observations for the owner (not changed)

- **The downloader does not follow or record subdirectory links,** and it ignores names ending in
  `.JSON`. Both are silent. Neither is known to occur in the annotator folders.
- **The plan's "59 passed" and "31 existing checks"** describe the readiness run. They are not bound:
  the second is historical, and the first depends on which sibling repositories are present.

## Verification

- Pending.
