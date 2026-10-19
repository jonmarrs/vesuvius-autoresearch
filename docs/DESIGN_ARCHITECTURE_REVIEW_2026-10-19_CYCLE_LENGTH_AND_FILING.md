# Design and architecture review — the owner's #133 cycle-length analysis and #131 filing month mode

Date: 2026-10-19. Baseline: `b3f61e25` (main after #134).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the two PRs the owner merged on 2026-10-18.
- **#133** added `scripts/cycle_length_gain.py`, the pre-registered comparison of 60- against 15-minute cycles. It
  reads the sprint logs through `scripts/epoch_boundary_overhead.py` (#126), which also fits the loop's per-cycle
  overhead.
- **#131** added `--month` to `scripts/check_filing_upstream_claims.py`, which checks the October filing's
  "#N (merged YYYY-MM-DD)" claims against GitHub.

The pre-registration, the readings, the report's numbers and the filing are the owner's. This review changes none
of them. It fixes three ways the tools could read their inputs wrongly without saying so.

## What changed

- **A cycle the loop logged as `CRASHED (OOM)` was dropped, and its minutes went to the next cycle.**
  - `run_autoresearch_loop.py` heads an out-of-memory crash `## Cycle N: name (CRASHED (OOM))`. The sprint-log
    parser matched the status as `\((\w+)\)`, which that header does not satisfy. So the cycle was skipped, and the
    clock was not advanced past it.
  - The sprint logs in this checkout (to 2026-07-11) hold 325 such headers, against 13,072 `CRASHED` ones.
  - Reproduced, with a day shift `a` at 07:51:00, `batch_size_24 (CRASHED (OOM))` at 07:53:00 and `b` at 08:09:30:
    - main read two cycles, and `b`'s overhead as 210 s, not 90 s;
    - an OOM crash fails in its first minutes, so the error stays under the 600 s at which `epoch_boundary_overhead`
      drops a stretched interval, and the inflated row enters its fit;
    - `cycle_length_gain` counted the arm as 0 crashed, where the pre-registration counts crashed cycles.
  - The parser now reads the status as `CRASHED` with `oom: true`, and advances the clock past it.
  - `epoch_boundary_overhead` no longer pairs an OOM crash with a run killed at the timeout. Unpaired, it would
    have left the killed run's own cycle unpaired.
- **`cycle_length_gain --sprint-logs` read a log twice if two of its names matched it, and ignored a name that
  matched nothing.**
  - Each path the patterns match is read once. A pattern that matches no log exits with "no sprint log matches".
  - Reproduced:
    - a glob plus one log it covers gave that day arm 4 scored cycles, not 2, which narrows its interval;
    - a mistyped log name gave one arm fewer, without a word.
- **`check_filing_upstream_claims --month` took any text.**
  - It is matched as a prefix of each merge's Pacific date. So `--month 2026/10` matched no merge, required no
    claim, and printed PASS over a filing that omits one. Reproduced with #2044.
  - `--month 2026-10-11` required claims for that day's merges only.
  - It must now be `YYYY-MM`, or argparse refuses it with exit 2.
- **Tests**, 10 new cases:
  - `tests/test_epoch_boundary_overhead.py`: the OOM cycle is parsed, and the next cycle's overhead is right; it is
    not paired as a killed run.
  - `tests/test_cycle_length_gain.py`: the OOM cycle is counted as crashed; a log named twice is read once; a name
    that matches nothing is an error.
  - `tests/test_check_filing_upstream_claims.py`: five malformed months are refused.

  With main's scripts, 9 of the 10 fail. The pairing test passes there only because main drops the OOM cycle
  altogether.

## Verified, no change needed

- **The committed cycle-length report is unaffected.**
  - No cycle in its JSON crashed. The gaps between consecutive starts are at most 61.9 minutes at night and 16.8 by
    day, so no OOM crash was dropped between them; one would add its minutes to a gap.
  - The report's numbers come from that JSON, which `tests/test_cycle_length_gain_report.py` binds to the text. This
    change regenerates nothing.
- **The analysis does what the pre-registration says.**
  - It stops at the first promotion and keeps it.
  - It pairs each 60-minute arm with the 15-minute arm beside it, so the replication arm meets the same day arm.
  - It applies the reading fixed in advance (`reading()`, tolerance 0.01).
  - The secondary drops `use_uamt_*` and `batch_size_*` by name.
- **Nothing pulls code into the running loop.** No script runs `git pull`, `fetch` or `reset`. So a merge to main,
  this one or #134, is not the restart onto other code that would stop the replication arm. The owner's pull would
  be.
- **Every Config line carries `batch_size`.** The loop writes the whole config, which the parser's `batch_size`
  lookup needs. Of 16,877 in the local logs, one from before the field existed lacks it.
- **#131's claim pattern and dates.**
  - Dates are taken in Pacific time, so #2044, merged 01:49 UTC on 10-12, is the 11th.
  - A claim about a PR outside our list is looked up.
  - An open PR claimed as merged is stale.
  - The September mode's output is unchanged, as its tests show.

## Observations for the owner (not changed)

- **The epoch-boundary reports cannot be checked here for dropped OOM cycles.** Their JSONs keep only the rows that
  passed the filters, and the October sprint logs are not in this checkout. An OOM crash in their windows would have
  added its minutes to the next cycle's overhead. Re-running `epoch_boundary_overhead.py` on the same logs would show
  whether any row changes.
- **`epoch_boundary_overhead.runs`** raises `StopIteration` on a run log with no protocol-v3 line, and the Welch
  interval divides by zero when both arms have no spread. Neither can happen on the logs these reports read.
- **`--limit 100`** in month mode lists our 100 newest villa PRs. A month's merges are recent, so it covers them
  until we have opened 100 PRs since.

## Verification

Environment: CPython 3.10 venv.

- `pytest` on these modules: 49 passed:
  - the three test files above;
  - `test_cycle_length_gain_report`;
  - `test_loader_epoch_boundary_measured_report`.

  With main's scripts, 9 of the 10 new cases fail.
- The reproductions above, with main's code and with this change.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR. These scripts are not the loop's code, and their tests are outside it.
