# Contributing

Vesuvius Autoresearch is a personal ML research workspace for the
[Vesuvius Challenge](https://scrollprize.org/). The repo runs an
automated, success-weighted search over experimental configurations
and promotes threshold-swept F1 improvements gated by AP-prevalence-lift.
PRs and issues are welcome.

## Development

For the bounded CPU checks without the research environment, use Python 3.10
and a fresh virtual environment:

```sh
python3.10 -m venv /tmp/vesuvius-cpu-tests
/tmp/vesuvius-cpu-tests/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements/ci-cpu.txt
/tmp/vesuvius-cpu-tests/bin/python scripts/run_validation_tests.py --profile portable -- --tb=short
```

The sixteen-module portable profile checks process cleanup, setup diagnostics,
bounded file captures, validation selection, retired launchers and the standalone
geometry tools, regional accumulator byte arithmetic and research-prerequisite
policy and recovery prechecks, held-out data separation, experiment checkpoint
paths and checkpoint-verification reporting. It runs on Linux
with pytest and NumPy; it does not validate
models, GPU behavior, annotation quality or historical study results. Use
`--profile portable --list` to inspect its exact scope. Patterns passed with
`--match` are restricted to that profile and never fall back to the full suite.

[Portable CPU checks](.github/workflows/cpu.yml) runs this profile and maintained
source lint on pull requests and pushes to main. The job uses a fresh environment,
no submodule checkout, read-only repository permissions and a ten-minute wall
limit. Installation and tests each have a three-minute limit; lint has one.
Actions are pinned by commit and Python dependencies by version/hash. Preserved
Villa and GP-winner sources are excluded from lint. A green job is subset evidence;
the full curated checks and manual smoke below remain separate obligations.
To make the job a merge requirement, add it as a required status check in branch protection.

Regenerate the CPU lock after changing its direct pins:

```sh
uv pip compile requirements/ci-cpu.in --python-version 3.10 --generate-hashes --output-file requirements/ci-cpu.txt
```

Keep pytest/Ruff pins aligned with the root dev group and NumPy with `uv.lock`.
The [CI advisory snapshot](reports/ci_dependency_audit.json) covers that lock only,
not bootstrap tools, Actions, OS packages or the GPU runtime.

Inspect setup without installing dependencies or starting work:
`python3 scripts/workspace_status.py` ([status guide](docs/WORKSPACE_STATUS.md)).
An `ok` report checks local paths and configuration parsing; it does not certify
GPU readiness or checkpoint compatibility.

```sh
uv sync
git submodule update --init villa    # the pinned ScrollPrize/villa
uv run python scripts/smoke_test.py  # ~20s, exercises the main code paths
```

`make test` remains the smoke alias. Use `make validate` for all curated
validation modules or `make test-all` for every module under `tests/`, including
research and historical-report guards. Both hide CUDA; data-, network- and
GPU-dependent tests may skip. Declared corpus/history checks skip with named
missing prerequisites by default; pass `--require-research-inputs` to pytest to
fail selected checks when those inputs are absent. See the
[research-test provisioning and scope](docs/RESEARCH_TESTS.md). Other legacy skip
policies and research dependencies remain separate. Record these gaps explicitly.
A smoke pass is not a full validation run.

Local training-data conversion has a maintained CPU
[TIFF/PNG import workflow](docs/TRAINING_DATA_IMPORT.md) with pinned sources and
new-directory publication. Its tests need the full project's CPU scientific
dependencies and run in the curated suite, outside the minimal portable profile.
The two root figure-generator entrypoints now report retirement before ML imports
or writes. Their source is preserved under
[scripts/archive/legacy_figures](scripts/archive/legacy_figures/README.md);
use the maintained [fiber CLI](docs/FIBER_DETECTION.md) for new sourced artifacts.

The default `uv sync` installs the locked `dev` group (pytest, Ruff and Mypy),
including the Mypy command used by the commit hook. Use the existing
[resume instructions](docs/RESUME_AFTER_RESTART.md) on a research host with an
unlocked Villa installation; do not exact-sync away its manually installed packages.

The smoke test forces `CUDA_VISIBLE_DEVICES=""`. Run it while the machine is
idle: CPU tests still compete with fits and renders for RAM and CPU time.

Inspect the curated validation suite with
`python3 scripts/run_validation_tests.py --list`. Use the project interpreter to
run it, or select modules with quoted, repeatable `--match` globs; pass pytest
options after `--`. For example:

```sh
uv run python scripts/run_validation_tests.py --match '*noise_probe*' -- -x -rs
```

The runner launches pytest from its own checkout and hides CUDA by default.
`--allow-cuda` preserves the caller's visibility settings for an intentional GPU
test run. A selected subset is not the full suite; include the selection and
pytest arguments in the PR's test report. See [validation usage](README.md#-validation).

## Pull requests

Every meaningful PR includes a test report. The structure is in
[`.github/TEST_REPORT_TEMPLATE.md`](.github/TEST_REPORT_TEMPLATE.md) and
is auto-populated into new PR descriptions by
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

Required sections:

- **What changed** — one sentence.
- **Why** — one sentence.
- **Verification** — exact commands run, actual captured output, one-line
  interpretation per test. Run `scripts/smoke_test.py` at minimum.
- **Edge cases considered** — explicit list.
- **What was NOT tested** — explicit list of gaps. Don't hide them.
- **Reviewer focus** — the part you'd most like a reviewer to scrutinize.

The point is concrete evidence of human evaluation, not polished prose.

## Project layout

- `scripts/training/train.py` — training subprocess, spawned one cycle at a time
- `scripts/training/prepare_surface_volume.py` — pinned local TIFF/PNG import into a new training fragment
- `v3_training/` — [archived prototype](v3_training/README.md); its CLI refuses before ML imports
- `scripts/training/config.py` — configuration without training imports
- `run_autoresearch_loop.py` — success-weighted search over `tweak_templates`
- `scripts/process_supervisor.py` — bounded subprocess-group cleanup
- `scripts/loop_control.py` — lock ownership and stop/status controls
- `src/vesuvius_autoresearch/core/vesuvius_loader.py` — volume and dataset loading
- `src/vesuvius_autoresearch/core/model_wrappers.py` — shared model wrappers and inference factory
- `scripts/inference/` — prediction and ensemble scripts
- `scripts/` — utilities (`smoke_test.py`, `reevaluate_best_model.py`, label generators, etc.)
- `sprint_logs/` — per-shift logs (config, F1, diagnostic metrics, and outcome)
- `villa/` — submodule of [ScrollPrize/villa](https://github.com/ScrollPrize/villa)
- `local_data/` — scroll data (gitignored, expected to live alongside)

## Running a bandit shift

Day Shift (runs 07:00–19:00) and Night Shift (runs 19:00–07:00), both
15-minute cycles (nights ran 60 minutes from 2026-04-29 to 2026-10-20),
auto-detect from the host's local clock when `run_autoresearch_loop.py`
starts:

```sh
./start.sh
./stop.sh  # stops the registered process and pauses the watchdog
```

The loop writes to `sprint_logs/sprint_log_<timestamp>_<shift>.md` and
auto-commits successful promotions locally. Starting again clears the pause.
