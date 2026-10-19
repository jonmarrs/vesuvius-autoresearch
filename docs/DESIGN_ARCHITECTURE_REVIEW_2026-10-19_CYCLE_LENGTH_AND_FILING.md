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
  - **`epoch_boundary_overhead` leaves an OOM crash out of its killed-run pairing, on both sides.** The pairing
    matches 60-minute crashed cycles with the run log's runs that never scored, in order, and only when the counts
    agree.
    - An OOM crash was killed by neither: its cycle is not counted, and nor is its run. The run is the segment where
      the loop's own test, "out of memory", appears.
    - Such a run often logs steps before the traceback: 7 of the 9 in `run.log.old` do.
    - Counted on either side alone, the totals differ and nothing is paired. Counted on both, they could pair the
      wrong runs. The independent review found the run side.
- **`cycle_length_gain --sprint-logs` read a log twice if two of its names matched it, and ignored a name that
  matched nothing.**
  - Each log the patterns match is read once, however it is spelled: a glob, `./name`, an absolute path. Logs are
    compared by real path.
  - A pattern that matches no log exits with "no sprint log matches".
  - A log is read back through `glob.escape`, so a directory such as `logs[1]` still works.
  - Reproduced:
    - a glob plus one log it covers gave that day arm 4 scored cycles, not 2, which narrows its interval;
    - a mistyped log name gave one arm fewer, without a word.
- **`check_filing_upstream_claims --month` took any text.**
  - It is matched as a prefix of each merge's Pacific date. So `--month 2026/10` matched no merge, required no
    claim, and printed PASS over a filing that omits one. Reproduced with #2044.
  - `--month 2026-10-11` required claims for that day's merges only.
  - It must now be `YYYY-MM` in ASCII digits, month 01–12, or argparse refuses it with exit 2, before any `gh`
    call.
  - A well-formed wrong month (`2026-01` for `2026-10`) still requires no claims. The output's
    `live: merged in 2026-01=[]` line shows it.
- **Tests**, 14 new cases:
  - `tests/test_epoch_boundary_overhead.py`:
    - the OOM cycle is parsed, and the next cycle's overhead is right;
    - neither its cycle nor its run, which logged a step, is paired as a killed run.
  - `tests/test_cycle_length_gain.py`:
    - the OOM cycle is counted as crashed;
    - a log named four ways is read once;
    - a log under a directory with glob characters is read;
    - a name that matches nothing is an error.
  - `tests/test_check_filing_upstream_claims.py`:
    - seven malformed months are refused, among them `2026-00` and full-width digits;
    - the command itself exits 2 before calling `gh`.

  With main's scripts, 13 of the 14 fail. The one that passes is the glob-character test: main read each pattern
  as given.

## Verified, no change needed

- **The committed cycle-length report is unaffected, within a bound.**
  - No cycle in its JSON crashed. The gaps between consecutive starts span 16.4–16.8 minutes by day and 61.5–61.9 at
    night.
  - A dropped OOM crash would add its own duration to one gap. So any crash of over about 24 s would show, and none
    does.
  - A shorter one would not. In the local logs, 30% of OOM cycles took 18 s or less, the longest 97 s.
  - The report's numbers come from that JSON, which `tests/test_cycle_length_gain_report.py` binds to the text. This
    change regenerates nothing.
  - A re-run would add `"oom": false` to every cycle. No test compares regenerated output with a committed JSON.
- **The analysis does what the pre-registration says.**
  - It stops at the first promotion and keeps it.
  - It pairs each 60-minute arm with the 15-minute arm beside it, so the replication arm meets the same day arm.
  - It applies the reading fixed in advance (`reading()`, tolerance 0.01).
  - The secondary drops `use_uamt_*` and `batch_size_*` by name.
- **Nothing pulls code into the running loop.** No script pulls into this checkout:
  - the loop's own `git reset -q -- <files>` only unstages;
  - the `git fetch` calls in `watch_villa_upstream.sh` and `check_villa_runner_pr.py` are in `villa/`.

  So a merge to main, this one or #134, is not the restart onto other code that would stop the replication arm. The
  owner's pull would be.
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
- **Two old header forms are still dropped,** and the clock does not advance past them: a tweak name with a space
  (3 headers on 2026-05-17), and `baseline validation (RUNNING)` (2026-03-27). No current tweak name has a space.

## Verification

Environment: CPython 3.10 venv.

- `pytest` on these modules: 63 passed:
  - the three test files above;
  - `test_cycle_length_gain_report`;
  - `test_loader_epoch_boundary_measured_report`;
  - `test_loader_epoch_boundary_report`.

  With main's scripts, 13 of the 14 new cases fail.
- **Mutation check.** Each mutation fails a test:
  - no OOM alternative in the pattern;
  - no OOM exclusion of the cycle, or of the run;
  - paths compared as spelled;
  - no `glob.escape`;
  - no check for a pattern that matches nothing;
  - `\d` digits;
  - month `00`;
  - no `type=month_arg`.
- **Independent review** of the first commit. It found:
  - the run side of the pairing;
  - paths compared as spelled;
  - that `type=month_arg`, `glob.escape` and month `00` were untested;
  - full-width digits;
  - the gap argument's bound;
  - two inexact sentences.

  All are addressed above.
- The reproductions above, with main's code and with this change.
- Ruff and mypy clean on the changed files.
- The standard suite: see the PR. These scripts are not the loop's code, and their tests are outside it.
