# DRAFT (not posted): autoresearch.md describes a runner villa does not ship

**Status:** draft, 2026-09-29. **Not posted, and not to be posted without the user's explicit
approval.** Gates:
* the weekly new-item slot (next ≥ 2026-10-06);
* #1928 is still open;
* a duplicate search on the day. It was clean on 2026-09-29 for "autoresearch.md run_single",
  "FIT_SPIRAL_RUN_TAG", "ink.log" and "aggregate_metrics".

Evidence: `reports/villa_runner_layout_vs_autoresearch_doc.md`.

## The defect (verified against villa `6e53201ac`)

`spiral-fitting/autoresearch.md`, "The pipeline and how to run it", says `run_single.py` reads
`CUDA_VISIBLE_DEVICES`, `FIT_SPIRAL_RUN_TAG` and `FIT_SPIRAL_OUT_DIR` from the environment, and that
per-step logs go to `<out_dir>/logs/<tag>.{fit,ink,coverage}.log`. The runner villa ships is
`spiral-fitting/runners/run_single.py` (#1553). Launched as the doc says:

```
$ CUDA_VISIBLE_DEVICES=0,1,2,3 FIT_SPIRAL_RUN_TAG=jul9a FIT_SPIRAL_OUT_DIR=... python runners/run_single.py
run_single.py: error: the following arguments are required: --dataset, --ink-volume
```

It takes `--output`, not `FIT_SPIRAL_OUT_DIR`, which it overwrites (`run_single.py:285`). It writes
no log files. It enables W&B unless `--no-wandb` is given. Line 16 also names `run_single.py` without
its `runners/` directory. The text dates from #1140 (07-14), when villa had no runner in the tree.

## Open question before drafting a diff

**The maintainers' own loop may use a different, unpublished runner that does match the doc.** If
so, the fix is one sentence ("this section describes the internal runner; the published one is
`runners/run_single.py` with flags …"), not a rewrite. That would be a question to ask, not a PR to
open. Look for evidence first, e.g. recent commits by the loop's authors that reference
`FIT_SPIRAL_RUN_TAG` launches.

## Shape if it is a PR (same shape as #1721)

The smallest correct change, about 6 lines in one file:

* line 16: `run_single.py` → `runners/run_single.py`;
* lines 62–66: replace the three environment variables with the flags actually needed:
  `--dataset`, `--ink-volume`, `--output`, `--gpus 0,1,2,3`, `--no-wandb`;
* line 70: logs are whatever the caller redirects; the metric is at
  `<output>/<datedir>/meshes/fitted/ink_metric/metrics.json`, or
  `<output>/seed-<s>/…` with `--seeds`.

Lines 32, 74, 102, 124, 147 and 160 also cite the per-tag logs or `FIT_SPIRAL_RUN_TAG`. Changing all
of them is a rewrite, and rewrites don't merge. The minimal PR fixes
the launch interface and says the logs are the caller's redirect.

No AI markers. Evidence goes in the body. Do not nudge.
