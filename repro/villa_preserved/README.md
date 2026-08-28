# Byte-identical copies of the villa files our reproductions cite

Copied 2026-08-27 from villa at our pin `ced62390e` (2026-08-13). Nothing here is our work: every
file is a byte-identical copy, verified by md5 against `git show ced62390e:<path>`.

## Correction, 2026-08-28: these files were MOVED, not deleted

The first version of this file, and the commit message that introduced it (`492e2cb0`), said
upstream had **deleted** 110 files from `ink-detection/`. That was wrong, and the error was mine:
I ran `git diff --stat ced62390e origin/main -- ink-detection/`, and a path-scoped diff renders a
**move out of that path** as a deletion. It cannot see the destination.

What upstream actually did between `ced62390e` and `6847063ff` is relocate the 2023-era
ink-detection tree to `deprecated/ink-detection/`. Checked at upstream HEAD:

```
labels at our pin,  ink-detection/all_labels:              46
labels upstream, deprecated/ink-detection/all_labels:      46
```

All three segments this project names as its unblock path (`20230820203112`, `20230826170124`,
`20230903193206`) are present upstream, as are `train_timesformer_og.py` and
`train_resnet3d_3d_decoder.py`. **Nothing was lost, and nothing here was rescued.**

## So why keep this directory?

A weaker reason than the one it was created for, but a real one.

- Our reports cite these files at `villa/ink-detection/<name>`. That path does not exist upstream any
  more. A pin bump silently breaks every one of those citations, and a byte-identical local copy at a
  stable path is what keeps a report reproducible across the bump.
- `deprecated/` is a declared intention. Upstream is free to delete the directory later, and the
  labels are the input to the only unblock path this project has identified.

That is a reproducibility convenience and a low-cost hedge. It is **not** a rescue, and this file
should not be read as evidence that upstream is discarding data.

## What is here

| file | why it matters |
|---|---|
| `train_timesformer_og.py` | the GP-winner recipe our Phase 2 replication retrained (held-out AUC 0.905) |
| `train_timesformer_deduped.py` | its sibling, cited alongside it |
| `train_resnet3d_3d_decoder.py` | referenced by our ResEnc comparison |
| `inference_timesformer.py` | the inference half of the same recipe |
| `download.sh`, `requirements.txt` | provenance: how the data and environment were obtained |
| `all_labels/{20230820203112,20230826170124,20230903193206}_inklabels.png` | the three segments named in the unblock path |

The other 43 of the 46 labels are not copied. They are 45 MB, they are in upstream at
`deprecated/ink-detection/all_labels/`, and they are also in villa's history at our pin:

```bash
git -C villa show ced62390e:ink-detection/all_labels/<segment>_inklabels.png > <out>.png
```

## The lesson, which is the part worth keeping

A path-scoped diff cannot distinguish a deletion from a move out of the scope. I read
`19,342 deletions` as loss and wrote a commit message asserting it, without running the one command
that would have distinguished the two: search for the filenames across the whole tree.

This is the same shape as several defects already recorded in this project: a check that is
structurally blind to the alternative it is being used to rule out. The tiling closure could not see
per-strip scale error; `col_gutter_auc`'s negative controls could not see metric blindness; a
path-scoped diff cannot see a move. In each case the fix was to ask what the check *cannot* see
before citing it.

## What this does NOT do

It does not update the pin. The pin is still `ced62390e`, and our reports reproduce against it.
