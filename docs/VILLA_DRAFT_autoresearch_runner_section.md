# POSTED as villa #2022 (2026-10-09): autoresearch.md describes a runner villa does not ship
## STATUS 2026-10-09: OPENED as https://github.com/ScrollPrize/villa/pull/2022 after the gate passed 33/33 at
## `a329895ea`. It is one file (+11 / −10), the body is verbatim from `docs/villa_pr_autoresearch_runner_body.md`, and the
## commit has no AI marker, following villa precedent. No nudges. Approved by the user 2026-09-29.

The approval is conditional on everything being re-checked on the day ("make sure we don't
embarrass ourselves"). **Posting-day procedure. Any failure means do not post:**

1. `.venv/bin/python scripts/check_villa_runner_pr.py` must pass every check (33/33 on 09-29 at
   `6e53201ac`). It re-fetches villa, regenerates `docs/villa_pr_autoresearch_runner.patch` against
   the current `origin/main`, re-proves every behaviour by running the current runner with stubbed
   steps, checks the PR body's cited functions and SHA, and searches for duplicates. If only the SHA
   check fails, update the SHA in the body and re-run. Anything else: stop and re-examine.
2. Look at every new number in the `INFO` search hits.
3. Re-read the generated patch and `docs/villa_pr_autoresearch_runner_body.md` in full.
4. Confirm #1928's state and that no other villa item of ours was opened within 7 days.
5. Open the PR from a branch on `jonmarrs/villa` off the current `origin/main`, with only this one
   file changed. Title: `spiral-fitting: autoresearch.md launches runners/run_single.py with the
   flags it takes`. Body = the body file, verbatim. No AI markers. Do not nudge afterwards.

The patch and body below this line are the 09-29 working drafts. The generated files are
authoritative.

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

## The open question, answered 2026-09-29: the doc's runner was never published

* `autoresearch.md` was added in #1088 (06-30) and revised in #1140 (07-14, pmh47).
* No `run_single` of any kind existed in villa's tree until #1553 (08-21). The only
  `autoresearch` branch on the remote, `spiral-autoresearch-giorgio` (07-08), has no runner either.
* So the doc was written against a runner that was never published, and the published one has a
  different interface.
* The fix therefore **adds the published runner's flags**. It does not claim the doc was wrong for
  whatever runs internally.

## A silent failure, not just a loud one (`scripts/probe_villa_runner_gpus.py`)

Launched with the doc's environment variables plus the required flags, but without `--gpus`:

| launch | fit command | `CUDA_VISIBLE_DEVICES` | tag | `FIT_SPIRAL_OUT_DIR` |
|---|---|---|---|---|
| env vars, no `--gpus` | `python fit_spiral.py`: **one process** | 4,5,6,7 passed | passed | **overridden** |
| `--gpus 0,1,2,3` | `torch.distributed.run --nproc-per-node=4` | 0,1,2,3 | passed | overridden |

The doc's instruction to "pin with `CUDA_VISIBLE_DEVICES`" therefore yields a single-process fit, and
nothing warns. How that process uses four visible devices was not measured.

## The patch (7 lines changed each way, 1 file; same shape as #1721)

```diff
--- a/spiral-fitting/autoresearch.md
+++ b/spiral-fitting/autoresearch.md
@@ -13,7 +13,7 @@
    - `point_collection.py` — helper for loading sets of annotated points, and linking them to nearby patches.
    - `losses.py`, `spiral_helpers.py`, `geom_utils.py`, `transforms.py`, `flow_fields.py` — fitting-side helper modules on the fit path (`flow_fields.py` is used via `transforms.py`) and NOT used by the metric/render pipeline. These are also fair game to edit (see scope below).
    - `tifxyz.py` — helper for loading/saving grid-topo quad-mesh patches. Read it for context, but it is **frozen** (see scope): it is shared with `render_ink.py`, so editing it changes the metric.
-   - `run_single.py` — the pipeline runner you launch (fit → render ink → score ink). You do NOT edit this or the scoring scripts; just understand what it does.
+   - `runners/run_single.py` — the pipeline runner you launch (fit → render ink → score ink). You do NOT edit this or the scoring scripts; just understand what it does.
 4. **Initialize results.tsv**: Create `results_jul9.tsv` with just the header row (see "Logging results"). The baseline will be recorded after the first run. Change `jul9` to whatever branch tag is chosen.
 5. **Confirm and go**: Confirm setup looks good.

@@ -59,15 +59,15 @@
 2. `render_ink.py <meshes_dir>` — renders ink strips into `<meshes_dir>/ink`.
 3. `get_ink_metrics.py <meshes_dir>/ink` — scores ink coverage into `<meshes_dir>/ink_metric`.

-`run_single.py` reads three things from the environment, which the caller sets:
+`runners/run_single.py` takes these flags:

-- `CUDA_VISIBLE_DEVICES` — the GPU subset for this run. `run_single.py` honours it: `--nproc_per_node` is set to the number of visible GPUs, and the pin is passed straight through to every step.
-- `FIT_SPIRAL_RUN_TAG` — the run tag (names the output dir and the fitted-mesh folder).
-- `FIT_SPIRAL_OUT_DIR` — the base output dir.
+- `--gpus 0,1,2,3` — the GPU subset for this run: one fit rank per device, and the pin is passed straight through to every step. Setting `CUDA_VISIBLE_DEVICES` alone is not enough; without `--gpus` the fit runs as a single process.
+- `--output <dir>` — the output dir for this run (it sets `FIT_SPIRAL_OUT_DIR` itself). `FIT_SPIRAL_RUN_TAG`, if set in the environment, still suffixes the run and fitted-mesh folders.
+- `--dataset` and `--ink-volume` (required), and `--no-wandb`.

-**Run two experiments at a time, each on four GPUs.** On an 8-GPU box that means one run pinned to `CUDA_VISIBLE_DEVICES=0,1,2,3` and one to `4,5,6,7`, launched concurrently. Each run is fully self-contained on its four GPUs (fit, render, and score all stay within the pin), so the two never collide.
+**Run two experiments at a time, each on four GPUs.** On an 8-GPU box that means one run with `--gpus 0,1,2,3` and one with `--gpus 4,5,6,7`, launched concurrently. Each run is fully self-contained on its four GPUs (fit, render, and score all stay within the pin), so the two never collide.

-Per-step logs go to `<out_dir>/logs/<tag>.{fit,ink,coverage}.log`, and the ink metric is written to `<out_dir>/<datedir>_<tag>/meshes/fitted_<tag>/ink_metric/metrics.json`.
+`run_single.py` writes no log files: redirect its output yourself, and read the per-step logs this document mentions from that file. The ink metric is written to `<output>/<run dir>/meshes/fitted_<tag>/ink_metric/metrics.json` (`fitted` if no tag is set).

 ## Output format — reading the metric

```

The remaining per-tag log mentions (lines 32, 74, 102, 124, 147, 160) are covered by the one
sentence "read the per-step logs this document mentions from that file". Rewriting them would be a
rewrite, and rewrites don't merge.

No AI markers. Evidence goes in the body (the table above). Do not nudge.
