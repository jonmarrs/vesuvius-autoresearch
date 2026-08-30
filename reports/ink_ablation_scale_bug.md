# VOID: the ablation run was fed 9.6 um data to models trained at 2.4 um

**2026-08-30.** Everything measured in the first ablation run is void. The cause is mine and is
recorded here before any corrected run, so the void numbers cannot later be mistaken for results.

## What was run, and what it appeared to show

Six released `PHerc.1667-iteration-*` checkpoints over ScrollGT's `scroll1_20231210121321` region.
The outputs looked pathological rather than weak:

```
it0 above0.5  2.8%    it1 67.0%    it2 17.3%    it3 0.01%    it4 88.0%    it5 70.9%
```

against a registered ink fraction of 18.4%, and every member scored **at or below chance** against
ground truth under all three pre-registered alignments (0.41 to 0.50), with a coarse +/-64 px shift
sweep peaking at 0.4731.

Read alone, that is a clean cross-scroll transfer failure, and it is the write-up I was one step
from producing.

## The control that stopped it

Running the identical pipeline on the models' **own** scroll, PHerc 1667, where these checkpoints
demonstrably recovered legible text:

| member | 1667 above 0.5 | Scroll 1 above 0.5 |
|---|---:|---:|
| it1 | 0.6908 | 0.6703 |
| it3 | 0.0001 | 0.0001 |
| it4 | 0.9023 | 0.8803 |

The same pathology on their home scroll. That is not a property of Scroll 1, so it is a property of
the pipeline.

## The bug

```
level 0: scale [2.4, 2.4, 2.4]     <- the resolution these models were trained on
level 2: scale [2.4, 9.6, 9.6]     <- what was fed to them
```

The checkpoints operate on 2.4 um data. I ran inference at pyramid **level 2**, which is 4x coarser
laterally. Every prediction was made on the wrong spatial scale.

**Where the mistake came from, precisely.** ScrollGT's target is *defined* at level 2, because that
is the resolution its ground truth was registered at. I inherited that level for the model input
without asking whether the model wanted it. Two coordinate conventions were in play, one correct for
the labels and the other wrong for inference, and nothing in the pipeline objected.

## What is void, and what is not

**Void:** the firing rates, the per-member AUCs, all three alignment arms, and the wrong-direction
control result. None of them says anything about these models or about cross-scroll transfer.

**Not void:** the reachability spike, which only showed that a checkpoint loads and emits
well-behaved output; the exclusion check, which showed no member trained on this segment; and the
pre-registration, which is untouched.

**Not established, and specifically not to be repeated:** that the PHerc.1667 models fail to
transfer to Scroll 1. That claim was never tested, because the models were never given data at the
resolution they expect.

## Cost of the fix

The region is 4096^2 at level 2 and therefore **16384^2 at level 0**, so 62 depth slices is about
16 GiB rather than 1.7 GiB. The upside is that model output would then be 4096^2, matching the
ground truth's native resolution exactly instead of needing a 4x block-mean.

## The lesson, which is not a new one here

The control that caught this is the same shape as the `k=0` null arm in the sheet-switch injection:
run the harness where the answer is already known. Both times it was the only thing standing between
a plausible narrative and a wrong published claim. The difference is that this time the harness was
pointed at someone else's models, where a confident negative would have been a claim about their
work rather than ours.

---

# RESOLVED, same day: the dominant bug was preprocessing, not pyramid level

My attribution above was incomplete. Level 2 was indeed the wrong resolution, but fixing it alone did
not help: at level 0 with z-scored input, it5 fired on **99.9%** of pixels. The dominant fault was
the intensity convention.

## The model card documents three mutually inconsistent conventions

| where | says |
|---|---|
| `modeling_inkdetection.py` docstring | "intensity already **z-score normalised**" |
| Full-segment inference snippet | feeds **raw uint8** cast to float, no normalisation |
| Quick start | "roughly **[0, 1]** ... clipped raw uint8 layers to [0, 200] then applied Normalize(mean=0, std=1)" |

I followed the docstring, then the snippet. Both saturate. Only the Quick start convention,
`clip(x, 0, 200) / 255`, produces sane output. Two reasonable readings of the same card both fail,
which is why this took four attempts rather than one.

## Measured, on the models' own scroll (PHerc 1667, segment w011, level 0)

Fraction of pixels above 0.5, 512x512 patch:

| member | z-score | raw uint8 | **clip(0,200)/255** |
|---|---:|---:|---:|
| it0 | 0.0343 | 0.0517 | **0.0732** |
| it1 | 0.7900 | 0.0784 | **0.1990** |
| it4 | 0.9870 | 0.1246 | **0.1033** |
| it5 | 0.9991 | 0.9634 | **0.0705** |

## The reference that settles it

The open-data bucket publishes a prediction for this exact segment on this exact volume,
`...2.399um-...-new_canon_autoresearch_recipe-tile256-stride128.tif`, with a `ds8` preview. It is
not one of these six checkpoints, but it is a correct prediction on the same data:

```
published prediction (ds8):  mean 33.3/255 = 0.13
  above 128 (i.e. 0.5):  2.82%
  above 160:             1.99%
  above 200:             1.09%
```

**2.8%** is what a correct firing rate looks like here. `clip(0,200)/255` puts it0 and it5 at
7.0-7.3% on a central patch, the same order of magnitude and plausible for a denser region. z-score
and raw put members at 67 to 99%, which is not a weak prediction, it is a broken input.

## What this changes

The void verdict on the first ablation run stands, with a corrected cause: **wrong intensity
convention, compounded by the wrong pyramid level.** No claim about cross-scroll transfer was ever
tested and none may be repeated.

The lesson is narrower than "read the docs": the docs were read, and they disagree with each other.
What resolved it was finding published output for the same segment and checking against it. A known
answer beats a careful reading of an inconsistent source.

## Worth reporting upstream

The three-way inconsistency is a real trap in released artifacts, checkable in one page, and of the
same kind as the `instance-labels-harmonized` dtype split already filed as villa#1654. Anyone
following the docstring or the tiling snippet gets a saturated model and no error message.
