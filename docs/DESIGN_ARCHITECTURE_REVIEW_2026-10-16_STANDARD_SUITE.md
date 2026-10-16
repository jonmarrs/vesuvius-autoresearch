# Design and architecture review — what the standard suite runs

Date: 2026-10-16. Baseline: `8e2d4b9a` (main after #89). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- the test suite that the owner's and these reviews' validation runs use, `scripts/run_validation_tests.py`'s
  `VALIDATION_TESTS`;
- the 213 of 285 test modules outside it, and why they fail where they fail;
- `scripts/evaluate_villa_metrics.py`, which one of them runs.

## What changed

- **The standard suite runs every test of code the loop runs.** 40 test modules that test it were outside
  `VALIDATION_TESTS`; none had ever been listed. Among them are the tests of:
  - the promotion criterion (`test_improvement_criterion`, `test_f1_improvement_criterion`);
  - the promotion metric's computation (`val_f1`, in `vesuvius_autoresearch.detector.metrics`:
    `test_detector_metrics`);
  - the prize gates (`test_prize_promotion_gates`);
  - the Frangi target and its torch filter;
  - the ridge channel's `fibers.detection`;
  - the loader workers, the topology threshold, the augmentations and the clDice loss;
  - the model builders (`vesuvius_model`);
  - the evidence chain's reports, and the handoff's first step (`audit_villa_upstream`).

  So a change to any of these, validated against the list, was not tested by them. All 40 pass here, apart from
  three skips for absent dependencies: the LeJEPA checkpoint, villa's `ink-detection`, and `wandb`.
- **A guard keeps it so.** `tests/test_validation_suite_covers_the_loop.py`, itself in the list, computes the
  loop's code from its entry points:
  - the loop and `loop_control`;
  - `train.py` (the training run and its `--smoke` preflight) and `predict.py` (the benchmark);
  - `smoke_test.py`;
  - the scripts that share the loop's lock;
  - the post-sprint handoff and each script its steps run.

  It follows their imports through the repo, then fails, naming them, when a test module that imports any of that
  code is not listed.
  - **Counting rule.** An import counts the module it uses, not the packages it only loads on the way:
    - `train.py`'s `from vesuvius_autoresearch.detector.metrics import …` runs `metrics.py` and only loads
      `detector/__init__`, so the detector's own training and inference tests are not required;
    - the loader's `from vesuvius_autoresearch.fibers import detect_ridges` uses `fibers/__init__` and the
      `detection` it re-exports.
  - **Other checks.** It fails when an entry point is missing, or when the list names a missing file or a module
    twice. It checks that the loop's code includes, for example, `promotion.py`, `detector.metrics` and
    `fibers.detection`, but not `detector.infer`. It also checks how it reads `import` forms: `import train`,
    `from scripts.training.train import …`, an import inside a function, `from package import name` and
    `from package import submodule`.
- **`test_wandb_tracking`'s end-to-end test skips without `wandb`, and `test_resnet3d_decoder` without villa's
  `ink-detection`,** instead of failing.
- **`evaluate_villa_metrics.py` reports what it can, and stops only without its core metrics.**
  - It imported all of villa's metrics in one block, printed any failure, and went on. Both volumes were read,
    then the first metric failed with a `NameError`.
  - `critical_components_multiclass` needs `cupy` (a GPU), so on a CPU host that block lost every metric.
  - It now stops, with the import error, only when dice, centerline Dice or connected components do not import.
    The other metrics (multiclass critical components, multiclass Dice, mean AP, skeleton distance) are imported one
    by one and reported as unavailable, as a metric that fails to compute already was.
  - It finds villa from its own checkout, not the working directory. An unused import (`critical_components`) is
    gone.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **The standard suite left out 40 modules testing code the loop runs**, among them the promotion criterion, the promotion metric, the prize gates and the Frangi target. The list is kept by hand, and nothing checked it. | Listed, and guarded. With main's list the guard's first test names the 40. |
| P4 | `evaluate_villa_metrics.py` lost every metric when one optional metric's dependency was missing, and then failed on a `NameError` after reading both volumes. It found villa from the working directory. | Core metrics required, the others optional; villa found from the checkout. Tests: a missing core metric stops before the volumes are read; a missing optional metric leaves the others reported; the skeleton distance runs from outside the checkout. All three fail on main; the third now passes on a CPU host. |

## Review of the PR, and what it changed

The independent review of the PR's first head (`071b149d`) found nothing blocking. It confirmed:
- the 28 modules first added pass in any order and leave nothing in the checkout;
- the 72 modules listed before give identical results, test for test.

