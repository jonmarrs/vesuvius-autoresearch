# inkdelta passes all six pre-registered corpus checks

**2026-09-27.** Result of `docs/preregistration/2026-09-27_inkdelta_validation.md`, run by
`scripts/validate_inkdelta.py` (committed at `6d638682` before inkdelta touched any real run).
Tool: `projects/inkdelta` (its own repository; commits f68dd95 and 01a521c there), 19 unit tests.
Full output: `reports/inkdelta_validation.json`.

| # | case | required | got |
|---|---|---|---|
| 1 | `detfit_up1` vs `smp_pub` | INVALID, `STALE_SLICES` | **INVALID**, solely via `STALE_SLICES` on `smp_pub` |
| 2 | finding 62 re-run | NOT RESOLVED, +4.82% [−7.51%, +17.15%] | **NOT RESOLVED, +4.82% [−7.51%, +17.15%]**, exact to 4 d.p. |
| 3 | `detfit_s4` vs `step2_s4`, builds declared differently | INCOMPARABLE | **INCOMPARABLE** |
| 4 | the same pair, undeclared, `--cv 0.074` | NOT RESOLVED plus the build warning | **NOT RESOLVED, +6.45% [−14.06%, +26.96%]**, `SAMPLER_BUILD_UNDECLARED` |
| 5 | deterministic repeats | NOT RESOLVED, \|rel\| < 0.01%, no FAIL | **NOT RESOLVED, +0.00%**, no findings at all |
| 6 | deliberate re-score (`tif_score_pr1905`) | INVALID, `STALE_SLICES` | **INVALID**, `STALE_SLICES` |

**Each verdict was reached for the registered reason**, checked in the JSON and not just from the
verdict string.

## What case 4 shows a loop user

The +6.45% is a *real*, measured effect of the sampler build. From one run per side, at a run-to-run
CV of 0.074, its interval spans −14% to +27%, so the tool reports it as **not resolved**. A loop that
keeps changes on a single-run win would have accepted it as an improvement. It is a build artefact,
and a real effect of that size cannot be told from noise without replicates. That is the practical
case for running this before `keep`.

## One design change after the first validation run

The first pass exposed an over-strict rule that none of the six cases exercised. A scorer field
recorded on only some runs, such as the snapshot, which predates villa #1805 on older scorers, was
treated as a conflicting value, giving INCOMPARABLE. The models may be identical; it is just
unverifiable. It is now a warning (`SCORER_PARTLY_UNVERIFIABLE`), and only conflicting recorded values
make runs incomparable. A unit test was added and the six cases re-run: all still pass. The
registration's table was not edited.

## Limits

* The `detfit_*` and `rpath_*` integrity checks read chain-level logs covering several arms (stated
  in the registration).
* Validation is on one project's corpus and one region. The noise CV it quotes is ours; users should
  measure their own.
* The tool cannot detect which `vc_render_tifxyz` build sampled a run; the user declares it.
