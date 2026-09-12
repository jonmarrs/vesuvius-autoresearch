# Fit drivers for every spiral arm we have scored

**Vendored here 2026-09-12.** These scripts live and run in
`/home/jon/openclaw-workspace/Neo-VM/spiral_out/`, which belongs to a **different repository** — the
OpenClaw workspace, with its own live remote. This repo never commits there
(see `docs/` and the standing rule to verify `git rev-parse --show-toplevel` before any git write in
a nested tree), so until today **the exact configuration of every arm behind every published result
was untracked from this repo's point of view.**

That is a reproducibility hole, and it produced a visible symptom: commit `444ff05f`'s message says
"Also adds `spiral_out/fit_anchor10_pilot.sh`". **It did not** — that path is outside this repo and
the file was never staged. The message overstated what the commit contained. Recorded here rather
than quietly fixed, since the commit is already pushed.

## What is here

A copy of every `*.sh` driver in `spiral_out` at the time of vendoring, 60 files. Each one pins, for
one arm: the dataset path, the villa tree, the venv, the z-ROI, the config overrides, and the seed.
Together with `reports/` and `docs/preregistration/` they are what makes an arm re-runnable.

**These are copies, not the live scripts.** They are here to be *read* and to record what was run.
Running one requires the paths it names to exist. If you change a driver, change it in `spiral_out`
and re-copy — this directory is downstream.

## The two tiers, which are not comparable

* `fit_gap133*`, `fit_boot090*`, `fit_rand090*`, `fit_nosame_s*`, `fit_strip090*`, `baseline.sh`,
  `seed0*.sh` — villa-spiral **`6847063f`** (pinned working tree).
* `fit_curbase_s*`, `fit_nosamecur_s*`, `fit_anchor10cov_pilot.sh` — **current** villa
  (`villa-spiral-current/`), which recovers 67.6% more ink through a byte-identical scorer.

`reports/corpus_is_on_superseded_code.md` and `reports/noise_floor_by_tier.md` explain why mixing
them is invalid; `scripts/measure_noise_floor.py` refuses to.

## Superseded drivers kept deliberately

`fit_smoke_anchor10.sh` and the 200-step smoke drivers produced measurements that later turned out to
be the wrong instrument (radius cannot identify a winding) or the wrong configuration
(`spiral_s1_anchor10` collapses all ten anchors onto one z-plane). They are kept so those earlier
numbers stay explainable rather than merely wrong.
