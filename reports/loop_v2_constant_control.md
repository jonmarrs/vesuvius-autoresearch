# Under validation protocol v2 the loop's incumbent scores no better than calling every pixel ink (finding 86)

**2026-10-12.** A post-hoc control, **not pre-registered**. It was run while carrying out the GPU-host step that
[the loop measurement review](../docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-12_AUTORESEARCH_LOOP.md) left untested. Script:
`scripts/loop_v2_constant_control.py` at `c01e42d9`; output: `reports/loop_v2_constant_control.json`. The checkpoint was
`best_model.pt` with SHA-256 `1f84953760eed3a8…`. The control is read-only; the checkpoint was hashed before and after
every run and never changed.

**Question.** The review asks the GPU host to re-score `best_model.pt` under protocol `seeded-sample-400-v2` and
compare it with the stored 0.468. The dry run of `scripts/reevaluate_best_model.py` returned **0.7271**. Is that the
model reading ink better than the stored score said, or a property of the new sample?

## Result

The v2 sample kept **97** of 400 requested patches (the ink-free ones are excluded), **397,312** pixels, of which
**0.5760** are ink. A threshold-swept F1 has a floor at that prevalence: calling every pixel ink scores
2p/(1+p) = **0.7310** at every threshold.

| predictor, same 97 patches | val_f1 | best threshold | predicted ink | AP lift | ROC AUC |
|---|---:|---:|---:|---:|---:|
| `best_model.pt` | **0.7271** | 0.05 | 0.9760 | **1.0856** | **0.5527** |
| every pixel ink | **0.7310** | 0.05 | 1.0000 | 1.0000 | 0.5000 |
| the model's probabilities, randomly permuted | 0.7248 | 0.05 | 0.9760 | 1.0002 | 0.5008 |

* The model's F1 is **0.0039 below** the all-ink floor. Its best threshold is the lowest one swept, where it calls
  97.6% of pixels ink.
* Its AP lift (1.0856) and ROC AUC (0.5527) are only slightly above the permuted control (1.0002, 0.5008). No
  significance is claimed for the gap: the pixels come from 97 patches and are not independent.
* So the +0.259 jump from 0.468 is the sample, not the model.

v1 recorded its own sample's prevalence in the checkpoint (`val_positive_rate`), so the two scores can be compared on
the one footing they share, the margin over each sample's own all-ink floor:

| score | val_f1 | ink prevalence | all-ink F1 | **margin** | ROC AUC | AP lift |
|---|---:|---:|---:|---:|---:|---:|
| v1, as stored (the review: 80 ink-containing patches, one strip) | 0.4683 | 0.2607 | 0.4135 | **+0.0548** | 0.6689 | 1.5387 |
| v2, re-scored today (97 patches spread over the fragment) | 0.7271 | 0.5760 | 0.7310 | **−0.0039** | 0.5527 | 1.0856 |

The same checkpoint that cleared its floor on one strip falls just below it on a sample spread over the fragment, and
its AUC drops from 0.669 to 0.553. That is what the review expected v2 to fix: v1's single strip flattered the model.
The two rows come from different code and different patches, so read the margins as direction, not as a measured
change.

## The lasagna flattening the config requests has never run on this host

`config.json` sets `use_lasagna: true`. The loader's flattening JIT-compiles a CUDA extension
(`villa/lasagna/grid_sample_3d_u8.py`, via `torch.utils.cpp_extension.load`), and this host has no CUDA compiler: no
`nvcc` on the system or in the venv, no `/usr/local/cuda`, `CUDA_HOME` unset (torch is the `cu128` pip build, which
ships the runtime but not `nvcc`). The loader catches the error and returns the **unwarped** patch, warning only the
first five times per process.

Counted on 2026-10-12 in the last two loop logs: `run.log` (2026-07-11) has **2,185** fallback warnings and
`run.log.old` (2026-06-26) has **980**. Every one is the same failure: 2,532 `ImportError` for the missing
`grid_sample_3d_u8_ext.so` and 633 `OSError: CUDA_HOME environment variable is not set`.

So the incumbent was trained, stored its score, and was re-scored here all on unwarped patches. The comparisons above
are like with like; what is wrong is that the config claims an input transform that has not been applied in any run on
record.

### Correction, 2026-10-13: a CUDA toolkit alone would not make it run

The extension never compiled, so the kernel's own input checks were never reached, and they would have failed
next. `villa/lasagna/grid_sample_3d_u8_kernel.cu` requires every input to be a CUDA tensor (`volume must be CUDA
uint8`, `grid must be CUDA float32`) and a `(D, H, W, 3)` grid. The loader reads patches on the CPU
(`get_raw_patch` returns `torch.from_numpy(...)`) and passed a 5-D grid. The loader now refuses a CPU uint8 patch
before the compile, with that reason, and passes the 4-D grid. (uint16 volumes, read as int32, cannot be warped
either; they are refused the same way.) So option 3's toolkit branch below also needs the
warp moved to the GPU (in the training process, not the data-loader workers), or the uint8 patch warped on the CPU
with torch's `grid_sample`, which the loader already uses for float volumes. Either way inference must apply the
same warp: `scripts/inference/predict.py`, `scripts/production_predict.py` and `scripts/inference/ensemble_predict.py`
never flatten, so a model trained on warped patches would be served unwarped ones.

Since the 2026-10-13 preprocessing review, a strict validation read refuses a requested warp that cannot run, so a
cycle that keeps `use_lasagna: true` (every cycle but the one that tweaks it off) cannot be scored on these uint8
volumes. `train.py` now reads one validation patch before training, so such a cycle fails before training instead of
after its budget, and after five crashed cycles in a row the loop waits one cycle budget between attempts.

## What this means for the migration

These are decisions for the loop's owner; none was taken here.

1. **Do not calibrate `F1_NOISE_TOLERANCE` from `scripts/f1_noise_probe.py` yet.** While runs sit at the all-ink
   ceiling, their F1 cannot spread far, so the measured run-to-run noise would understate it for any candidate that
   moves off the ceiling. This is reasoning, not a measurement; the probe was not run.
2. **The promotion gate still demands real signal.** After `--update-stored` the incumbent would store 0.7271, so a
   candidate needs F1 above 0.7571 and AP lift above 1.02. That is 0.0261 above the all-ink floor. What changes is
   that the stored incumbent score itself would sit below a no-information predictor.
3. **Lasagna**: install a CUDA toolkit matching `cu128` so the extension builds (changes the input of every future
   run; the incumbent never saw warped patches), set `use_lasagna` to false so the config describes what has
   actually run, or make the loader refuse to start when flattening is requested but unavailable.
4. **The metric**: v2's sample makes F1 a prevalence measurement for a near-constant model. Options include scoring
   the margin over the all-ink floor, adding ink-free patches back (the review calls that a separate decision), or
   promoting on AP lift or AUC. Not decided here.

## Changed with this finding

`scripts/reevaluate_best_model.py` now prints the ROC AUC and the all-ink baseline beside `val_f1`, and compares the
margins rather than only the raw F1, so the next re-score shows this directly:

```
  val_f1:              0.727089 (protocol seeded-sample-400-v2)
  ap_prevalence_lift:  1.0856
  roc_auc:             0.5527
  all-ink baseline F1: 0.730993 (ink prevalence 0.5760; val_f1 margin -0.003905)
  ...
  val_f1 margin over all-ink: today=-0.003905 stored=+0.054791
```

## Not done

One checkpoint, one sample seed (42), unwarped inputs only. The migration's `--update-stored`, commit, noise probe and
`./start.sh` steps were not run.
