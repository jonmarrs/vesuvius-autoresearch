# README skeleton

This file is a working skeleton for the project README. Section headings
and what-goes-here notes only — fill in the prose yourself in your own
voice. The technical sections (install, run, project layout) have verified
commands/lists you can copy verbatim. (Re-verified against the code on
2026-10-21: since the skeleton was written in May, train.py, the loader and the
inference scripts have moved, stop.sh replaced pkill, and promotion moved from
val_bpb to val_f1. The USER notes keep May's numbers.)

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

# Install project deps into a managed venv, and check out the pinned villa
# (the loop's topology metrics and villa augmentations; without it they are
# skipped, not failed)
make install         # or: uv sync
git submodule update --init villa

# Sanity check: GPU detection + main module imports + 11-test smoke
make check-deps
make smoke
```

Requires Python 3.10, an NVIDIA GPU (tested on RTX 4090; 24 GB VRAM
recommended), and access to a Vesuvius Challenge scroll volume at
`local_data/<segment>/surface_volume.zarr` plus its `inklabels.png`.

## Run a single training cycle

With the loop paused (`./stop.sh`):

```sh
PYTHONPATH=. uv run python scripts/training/train.py --config config.json
```

Reads `config.json` for the experiment config, and writes the loop's state:
`history.tsv`, `last_model.pt` and `run_result.json`, and, if it promotes,
`best_model.pt`, `results.tsv` and `prize_readiness.tsv`.

## Run a full bandit shift

```sh
# Before the first start, and after any change to the validation protocol or
# inputs: score best_model.pt under the current protocol (rewrites its stored
# scores; the loop refuses to start otherwise). `make reeval` only reports.
uv run python scripts/reevaluate_best_model.py --update-stored

make shift           # spawns run_autoresearch_loop.py in background via nohup
```

`make shift` reports that it launched the loop, not that a cycle began; the
loop's own output, including a refusal to start, is in `autoresearch.out`.
Auto-detects Day Shift (07:00-19:00 local time) or Night Shift (otherwise),
both 15-min cycles (nights ran 60 from 2026-04-29 to 2026-10-20), from the
system clock. Per-shift log
lives in `sprint_logs/sprint_log_<timestamp>_<shift>.md`. A cycle is
promoted when its val_f1 beats the incumbent's by more than 0.01 with an
AP-prevalence lift above 1.02, on the same validation protocol and inputs;
the loop commits each promotion locally (`config.json`, `best_model.pt`,
`autoresearch_history.json`) and does not push.

To stop: `./stop.sh` (it stops the loop's runs and pauses the watchdog;
`./start.sh` clears the pause).

## Re-evaluate best_model.pt

```sh
make reeval
```

Loads `best_model.pt` and runs validation under today's code path
without training, and leaves its stored scores as they are. Surfaces metric drift between when
the checkpoint was promoted vs today's measurement. To store the new
scores, run the script with `--update-stored` (above).

## Project layout

- `scripts/training/train.py` — training subprocess; one cycle per invocation
- `scripts/training/config.py` — configuration without training imports
- `run_autoresearch_loop.py` — success-weighted search over `tweak_templates`
- `scripts/loop_control.py` — lock ownership and stop/status controls
- `src/vesuvius_autoresearch/core/vesuvius_loader.py` — volume and dataset loading
- `src/vesuvius_autoresearch/core/model_wrappers.py` — shared model wrappers and inference factory
- `scripts/inference/` — prediction and ensemble scripts
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
