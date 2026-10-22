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

A copy of every `*.sh` driver in `spiral_out` at the time of vendoring, 60 files, and 14 copied since as
studies launched (74 on 2026-10-22). Each fit driver pins, for one arm: the dataset path, the villa tree,
the venv, the z-ROI, the config overrides, and the seed. Together with `reports/` and
`docs/preregistration/` they are what makes an arm re-runnable.

**Not vendored:** `nosamecur_s4`, `nosamecur_s5` and `nosamecur_s6`, the same-winding extension's arms
(`docs/preregistration/2026-09-28_samewinding_extension.md`). Its preregistration specifies each as
`fit_nosamecur_s1.sh` with only `optimizer_random_seed` (4, 5, 6) and the tag changed, but the drivers
that ran were never copied here. Copy them from `spiral_out`, then empty `_NOT_VENDORED` in
`tests/test_arm_tiers.py`, which holds this list exact.

**These are copies, not the live scripts.** They are here to be *read* and to record what was run.
Running one requires the paths it names to exist. If you change a driver, change it in `spiral_out`
and re-copy — this directory is downstream.

## The tiers, which are not comparable

`scripts/arm_tiers.py` is the one table of which arm belongs to which tier, and
`tests/test_arm_tiers.py` checks it against the tree each driver here fits with.

* `fit_gap133*`, `gap133*.sh`, `fit_boot090*`, `fit_rand090*`, `fit_nosame_s*`, `fit_strip090*`,
  `baseline.sh`, `seed0*.sh`, `fit_seed0*.sh` — villa-spiral **`6847063f`** (pinned working tree).
* `fit_curbase_s*`, `fit_nosamecur_s*`, `fit_anchor10cov_{pilot,s2,s3}.sh` — **current** villa
  (`villa-spiral-current/`), which recovers 67.6% more ink through a byte-identical scorer.
* `fit_upfit.sh` — the **upstream** fitter (`villa-spiral-upstream/`, villa `75c79ac5f`), its own tier
  until its registered comparison says otherwise (`docs/preregistration/2026-09-24_upstream_fitter.md`).

`reports/corpus_is_on_superseded_code.md` and `reports/noise_floor_by_tier.md` explain why mixing
them is invalid; `scripts/measure_noise_floor.py` refuses to. The smoke and exploratory drivers
(`fit_smoke_*`, `smoke.sh`, `densespace0.sh`, `margin0.sh`, `minspace0.sh`) are deliberately left out of the
table, so any analysis that scores them raises.

## Superseded drivers kept deliberately

`fit_smoke_anchor10.sh` and the 200-step smoke drivers produced measurements that later turned out to
be the wrong instrument (radius cannot identify a winding) or the wrong configuration
(`spiral_s1_anchor10` collapses all ten anchors onto one z-plane). They are kept so those earlier
numbers stay explainable rather than merely wrong.
