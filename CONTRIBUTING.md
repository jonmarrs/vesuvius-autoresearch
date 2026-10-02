# Contributing

Vesuvius Autoresearch is a personal ML research workspace for the
[Vesuvius Challenge](https://scrollprize.org/). The repo runs an
automated, success-weighted search over experimental configurations
and promotes threshold-swept F1 improvements gated by AP-prevalence-lift.
PRs and issues are welcome.

## Development

```sh
uv sync
uv run python scripts/smoke_test.py  # ~20s, exercises the main code paths
```

The smoke test forces `CUDA_VISIBLE_DEVICES=""`. Run it while the machine is
idle: CPU tests still compete with fits and renders for RAM and CPU time.

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

Day Shift (15-minute cycles, runs 07:00–19:00) and Night Shift
(60-minute cycles, runs 19:00–07:00) auto-detect from the host's local
clock when `run_autoresearch_loop.py` starts:

```sh
./start.sh
./stop.sh  # stops the registered process and pauses the watchdog
```

The loop writes to `sprint_logs/sprint_log_<timestamp>_<shift>.md` and
auto-commits successful promotions locally. Starting again clears the pause.
