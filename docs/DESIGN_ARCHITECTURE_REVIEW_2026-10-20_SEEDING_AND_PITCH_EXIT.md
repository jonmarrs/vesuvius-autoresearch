# Design and architecture review — the neural tracer's seeding launcher, and the pitch analysis's exit

Date: 2026-10-20. Baseline: `bb47d1d7` (main after #150).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the owner's #149 (`scripts/neural_tracer_seeding.py`, `scripts/neural_tracer_seed_probe.py`, and their
report), which the last round merged without reviewing. Then finding 92's analysis `main()`, which three rounds have
now changed (#148, #150) without a test running it.

## What changed

- **`neural_tracer_pitch_analysis.main()` exits by its status.**
  - It returned 0 for every status. The chain logs that code (`ANALYSIS rc=…` in
    `repro/fibers/run_neural_tracer_pitch_chain.sh`), so an INCOMPLETE or IDENTITY_FAILED analysis was logged like a
    good one.
  - Finding 91's analysis returns 1 unless OK; this one now does the same. Nothing branches on the code: the chain only
    logs it.
- **A test runs `main()` end to end.** It stubs ScrollGT's scorer, the fiber target and the `.afv` reader, with every
  scored cube at 5.0 against a native 5.0 and our tracer's 10.0. Four cases:
  - all 21 rows: OK, exit 0, and a verdict;
  - one failed run: OK, exit 0, the run listed in `failed_runs`;
  - three failed Scroll-3 runs: INCOMPLETE, exit 1, P2 unevaluated;
  - an identity problem: IDENTITY_FAILED, exit 1, no verdict.

  `monkeypatch` restores every stub, `sys.path` included, since `main()` prepends ScrollGT's `src`. The test kills
  each of these mutants: an exit of 0 for every status; the parent's status rule (INCOMPLETE after any failure)
  restored inside `main()`; and the verdict left out of the output.

## Verified, no change needed

- **`neural_tracer_seeding.seeding_scaled`** patches villa's `volume` module only for the length of a `with` block,
  and restores it in a `finally`:
  - its `ndimage` is wrapped so the presence smoothing runs at the requested sigma;
  - with a Hessian scale given, its Hessian sigma, radius and kernels are set.

  The wrapper refuses a smoothing call at any sigma but villa's 1.0, so a change in villa's code fails loudly.
  `split_argv` forces `--tile-workers 0` (spawned workers would import the module unpatched) and refuses any other
  value. `record_seeding` refuses a resume at other scales.
- **`neural_tracer_seed_probe`** calls villa's `tile_dots` on each cube's presence. Its docstring requires the run's
  own settings to reproduce the seed dots each run recorded. The committed `reports/neural_tracer_seed_probe.json` does,
  on all 21 cubes of both runs, and `tests/test_neural_tracer_seeding.py` pins it.
- Its default work directory is a path on the owner's machine, as in the repository's other research scripts.

## Verification

- `pytest` on the pitch analysis, pitch report, seeding, funnel and filing-number tests: 62 passed, 4 skipped for want
  of the sibling checkouts.
- Ruff and mypy clean on the changed files, the test included.
- The standard suite does not import these modules: see the PR.
