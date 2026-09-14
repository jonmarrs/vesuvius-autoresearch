# Ready PR candidate: `get_ink_metrics.py` OOMs on large strips

**Prepared 2026-09-14. NOT FILED — we are at villa's 3-open-PR cap** (#1780, #1728, #1723). File when
a slot opens, after re-verifying against upstream at that time.

## The defect, verified live at `76370e1a6`

`spiral-fitting/get_ink_metrics.py` launches one subprocess per fold and waits for all of them
together:

```python
546:  print(f'  launching fold {fold} on GPU {gpu} -> ...')
547:  procs.append((fold, gpu, subprocess.Popen(cmd, env=env, ...)))
550:  for fold, gpu, proc, logf in procs:
551:      rc = proc.wait()
```

So all three folds are live at once, each holding a copy of the strip's logits. The file contains
**zero** references to serial or sequential execution, so there is no existing way to avoid it.

## Why it matters

Strip size varies by two orders of magnitude with winding range:

| windings | flat grid | rendered strip |
|---|---|---|
| w010–w019 (inner) | 881 × 304 | 26.8M px |
| w120–w129 (outer) | 8267 × 426 | **352M px** |

At 352M px, three concurrent folds exhaust a 32 GB box. **And it fails in a way the fold logs do not
explain** — the OOM killer leaves `rc=-9` and nothing else:

```
[mem] used= 8706MB avail=23386MB    <- before launch
[mem] used=30878MB avail= 1214MB    <- three folds live
  fold 1 (GPU 0) FAILED (rc=-9)     <- SIGKILL
```

Anyone scoring outer windings on a workstation hits this, and the logs point nowhere.

## The fix we already run

`repro/spiral_render/serial_folds.patch` — **verified 2026-09-14 to apply cleanly to `76370e1a6`**.

* gated on `INK_METRIC_SERIAL_FOLDS=1`, so **the default path is byte-identical to upstream**;
* runs one fold at a time;
* averages incrementally rather than stacking all folds, so it never holds more than two at once;
* the incremental mean is **bit-identical to `np.mean` at n=3 float32**, verified.

## Before filing

1. **Re-verify the defect still exists** at upstream *then*, not from this file. That check has
   already prevented two wrong PRs (README §4 was fixed upstream; a stale note nearly produced
   another).
2. Re-run the patch dry-run against the then-current `get_ink_metrics.py`.
3. Include the memory trace above — it is the part that makes the failure legible, and it is what a
   maintainer cannot reproduce from the code alone.
4. Keep it to the gated behaviour change. No refactor, no reformat.

## Why this shape

Both merged PRs (#1721, #1722) were small fixes to `spiral-fitting` found by *running* villa's
pipeline. This is the same: a crash hit in real use, with the fix already in production here across
every outer-winding arm this project has scored.

It is a code change rather than a doc change, which is a different risk class — villa closes feature
PRs. It is framed as a defect fix with the default path unchanged, which is the closest this can get
to the shape that has merged twice.
