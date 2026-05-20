# README skeleton

This file is a working skeleton for the project README. Section headings
and what-goes-here notes only — fill in the prose yourself in your own
voice. The technical sections (install, run, project layout) have verified
commands/lists you can copy verbatim.

---

# Vesuvius Autoresearch

<!-- USER: one-line tagline if you want one. Plain, no marketing prose
("autonomous research swarm", "Gold Standard", emoji headers). The
maintainer feedback on 2026-05-19/20 was specifically about AI-flavored
content — keep this in your own voice. -->

## What it is

<!-- USER: 3-5 lines.
Audience: a Vesuvius Challenge researcher who just clicked a link.
Answer "what does this repo do" in plain English. Suggested points:
  - it runs an automated Thompson-sampling bandit over training configs
  - each cycle is a fresh train.py run with a sampled config tweak
  - successful cycles get auto-committed; failures revert
Avoid marketing claims. State what it does, not how impressive it is.
-->

## Status

<!-- USER: a small, factual results section.
This is your strongest signal to a reviewer and the maintainer's "tools
that get used" criterion (scrollprize.org/docs/34_prizes.md).
Suggested content (point at the actual numbers in the repo):
  - best val_bpb to date: 0.4135099595785141  (commit 75af47b4, 2026-05-19)
  - 3 promotions over the past 2 days (use_ridges_True, dropout_0.0,
    lr_0.0001)
  - per-shift logs in sprint_logs/, per-promotion log in
    prize_readiness.tsv, full results.tsv tracks every accepted cycle
  - link to results.tsv and a hint at how to read it
Keep it brief — bullet points, real numbers, no adjectives.
-->

## Install

```sh
# Install uv (https://docs.astral.sh/uv/) if you don't already have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project deps into a managed venv
make install         # or: uv sync

# Sanity check: GPU detection + main module imports + 11-test smoke
make check-deps
make smoke
```

Requires Python 3.10, an NVIDIA GPU (tested on RTX 4090; 24 GB VRAM
recommended), and access to a Vesuvius Challenge scroll volume at
`local_data/<segment>/surface_volume.zarr` plus its `inklabels.png`.

## Run a single training cycle

```sh
uv run python train.py --config config.json
```

Reads `config.json` for the experiment config, writes
`run_result.json`, `best_model.pt` (on improvement), `last_model.pt`
(always), and a row in `results.tsv`.

## Run a full bandit shift

```sh
make shift           # spawns run_autoresearch_loop.py in background via nohup
```

Auto-detects Day Shift (07:00-19:00 PT, 15-min cycles) or Night Shift
(19:00-07:00 PT, 60-min cycles) from the system clock. Per-shift log
lives in `sprint_logs/sprint_log_<timestamp>_<shift>.md`. The loop
auto-commits and pushes any cycle that improves val_bpb.

To stop: `pkill -INT -f "uv run python run_autoresearch_loop"`.

## Re-evaluate best_model.pt

```sh
make reeval
```

Loads `best_model.pt` and runs validation under today's code path
without training. Surfaces metric drift between when the checkpoint
was promoted vs today's measurement.

## Project layout

- `train.py` — training subprocess; one cycle per invocation
- `run_autoresearch_loop.py` — bandit loop (Thompson sampling over `tweak_templates`)
- `vesuvius_loader.py` — `FastVesuviusVolume`, `VesuviusLabeledDataset` (returns 3-tuple `(patch, ink_label, fiber_target)`)
- `model_wrappers.py` — `GenericMultiTaskWrapper` and `build_inference_model` factory
- `predict.py`, `ensemble_predict.py` — inference scripts
- `scripts/` — utilities (`smoke_test.py`, `reevaluate_best_model.py`, label generators, candidate ranking, etc.)
- `sprint_logs/` — per-shift bandit logs
- `villa/` — submodule of [ScrollPrize/villa](https://github.com/ScrollPrize/villa)
- `local_data/` — scroll data (gitignored, expected to live alongside)

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow
and PR test-report expectations.

## License

<!-- USER: confirm. Current is MIT per the old README. -->

MIT
