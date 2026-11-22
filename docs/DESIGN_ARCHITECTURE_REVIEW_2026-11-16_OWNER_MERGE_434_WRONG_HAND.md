# Design and architecture review — the owner's #434, finding 116's wrong-direction control

Date: 2026-11-16. Baseline: `20ed3e4` (main after round #175's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 22:12 UTC firing on 2026-11-16. Main had not moved.

It takes **#434**, merged at 05:54 UTC on 11-16. #434 is finding 116, a control on the sheet-following score that
findings 112, 114 and 115 decided by. PHerc. 0826's band was fitted as in finding 115, with the spiral declared to
turn the other way from the published direction. The registration asked whether the score would fail that fit.
The decision is `SCORE_BLIND_TO_DIRECTION`: the wrong-direction fit scored as well as the right one.

#434 added no script. Its fit ran through the launcher's `otherhand` arm, which round #175 tested, and its score
through the band scripts, which rounds #171 and #174 tested. The registered table lives in the report test, as
`registered_verdict`. This round recomputed the decision and tested that table.

## What changed

### Finding 116's table is held at its lines (`tests/test_first_letters_0826_wrong_hand_control_report.py`)

The record's `E`, 0.0992, is far from both lines, so this round made 7 mutants of `registered_verdict`. The report
test's 12 tests killed none of them. One new test function (8 cases) kills all 7:
- an `E` of exactly 0.03 separates, and 0.0301 partly separates;
- 0.0699 partly separates, and exactly 0.07 is blind to direction;
- 60 scored windings are enough, and 59 do not run;
- a step that exited 1, or was killed by a signal, does not run.

No code changed.

## Verified, no change needed

- **The decision recomputes from the record.** All three steps exited 0 and 70 windings were scored in each fit.
  The wrong-direction fit's median excess is 0.0992, above the line of 0.07, so `SCORE_BLIND_TO_DIRECTION`. The
  right-direction fit of finding 115 scored 0.1026.
- **Under finding 112's table the same fit would earn `ON_SHEETS`.** `verdict` on the record gives it, with 56 of
  70 windings positive. The right-direction fit earned `PARTLY_ON_SHEETS`, with 55.
- **The loss prediction held.** The track term at step 29,800 is 181.6 against the right direction's 171.1, 6.1%
  higher, within the registered 25%.
- **The order of events.** The registration and the launcher's `otherhand` arms were committed together (8b8b348,
  06:32 PST on 11-15) and the results at 17:38 PST (27f2c6b). Nothing in `repro/first_letters/eligible_band/`
  changed between the two or since. Eight minutes after the results, c3126cc added a fit-to-fit comparison to the
  record. It adds 102 lines and changes none, and the report marks it as unregistered.
- **The strategy carries the registered consequence.** It says that `ON_SHEETS` and `PARTLY_ON_SHEETS` in findings
  112 and 115 mean "near predicted sheets, locally", and that no further band is read for ink on this score alone
  until a second instrument is registered.
- **The report keeps its own reading apart.** It argues, marked as not registered, that a First Letters read needs
  the surface right locally more than the direction of the turns. It leaves to the owner whether to read further
  bands on the score alone until the second instrument exists.

## Observations for the owner (not changed)

- **The report test counts scored windings in the full fit only.** The registered row is "fewer than 60 windings
  are scored". Finding 112's verdict script applies it to the smoke fit as well. Here both fits had 70, so the
  verdict is the same either way.
- **`registered_verdict` would raise on a step with no record.** The band verdict command records a missing gate
  file as `None`, and `step["exit"]` then fails. All three records are present here.
- **Two launcher and verdict problems from earlier rounds are still open.**
  - `band_fit_verdict.py` fails on a full fit with no scored winding (rounds #171, #173, #174 and #175).
  - `run_fit.sh` goes on to the fit when its settings snippet fails (round #175).
  Both are unchanged on `20ed3e4`.

## Verification

- **The touched module.** `test_first_letters_0826_wrong_hand_control_report.py` gives 20 passed, against 12 on
  `20ed3e4`.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, 1,020 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 226 modules give the same 234 failing ids as round #175's run.
- **The test modules outside the suite.** The 262 modules give the same 23 failing ids as round #175's run, and
  2,678 passed.
- **The doc audit**, run alone, lists the same unresolved references as on `20ed3e4`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every failing id is this container's: it has no villa checkout.

## A note on this round's work

- **Finding 116 was checked from its record, not rerun.** The run needs the scan, villa's fit and a GPU.
- **The fit-to-fit comparison was not recomputed.** It needs the windings, which are on the owner's machine.
- **Not reviewed in #434:** the report beyond its verdict, comparison and consequences, and the edits to
  `docs/RESEARCH_STRATEGY.md` beyond the consequence.
- **Still not reviewed:** #433, #435, #436, #437 and #443, #422, #424 and #428, the rest of #390, #396 and #411, and
  the parts of #421 and #423 that rounds #170 and #171 listed.
