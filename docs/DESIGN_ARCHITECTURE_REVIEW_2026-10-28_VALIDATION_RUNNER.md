# Validation runner design and architecture review — 2026-10-28

Reviewed `scripts/run_validation_tests.py`, its curated registry and contributor
workflow against main `f193cec2376138b6bc7833344a8d02b3ee7142c2` (PR #279).
Work used an isolated checkout and synthetic subprocess fixtures. No live study
results/journals, GPU jobs, research deployment or prize filing were used.

## Findings and changes

- **CLI intent was ignored.** The launcher did not parse arguments, so `--help`,
  typos and requested pytest options all started the full suite. Argparse now
  handles help and rejects unknown options before launching anything. Explicit
  arguments after `--` are forwarded to pytest with their boundaries preserved.
- **The caller selected the checkout accidentally.** Relative test paths were
  resolved from the caller's directory, permitting missing tests or tests/config
  from another checkout. The pytest child now uses the runner's resolved checkout
  as its working directory and retains the active Python interpreter.
- **Routine validation inherited GPU access.** CUDA is hidden in the child
  environment by default. `--allow-cuda` preserves the caller's settings for an
  intentional GPU test; it neither allocates nor verifies a GPU. The parent's
  environment and working directory are unchanged.
- **The suite was hard to inspect or narrow.** `--list` prints paths without
  launching pytest or importing ML dependencies. Repeatable `--match` globs
  select the union of curated modules in registry order without duplicates.
  Each pattern must match; typos cannot silently reduce coverage. Invalid,
  missing or externally linked registry entries stop before launch.
- **Launch reporting obscured intent.** The runner prints selected/total module
  counts, checkout, CUDA policy and a shell-quoted command. It preserves pytest
  exit codes and maps signal termination to conventional `128 + signal` status.
  Spawn failures and keyboard interruption produce concise diagnostics.

The three original regressions all failed on the baseline. They establish that
help/unknown options launched pytest and that child launch lacked a checkout and
CUDA policy. Additional tests exercise selection, registry errors, environment
preservation, status propagation and real CLI subprocess behavior.

## Architecture

The runner remains standard-library-only. The flow is parse CLI → validate the
curated registry → select modules → list or describe and launch one pytest child.
The manually curated inventory and its existing coverage guard remain the source
of suite membership; this change does not replace them with broad discovery.
The new runner tests are registered in that inventory.

Pytest remains responsible for collection, execution and reporting. Arguments
after `--` can narrow tests or add paths; the printed curated-module count does
not claim a collected/passed test count. Missing optional data/dependencies can
still fail or skip individual tests. Hiding CUDA is a child environment policy,
not an isolation boundary: tests can change their own settings, and CPU/RAM work
still competes with training. The standard suite is not certified lightweight.

## Verification

Using cached dependencies, from `/tmp`:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python /workspace/vesuvius-validation-review/scripts/run_validation_tests.py --match '*validation_runner*' --match '*validation_suite_covers_the_loop*' --match '*checkout_imports_its_own_code*' --match '*smoke_checkout*' --match '*workspace_status*' -- -rs
python3 /workspace/vesuvius-validation-review/scripts/run_validation_tests.py --list --match '*validation*'
python3 /workspace/vesuvius-validation-review/scripts/run_validation_tests.py --help
```

Captured selected-run output:

```text
Validation scope: 5/145 curated modules
Working directory: /workspace/vesuvius-validation-review
CUDA visibility: hidden
55 passed in 9.13s
```

The listing returned the two validation-related module paths, and help displayed
usage without starting pytest. The selected run covers 29 runner cases, the
existing suite coverage guard, checkout import/smoke isolation and workspace
status. Actual CLI fixtures invoke a stand-in pytest child from a separate
directory, including checkout paths with spaces, exact argument boundaries,
inherited/hidden CUDA visibility and child exit code 5. The initial three cases
failed on the baseline: `3 failed in 0.20s`.

From `/workspace/vesuvius-validation-review`:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
/tmp/vesuvius-pr256-lint/bin/ruff check scripts/run_validation_tests.py tests/test_validation_runner.py
/tmp/vesuvius-pr256-lint/bin/ruff format --check scripts/run_validation_tests.py tests/test_validation_runner.py
PYTHONPATH=/tmp/vesuvius-pr256-types python3 -m mypy --follow-imports=skip --explicit-package-bases --namespace-packages --cache-dir /tmp/vesuvius-validation-mypy scripts/run_validation_tests.py tests/test_validation_runner.py
git diff --check
```

Smoke: **8/11 passed, 3 skipped, 0 failed in 16.4s**. Two dataloader checks
lacked local training inputs; optional bg2 augmentation was unavailable.
Matplotlib/fontconfig reported cache-directory warnings. Ruff check/format
passed, scoped mypy found no issues in two files, and whitespace checks passed.
These checks support runner behavior, not full-suite or scientific correctness.

## Limits

No full curated-suite run, native GPU execution, scientific accuracy or active
research-host integration was tested. CUDA opt-in was checked with a stdlib-only
stand-in for pytest, with no GPU allocations. Test selection is path-based and
does not infer which modules a source-code change requires. The runner does not
add process-group supervision or a test sandbox; pytest's normal foreground
process behavior remains in use. Existing environment and pytest configuration
are retained.
