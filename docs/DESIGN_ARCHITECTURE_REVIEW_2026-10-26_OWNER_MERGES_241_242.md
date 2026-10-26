# Design and architecture review — the owner's #241 (October form rollover) and #242 (seed-heading resume guard)

Date: 2026-10-26. Baseline: `c6dbc4c3` (main after the owner's #241 and #242).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 11:24 UTC firing. The 04:12–10:15 firings found main unmoved after #240.
- **#241** warns that villa's automated rollover PR, #2301, would make the prize page link November's form before
  October's deadline. It adds `scripts/check_prize_form_rollover.py`, which checks the October form before filing.
- **#242** adds a second villa patch to the seed-heading draft. `repro/fibers/villa_volume_seed_resume.patch` records
  the seed-selection rule in `run.json`, so a resume refuses tiles made under the old 35° rule. #242 also records an
  October 26 review of the three open villa PRs.

## What changed

- **The form checker crashed on the pages it was meant to reject.**
  - `form()` called `urllib.request.urlopen`, which raises on a 4xx or 5xx status rather than returning it.
  - #241's test fed `form()` a 503 response object and expected "not accepting". The real call never returns one, so
    a 503 or 404 ended the check with a traceback before it wrote its record.
  - An unreachable host did the same. So did an open rollover whose diff names no form: `form(None)` failed inside
    `urllib`.
  - `form()` now records each of these as not accepting, with the status or the reason. The filing form alone still
    decides the exit code, and a page that cannot be read is never "accepting".
  - `tests/test_check_prize_form_rollover.py` adds five cases: an HTTPError 503 with a page, a 404, an unreachable
    host, a timeout, and an open rollover without a form link. All five fail against #241's checker.
- **The doc audit could fetch into villa/.**
  - `scripts/audit_doc_references.py` asks villa/ whether it holds a cited commit, with `git cat-file -e`.
  - In a partial clone, git answers a missing object by fetching it from the promisor remote. This container's
    villa/ is one (`remote.origin.promisor`, `blob:none`). `GIT_TRACE` shows the call spawning
    `git fetch origin … --filter=blob:none --stdin` to GitHub.
  - This round's audit did exactly that. It wrote villa main's 322cb0899, and a commit from the jonmarrs/villa fork,
    into villa/'s object store. Audits until then had listed 322cb0899 as resolving nowhere. Afterwards they read it
    as villa's.
  - The audit's answer, and so `tests/test_audit_doc_references.py`, depended on the network and on whether the
    fetch beat the 30 s timeout.
  - `_git_env()`, which every git call in the audit uses, now sets `GIT_NO_LAZY_FETCH=1`; this git (2.43) honours it.
  - A new test builds a local server and a `blob:none` clone, then makes a commit only the server has. With the guard,
    the audit does not find that commit, and nothing is fetched. A control without the guard fetches it. Against
    main's audit, the test fails.
- **Three of the new Python files were not ruff clean.**
  - #241's checker and its test, and #242's changes to `tests/test_villa_draft_volume_seed_heading.py`, would all be
    reformatted by `ruff format`. The checker's test also failed `ruff check` on import order (I001).
  - Pre-commit would stop the next commit that touched them. They are now clean under the pinned ruff 0.9.10.
  - `tests/test_audit_doc_references.py`, which this round edits, was already not `ruff format` clean on main. It is
    formatted too.

## Verified, no change needed

- **#242's guard works through villa's own check.** At the pin, `main()` refuses a resume when any recorded setting
  outside the speed-only and derived lists differs from the saved `run.json` (`old.get(k) != record[k]`).
  - A saved record without `seed_heading_selection` reads `None`, so it is refused, and so is one naming another
    rule.
  - The check runs before `Owned` and `load_done`, so no finished tile is loaded first.
  - The owner's test applies both patches in order to the pinned villa, and checks that `_seed_heading` is
    unchanged by the second.
- **#242's counts.** "All 23 cases pass" is the 9 heading cases, the 3 resume cases and the 11 performance cases.
- **#241's rollover note is the record.** The evidence JSON's merge times put #1235, #1623 and #1947 after their
  months' deadlines. #1194, merged by GitHub Actions, landed on 07-21 before July's. The owner's test computes the
  dates and the November form's closed state from the JSON.

## Observations for the owner (not changed)

- **Two doc-audit entries from #242.** Neither is a villa commit that a villa checkout at our pin holds, and no test
  fails.
  - The villa PR review record backticks #2141's head, 19575a45.
  - The seed-heading draft backticks the jonmarrs/villa fork branch's head, d1de9ec1 in full. Only the audit here
    misses it, because the fetch described above brought it into this container's villa/.
- **This container's villa/ now holds two commits it did not before**: villa main's 322cb0899 and the fork's head.
  Audits here now read them as villa's, so this round's audit counts are not like-for-like with earlier rounds' for
  those two. The audit's path checks do not use git, and the live-documents list is unchanged.
- **Not checkable here:**
  - villa's PRs and rollover history, the Google Forms pages and the jonmarrs/villa fork branch, which are outside
    this session's scope;
  - the resume regressions, which need villa's tracer environment.

## Verification

- **Tests:**
  - before this change, #241 and #242's tests, with the filing, research-answer and suite-guard tests, gave 75 passed
    and 4 skipped;
  - after it, the checker and villa-draft tests give 24 passed;
  - against #241's checker, the five new cases fail.
- **Doc guards, the withdrawn-claims ledger, the suite guard, and the filing, form-answer, research-answer,
  rollover-checker, villa-draft and loop-tweak tests:** 540 passed and 6 skipped.
  - The one failure is `test_live_documents_stay_clean`, which lists villa paths absent from this container's villa
    checkout.
  - Its list is the same as on main.
- **The audit tests** give 12 passed with the guard, plus the standing failure. The new partial-clone test fails
  against main's audit.
- **Ruff** 0.9.10 `check` and `format` are clean on the five Python files this round touches.
- **No independent review this round.** The change is two functions' environment and error handling, their tests
  and formatting.
