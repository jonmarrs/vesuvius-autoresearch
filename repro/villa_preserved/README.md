# Files upstream deleted that our work depends on

Preserved 2026-08-27 from villa at our pin `ced62390e` (2026-08-13), because upstream `main`
(`6847063ff`, 2026-08-26) deletes them. Nothing here is our work: every file is a byte-identical
copy, verified by md5 against `git show ced62390e:<path>`.

## Why this exists

Upstream removed 110 files from `ink-detection/` between our pin and 2026-08-26 — 19,342 deletions.
Six of them are referenced by our reproductions or reports, and one directory is ground truth.

Our own submodule-update procedure says to verify `ink-detection/` is untouched before pinning
forward, precisely because GT is read from there. That check now fails. This directory is what makes
a future pin bump safe rather than silently destructive.

## What is here, and why each

| file | why it matters |
|---|---|
| `train_timesformer_og.py` | the GP-winner recipe our Phase 2 replication retrained (held-out AUC 0.905) |
| `train_timesformer_deduped.py` | its sibling, cited alongside it |
| `train_resnet3d_3d_decoder.py` | referenced by our ResEnc comparison |
| `inference_timesformer.py` | the inference half of the same recipe |
| `download.sh`, `requirements.txt` | provenance: how the data and environment were obtained |
| `all_labels/2023082{0113,61701}*.png`, `all_labels/20230903193206_inklabels.png` | see below |

## The three labels are the unblock path, which is why they are here

`reports/detector/gt_training_data_exhaustion_2026-08-15.md` records that registered-GT training
data on Scroll-1 is exhausted, and names the unblock path: *re-flatten one of the three absent
labelled segments*. Those three are `20230820203112`, `20230826170124`, `20230903193206`. Their
**geometry** is absent from the open bucket; their **labels** existed only in
`villa/ink-detection/all_labels/`, which upstream has now deleted.

So if that geometry is ever published, the labels are what turns it into a usable segment. Losing
them would close the only unblock path this project has identified.

## The other 42 labels are not copied, deliberately

`all_labels/` holds 45 label PNGs at our pin, 45 MB in total. Copying all of them would put 45 MB of
binaries into this repository to guard against a risk that is already low: **deleted files remain in
villa's history**, and are recoverable at any time with

```bash
git -C villa show ced62390e:ink-detection/all_labels/<segment>_inklabels.png > <out>.png
```

Verified working for all three copied labels. The three here are copied because they are named in a
live unblock path and are the ones we would reach for first; the rest are one command away.

That recovery depends on villa's history remaining available. If that ever looks uncertain, copy the
remaining 42 — but a 45 MB commit to hedge against upstream rewriting published history is not a
trade worth making today.

## What this does NOT do

It does not update the pin. The pin is still `ced62390e`, and our reports reproduce against it. This
only means that when someone does bump it, the files above survive the bump.
