# Pre-registration: does inkdelta give the right verdict on this project's own corpus?

**Written 2026-09-27, before inkdelta was run on any real run directory.** Runner:
`scripts/validate_inkdelta.py`, committed with this file. The tool is `projects/inkdelta` 0.1.0 (local
commit f68dd95 in that repository), with 18 unit tests on synthetic villa-layout runs.

## The question

The October plan (option A, chosen by the user) is a checker that tells a villa loop user whether a
`total_fg_pixels` difference is real. Before release it must be right on comparisons whose truth we
already know. Every expected verdict below comes from a registered finding, not from running the tool.

## Cases and required verdicts

| # | A vs B | required | why it is known |
|---|---|---|---|
| 1 | `detfit_up1` vs `smp_pub` | **INVALID**, `STALE_SLICES` on B | `smp_pub` skipped sampling (finding 65 correction) |
| 2 | `detfit_s4..s9` vs `detfit_up1..3`, builds declared equal | **NOT RESOLVED**, interval **+4.82% [−7.51%, +17.15%]** to 4 d.p. | finding 62, registered |
| 3 | `detfit_s4` vs `step2_s4`, builds declared `edge-0513` / `post-1146` | **INCOMPARABLE** | finding 66: the step differs |
| 4 | the same pair, builds undeclared, `--cv 0.074` | **NOT RESOLVED** plus the `SAMPLER_BUILD_UNDECLARED` warning | single runs at CV 0.074 give ±20.5%, wider than the true +6.45% |
| 5 | `rpath_up_a` vs `rpath_up_b` (deterministic repeats), `--cv 0.074` | **NOT RESOLVED**, \|rel\| < 0.01%, no FAIL | finding 64: repeats agree to 0.0002% |
| 6 | `detfit_up1` vs `tif_score_pr1905` | **INVALID**, `STALE_SLICES` on B | that score deliberately re-used existing slices; the tool cannot know intent and must still flag it |

Case 4 is the one a loop user most needs to see. A real, measured +6.45% build effect is *not
resolvable* from one run per side at our noise level. The checker has to say "not resolved", not
invent a win.

## Stated before running

* **Weaker logs.** The `detfit_*` and `rpath_*` renders logged into chain-level logs covering several
  arms (`detfit_chain.log`, `upstream_fitter_chain.log`, `upstream_render_path_chain.log`). A skip in
  any arm would flag all of them, so their integrity check is weaker than for a per-run log.
* **Scorer snapshot unrecorded.** Our pinned scorer predates villa #1805, so no case records it. Every
  run should warn `SCORER_SNAPSHOT_UNRECORDED`; that is correct and not a failure.
* **Rule.** Any case that disagrees with its required verdict fails validation. The tool is then fixed
  and re-validated, with the failure reported, never by editing this table.

## Cost

Seconds on CPU.
