# Contributing

Vesuvius Autoresearch is a personal ML research workspace for the
[Vesuvius Challenge](https://scrollprize.org/). The repo runs an
automated Thompson-sampling bandit loop over experimental configurations
and tracks val_bpb improvements over time. PRs and issues are welcome.

## Development

```sh
uv sync
uv run python scripts/smoke_test.py  # ~20s, exercises the main code paths
```

The smoke test forces `CUDA_VISIBLE_DEVICES=""` so it can run alongside
an active training process without contending for GPU.

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

- `train.py` — training subprocess, spawned by the bandit loop one cycle at a time
- `run_autoresearch_loop.py` — the bandit loop (Thompson sampling over `tweak_templates`)
- `vesuvius_loader.py` — `FastVesuviusVolume` and `VesuviusLabeledDataset` (returns 3-tuple `(patch, ink_label, fiber_target)`)
- `model_wrappers.py` — `GenericMultiTaskWrapper` and `build_inference_model` factory
- `predict.py`, `ensemble_predict.py` — inference scripts
- `scripts/` — utilities (`smoke_test.py`, `reevaluate_best_model.py`, label generators, etc.)
- `sprint_logs/` — per-shift bandit logs (cycle-by-cycle config + val_bpb)
- `villa/` — submodule of [ScrollPrize/villa](https://github.com/ScrollPrize/villa)
- `local_data/` — scroll data (gitignored, expected to live alongside)

## Running a bandit shift

Day Shift (15-minute cycles, runs 07:00–19:00 PT) and Night Shift
(60-minute cycles, runs 19:00–07:00 PT) auto-detect from the local
clock when `run_autoresearch_loop.py` starts:

```sh
nohup uv run python run_autoresearch_loop.py > shift_stdout.log 2>&1 &
```

The loop writes to `sprint_logs/sprint_log_<timestamp>_<shift>.md` and
auto-commits + pushes any cycle that improves `val_bpb`.