| Finding | Outcome |
| --- | --- |
| The guard matched a hand-written list of module names, which left out code `train.py` imports: `detector.metrics` (val_f1), `vesuvius_model`, `scroll_augmentations`, `cldice_loss`, `wandb_tracking`, `pixel_auc`, the loader's `fibers` package, and the handoff's `audit_villa_upstream`. Twelve modules testing them were still outside. Its self-test called `from vesuvius_autoresearch.fibers import trace` not loop code, though that loads `detection`. | The guard computes the loop's code from its entry points, by file. The twelve are listed. `test_wandb_tracking`'s end-to-end test and `test_resnet3d_decoder` skip without their dependency. |
| `evaluate_villa_metrics.py`'s new exit applied to every metric. Only `critical_components_multiclass` needs `cupy`, and `main()` already treats it as optional. | Core metrics required, the rest optional (above). |
| The doc's run of "the modules still outside" was main's 213, not the 185 then outside, and some of its causes were wrong. | Re-run on the 173 now outside (below). |
| The guard put `scripts/` first on `sys.path`; its glob was not recursive; it read files as text. | `from scripts import run_validation_tests`; `rglob`; bytes. |
| The doc said the modules were added after the list was last kept by hand (it was edited on 2026-10-15, and the modules are older); "about two minutes"; that some of the 28 import `loop_control` or an inference script (none does). | Corrected. |
| The new metrics test could not fail on its `NameError` assertion (it gave no volumes) and did not test the villa path. | Rewritten, with volumes and from outside the checkout. |

## The modules still outside the suite

Running at this commit; recorded in the next.

The rest are research analyses and probes (`analyse_*`, `probe_*`, `audit_*`), the detector's and the fibers'
own subsystems, and the documentation guards that pre-commit runs on its own.

## Observations for the owner (not changed)

- **The guard reads import statements.** It does not see code a test runs as a subprocess or loads by path. For
  example, `test_villa_baselines_launchers` runs the launchers the action matrix names, and loads
  `launch_neural_tracing.py` with `spec_from_file_location`. So it is not required, and not added: it fails twice
  here for the LeJEPA checkpoint and villa's GP-winner config, and writes `scripts/_finetune_lejepa_runner.py` (an
  ignored file) into the checkout.
- **The entry points are listed by hand** in the guard. A new script the loop or the handoff starts belongs there.
- **`test_correlate_geometry_ink.py` runs its script on a host path** (`/home/jon/…/spiral_out`), and fails where
  that is absent rather than skipping.
- **Earlier reviews' recorded counts are not comparable.** The validation runs they record describe the list as it
  stood; from this change on, "passed" includes the 40 modules' tests.

## Reviewed and sound

- **No module was outside the list because it fails.** The 40 pass here, apart from the three skips above, and the
  failures outside the list are all environmental.
- **No false positives today.** A bare `import train` is the training script only. The other `train` modules are
  imported by package path (`vesuvius_autoresearch.detector.train`). The tests use no relative imports.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `e4032512` (#89), whose tree is `8e2d4b9a`'s but for its review doc's result
  lines. With the old list it was 42 failed, 2240 passed, 15 skipped, 1 xfailed, 2 errors in 2 min 37 s. The
  failures and errors are environmental: no scroll data, no CUDA, no villa data files.
- Branch, first head (`071b149d`, 29 modules added): 42 failed, 2371 passed, 19 skipped, 1 xfailed, 2 errors in
  3 min 31 s. Same set; the 131 extra passes and 4 extra skips are the added modules' tests.
- Branch, after the PR review's fixes: running at this commit; recorded in the next.
- Ruff (check and format) and mypy on the changed files: clean.

New tests:
- `tests/test_validation_suite_covers_the_loop.py`:
  - `test_every_test_of_the_loops_code_is_in_the_standard_suite` (with main's list it names the 40);
  - `test_the_entry_points_exist_and_reach_the_loops_modules`;
  - `test_the_standard_suite_names_only_existing_modules`;
  - `test_the_guard_reads_the_ways_tests_import`.
- `tests/test_evaluate_villa_metrics.py`, each failing on main:
  - `test_a_missing_required_metric_stops_before_reading_the_volumes`;
  - `test_a_missing_optional_metric_leaves_the_others_reported`;
  - `test_skeleton_distance_is_reported_without_a_wandb_run`, now run from outside the checkout (on main it fails
    here for `cupy`).

Not verified here: the enlarged suite on the GPU host.
