# Research operations and strategy review — October 28, 2026

Reviewed the loop's process ownership, handoff execution, configuration and
label resolution, operator entry points, local artifact checks and research
strategy. The starting public main was `6cb1c53faacc2fa507a06dca353908c4858134a9`.
Implementation and CPU verification used a separate checkout. No live study
measurements were read and no GPU experiment was launched or deployed.

## Findings and changes

1. **Module-launched training escaped process detection.** A process started
   with `python -m scripts.training.train` was not found by `unsupervised_runs`,
   although it can write the same checkpoint and result files as a path-launched
   trainer. A harmless module sleeper reproduced the missed PID and absent
   refusal. Detection now parses the interpreter's module entry point, keeping
   script arguments and `python -c` separate. Both trainer modules receive the
   existing orphan/hand-started behavior and checkout isolation.
2. **GPU handoff checks did not reserve the checkout.** A successful initial
   process scan allowed a later watchdog restart to launch training during the
   handoff. GPU execution now retains the research lock through supervised
   execution and cleanup. The local lock and orphan guard cannot be bypassed by
   `--force`. Non-GPU preflight keeps its planning behavior. The lock protects
   cooperating work in this checkout; the existing cross-checkout process scan
   is an observation, not a host-wide GPU reservation.
   Review additionally reproduced a report-path alias that released the POSIX
   lock and a cross-checkout scan missing module-launched trainers. Report paths
   aliasing the lock (directly, by symlink or hard link) are now rejected before
   opening it, and the scan includes both trainer module names. Shell launchers
   no longer count as competing work, while real Python research ancestors
   remain visible.
3. **Setup diagnosis required too much knowledge of the implementation.** A
   background launcher PID does not show whether data or configuration are
   usable. The new standard-library-only `workspace_status.py` reports local
   setup blockers, process IDs and watchdog pause state without loading model
   weights or research arrays. It deliberately records training readiness as
   unchecked. Human and JSON interfaces share the same report and exit codes.
4. **Label selection was coupled to heavyweight imports.** The status tool
   needs the trainer's actual refined/pseudo-label priority. Those three
   existing path helpers moved unchanged into `scripts/training/input_paths.py`;
   the old modules re-export them. This avoids a second label-selection policy
   while keeping NumPy, Torch and training imports out of setup inspection.
5. **Local policy was misrepresented as official eligibility.** Strategy docs
   still treated a 64-pixel window as a current prize rule and used it to rule
   out research. Current official rules explicitly permit larger windows with
   evidence against hallucination. Docs and diagnostic messages now distinguish
   the local recipe from official eligibility. Artifact reports label their
   scope and leave prize eligibility unassessed. Runtime numerical thresholds,
   existing models and registered experiments retain their contracts.
6. **The front-page baseline label was wrong.** The legacy detector's measured
   ROC AUC 0.518 was called an all-positive floor. The README and strategy now
   identify the constant predictor's 0.500 floor separately. Measured model
   scores and historical source artifacts are unchanged.

## Architecture and user experience

Keep three boundaries explicit: read-only observations, locked execution and
scientific conclusions. A status snapshot cannot grant permission to use the
GPU; an execution lock cannot establish valid measurements; a local artifact
check cannot establish prize eligibility. The existing supervisor and shared
configuration are reused rather than adding a second execution framework.

The [status guide](WORKSPACE_STATUS.md) provides commands, exit meanings and
next steps. The README now leads with current priorities and setup inspection;
the [short roadmap](research_plan.md) points to one current
[sourced strategy](RESEARCH_STRATEGY.md). The strategy ranks usable upstream
fixes, conservative fiber continuity, reviewed labels and controlled cross-scroll
adaptation, with explicit pilot budgets and stopping conditions for one 4090.
It distinguishes released results, proposals and unverified native integration.

The process checks remain Linux-specific. Filesystem status does not validate
array contents, checkpoint compatibility, dependencies or GPU memory. Work
outside the checkout's lock protocol still requires scheduling coordination.
Registered studies should continue from their pinned code; merging these fixes
does not deploy them into a live research checkout.

## Verification

The PR test report records exact commands and captured outcomes. Regression
tests use real isolated CPU processes to verify module detection, checkout
locking and child cleanup. Status tests forbid heavy imports and verify that
fixture bytes and modification times remain unchanged. Existing training-data,
validation, artifact, filing and headline checks cover the helper extraction
and policy clarification. The standard suite now includes the new process and
status regressions and the previously omitted unchanged-control reader tests.
Smoke checks exercise model construction and CPU checkpoint loading; missing
real training data and the unavailable augmentation import are disclosed skips.

An independent review checked process argument boundaries, unchanged helper
semantics and diagnostic scope. Its usability fixes made watchdog pause state
and process IDs visible in the human output as well as JSON. Current upstream
research recommendations were checked against pinned official rules and open
issues/PRs; no upstream contribution or prize submission was made by this review.

### Captured local checks

The temporary Python 3.10 environment `/tmp/vesuvius-review-env` exposes the
already cached dependencies. No packages were downloaded. All commands below
ran in the review checkout with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''`, plus
`VILLA_ROOT=/workspace/pr229-review-fixtures/villa`,
`SCROLLGT_ROOT=/workspace/pr229-review-fixtures/scrollgt` and
`AGENTS_AGENT_MODE=1` for pytest.

```sh
/tmp/vesuvius-review-env/bin/python -m pytest -q -rs \
  tests/test_workspace_status.py tests/test_loop_control_modules.py \
  tests/test_loop_lifecycle.py tests/test_post_sprint_villa_handoff.py \
  tests/test_training_data_sources.py tests/test_detector_config.py \
  tests/test_prize_promotion_gates.py tests/test_prize_readiness.py \
  tests/test_submission_contracts.py tests/test_readme_headline_numbers.py \
  tests/test_validation_suite_covers_the_loop.py tests/test_loop_unchanged_control.py \
  tests/test_october_prize_form_answers.py tests/test_october_research_form_answers.py \
  tests/test_filing_2026_10_numbers.py
# 344 passed, 1 warning in 51.98s

/tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
# 8/11 passed, 3 skipped, 0 failed in 15.0s
```

The warning is CPU-only pin-memory configuration. Smoke skipped two checks
requiring local training data and one requiring Villa's augmentation import.
This is not a full training-environment certification.

After the independent review's final handoff fixes, the affected suite was
rerun with `/tmp/vesuvius-review-env/bin/python -m pytest -q
tests/test_post_sprint_villa_handoff.py`: **34 passed, no skips, in 7.12 seconds**. The earlier
344-check run precedes those additional alias, cross-checkout and shell-launcher regressions.
Ruff passes on all 15 changed Python files; targeted mypy passes on the nine
new or directly reviewed process/status/artifact files. Diff and local Markdown
link checks pass.

An additional run of `tests/test_autoresearch_measurement.py`,
`tests/test_detector_patch_origin.py` and `tests/test_checkpoint_tool_contracts.py`
returned **199 passed, 1 skipped, 1 failed**. The skip requires the real Fr143
volume. The failure (`test_the_smoke_preflight_stops_on_a_foundation_model_that_does_not_fit`)
is blocked by the unavailable `nrrd` dependency in Villa's augmentation import;
the same test fails identically on the unchanged local main `625aa5d3`.
Do not describe this broader run as passing. The changed-path/data checks in
the focused suite above pass. The full repository suite and GPU workflows
were not run.
