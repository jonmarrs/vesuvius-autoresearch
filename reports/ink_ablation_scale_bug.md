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
