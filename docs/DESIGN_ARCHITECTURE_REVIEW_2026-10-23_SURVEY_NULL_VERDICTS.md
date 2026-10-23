# Design and architecture review — the manipulation survey called its nulls bounded by their MDE

Date: 2026-10-23. Baseline: `faa32e40` (main after #205).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 18:13 UTC firing. Main has not moved since #205, and there are no open pull
requests. Rounds 106 and 107 recorded this as an observation; this round fixes it.

## What changed

- **The survey's verdict quoted the design MDE as what a null bounds.**
  - `scripts/survey_manipulation_effects.py` labelled every non-significant study
    "null, bounds X%", where X is the design MDE. Its docstring said a null "always reads 'no effect
    larger than X'", and its closing printout said "Every null is a bound".
  - The MDE is what the design could reliably see. What a null's data rule out is its 95% CI. For the
    two pinned ink nulls that is [−18.4%, +16.7%] and [−20.7%, +13.1%], beside an 11.8% MDE.
  - #192 and #195 made this correction in the summary, README and FINDINGS, and round 107 put it in
    the withdrawn-claims ledger. That ledger reads only Markdown, so the generator and its JSON kept
    the old label.
  - **The verdict is now one function, `verdict()`.** It returns IMPROVED or HARMED at α, and
    otherwise "null", which is what the report's own table already said. The docstring and
    printout now state the distinction.
- **`reports/manipulation_effects_survey.json`'s five null labels** are rewritten from each row's
  own recorded p and effect by that function. The data come from arms on the owner's machine, so the
  script cannot be re-run here. Only the five `verdict` strings change; every number is
  byte-identical.
- **The report's table is now bound to the JSON.** `reports/no_lever_has_improved_reading.md` typed
  its table from the survey, and nothing read it back. `tests/test_manipulation_survey.py` checks
  every row against the JSON and the script's study list:
  - the arm counts, effect, p, CI and MDE, as printed;
  - the verdict.
- **The report said "the loosest of them admits an 18% gain".** No null admits that: the largest gain
  any interval allows is +16.7%, the top of patch bootstrap's interval. 18% was about its
  half-width. A dated note says so, and the figure is bound.

## Verified, no change needed

- **Nothing read the old label.** The three headline tests that read this JSON use its `mde`, `lo`,
  `hi` and `rel` fields, never `verdict`.
- **The report's own table and its "The nulls are not equal" section** already distinguished the MDE
  from the CI.

## Observations for the owner (not changed)

- **The survey cannot be re-run here.** Its `--spiral-out` default is the owner's machine path. The
  relabelled JSON is what the corrected script would write from the same arms, but that is not
  checked by a run.

## Verification

- **New tests:** 3 passed.
  - Each of seven perturbations fails a test: four table figures, the HARMED verdict, the noted
    16.7%, and a JSON verdict.
  - So does restoring one "null, bounds 12%" label, whose 12% is the design MDE.
- **Neighbours:** the ledger, the suite coverage guard, the three headline-number tests that read
  the survey, and the arm-tier test give 135 passed.
- **Ruff** 0.9.10 `check` and `format` are clean on the script and the new test.
- **Doc guards:** 378 passed and 2 skipped on main `faa32e40` and on the branch.
- **Doc audit:** the branch gains no entries.
- **The standard suite** with the locked-package overlay: 2813 passed, 22 skipped and 1 xfailed, as on
  main. The ten failures are main's ten environmental ones: nine need villa files, one is
  `gp_winner`. The new test exercises a report script, not the loop's code, so it sits outside the
  suite; the suite coverage guard agrees.
- **No independent review this round.** The change is one label rule, a relabelled artifact, a
  dated note and a binding test, each checked by perturbation.
