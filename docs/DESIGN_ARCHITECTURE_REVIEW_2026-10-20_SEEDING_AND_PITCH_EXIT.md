# Design and architecture review — the neural tracer's seeding launcher, and the pitch analysis's exit

Date: 2026-10-20. Baseline: `bb47d1d7` (main after #150).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- **The owner's #149**: `scripts/neural_tracer_seeding.py`, `scripts/neural_tracer_seed_probe.py` and their report. The
  last round merged it without reviewing it. Its proposal (`docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md`)
  is "PROPOSED, not registered, nothing run".
- **Finding 92's analysis `main()`.** Two commits in #150 (`5c48c58f`, `021ff519`) changed it, and #148 changed the
  verdict it calls, with no test running it.

## What changed

- **`neural_tracer_pitch_analysis.main()` exits by its status.**
  - It returned 0 for every status. The chain logs that code (`ANALYSIS rc=…` in
    `repro/fibers/run_neural_tracer_pitch_chain.sh`, which runs without `set -e`), so an INCOMPLETE or IDENTITY_FAILED
    analysis was logged like a good one.
  - It now returns 1 unless OK, as finding 91's analysis does. Nothing else reads the code.
  - Exit 1 also covers a crash; the status line in `analysis.log` tells them apart, as for finding 91.
- **A test runs `main()` end to end**, with ScrollGT's scorer and fiber target and the `.afv` reader stubbed. The stubs
  record what they are given. Every scored cube is at 5.0, against a native 5.0, our tracer at 10.0 and connected
  components at 1.0.
  - **All 21 rows:** OK and exit 0. It checks:
    - the full predictions, the materiality and the in-sample reading;
    - the comparators and the stop reasons;
    - that each cube's fibers reach the rasteriser scaled back to its own frame, at its own size;
    - that the scorer gets the cube's own target and the registered tolerance.
  - **One failed run:** OK, exit 0, the run listed, its row None.
  - **Three failed Scroll-3 runs:** INCOMPLETE, exit 1, P2 unevaluated.
  - **An identity problem:** IDENTITY_FAILED, exit 1, no verdict.
  - **A ScrollGT scoring version other than 3:** refused.

  `monkeypatch` restores every stub, `sys.path` included, since `main()` prepends ScrollGT's `src`. The test kills
  each of these mutants:
  - an exit of 0 for every status;
  - the rule from before `5c48c58f` (INCOMPLETE after any failure);
  - the verdict left out of the output;
  - the tracer and CC comparators swapped;
  - a failed run's row not recorded as None;
  - `scale_back` skipped;
  - the scoring-version refusal removed;
  - the stop reasons dropped.
- **`neural_tracer_seeding` refuses two ways around its checks.**
  - **An abbreviated `--tile-workers`.** argparse expands an unambiguous abbreviation (`--tile-work 4`, `--tile-w=4`),
    which the check for `--tile-workers` did not see. Villa would then have spawned workers that seed with its
    unpatched module, while `seeding.json` recorded the scaled sigma. Abbreviations of `--tile-workers` are now refused.
    A different flag, such as `--tile`, passes through.
  - **A resume of a run villa started on its own.** `record_seeding` refused other scales only once `seeding.json`
    existed. A work directory holding villa's `run.json` but no `seeding.json` was resumed at the new scales and
    stamped with them, though its first tiles were seeded at villa's. It is now refused.
- **Tests for the launcher** (`tests/test_neural_tracer_seeding.py`). The launcher's `main()` had never run under a
  test. Against a stand-in for villa's `volume` module, importable as the launcher imports it, the tests check that:
  - villa's `main` receives the arguments with `--tile-workers 0`;
  - `seeding.json` is written before it runs;
  - the patch is active during it, and undone afterwards, also when villa's run exits with `SystemExit`;
  - a resume at other scales never reaches villa.

  Further tests cover the abbreviations and the plain-villa resume. Each fix's mutant is killed:
  - the abbreviation check removed;
  - the plain-villa resume allowed;
  - the record written after villa runs;
  - the patch restored only on an exception.

## Verified, no change needed

- **`seeding_scaled`** saves villa's module state before its `try`, and restores it in `finally`.
- The smoothing wrapper refuses any smoothing call at a sigma other than villa's 1.0. That catches a change in villa's
  smoothing sigma, but not every change:
  - a second sigma-1.0 call in villa's module would be scaled too;
  - smoothing moved to a direct import would leave the patch doing nothing.

  The proposal's own rule covers both: a cube whose recorded seed dots differ from the probe's is MANIPULATION_FAILED
  and not scored.
- The Hessian radius matches scipy's `int(4σ + 0.5)`.
- **`neural_tracer_seed_probe`** calls villa's `tile_dots` on each cube's presence.
  - The committed `reports/neural_tracer_seed_probe.json` reproduces the seed dots both runs recorded, on all 21 cubes,
    and `tests/test_neural_tracer_seeding.py` pins it. The probe does not check this itself when it runs.
  - Its default work directory is a path on the owner's machine, as in the repository's other research scripts.
- No villa flag used by finding 91's settings or the chains is a prefix of `--smoothing` or `--hessian`, so the
  launcher's own parser takes none of them (independent review).

## Observations for the owner (not changed)

- Finding 92's analysis now differs further from the copy frozen in its work directory, so the chain would refuse to
  resume it. That is harmless, since the run is complete.

## Verification

- `pytest` on the pitch analysis, pitch report, seeding, funnel and filing-number tests: 64 passed, 4 skipped for want
  of the sibling checkouts.
- Ruff, and mypy with `--warn-unused-ignores`, are clean on the changed files, the tests included.
- The standard suite imports none of these modules. On the first commit (`5477185f`) it ran as on main: 2672 passed,
  with the same 42 failures and 2 errors, all environmental.
- **Independent review** of the first commit found nothing blocking. Its should-fix findings:
  - the `main()` test's verdict check did not depend on the comparators or the scorer's inputs;
  - the seeding launcher's `main()` was untested.

  Its nits:
  - the two ways around the launcher's checks;
  - the "fails loudly" claim;
  - the doc's history of `main()`;
  - three unused `type: ignore`s.

  All are addressed above.
