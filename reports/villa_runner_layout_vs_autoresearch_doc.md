# villa's runner does not write the layout its autoresearch doc describes (2026-09-29)

**Question.** Does inkdelta read the runs villa's own runner produces? Upstream moved 9 commits on
09-28/29 (villa `6e53201ac`), so I checked each input inkdelta relies on against that tree.

## What still holds

| inkdelta relies on | villa `6e53201ac` |
|---|---|
| `all slices exist, skipping` | `vc_render_tifxyz.cpp:1738-1739`, unchanged |
| `p95=` and `rendered strip is entirely zero` | `render_ink.py:643`, `:662`, `:667` (#1886) |
| `summary.{total_fg_pixels, model, model_dir, checkpoint, folds, fg_threshold}` | `get_ink_metrics.py:618-632`, unchanged since #1805 |
| `.../meshes/fitted[_<tag>]/ink_metric/metrics.json` | `get_ink_metrics.py:497`; `spiral_helpers.py:1519` |

## What does not

`spiral-fitting/autoresearch.md` ("The pipeline and how to run it") describes a `run_single.py` that
reads `CUDA_VISIBLE_DEVICES`, `FIT_SPIRAL_RUN_TAG` and `FIT_SPIRAL_OUT_DIR` from the environment, and
writes `<out_dir>/logs/<tag>.{fit,ink,coverage}.log`. That text dates from villa #1140 (2026-07-14).
At #1140 villa contained **no runner at all**. The runner villa ships, `runners/run_single.py`, was
added in #1553 (2026-08-21) and is unchanged in shape since #1612 (08-26). It:

* takes `--dataset`, `--ink-volume`, `--output` and `--gpus` flags, and sets `FIT_SPIRAL_OUT_DIR`
  itself, overriding the caller's (`run_single.py:285`). It never sets `FIT_SPIRAL_RUN_TAG`; one in
  the caller's environment still reaches the fit, because the environment is copied;
* keeps **no log files**: the fit, render and score subprocesses write to the caller's stdout;
* with `--seeds`, writes `<output>/seed-<s>/<datedir>/meshes/fitted/...` per seed, plus
  `<output>/aggregate_metrics.json` (mean, **population** SD and count over seeds);
* under `runners/run_sweep.py`, writes one combined log per config at
  `<sweep>/.sweep/logs/<config>.log`.

Our own corpus used the documented layout, through our wrapper. So inkdelta's validations passed, and
this gap never showed.

## Effect on inkdelta 0.3.0, measured on villa's own layout

`scripts/gen_villa_runner_layout.py` runs villa's `run_single.py` (`6e53201ac`) with its three
subprocess steps stubbed, so the tree comes from villa's code rather than from my reading of it. On
that tree, inkdelta 0.3.0:

| command | result |
|---|---|
| `check <single-run output>` | OK, with `LOG_NOT_FOUND` |
| `check <--seeds output>` | **FAIL `METRICS_MISSING`** (3 found) |
| `compare --a base --b change` | **INVALID**: "a run failed an integrity check; its score is not a fresh render" |
| `noise --group base --group change` | **INVALID**: "a replicate is not a fresh render" |

The INVALID message was false: the runs were fresh, just three to a directory.

## Fix: inkdelta 0.4.0 (`65f63ba`, CI 8/8)

* A `--seeds` output expands to one run per seed, in numeric order.
* The sweep log is found automatically. It covers every seed, so a skipped render in it fails all of
  them, and the message says so.
* `aggregate_metrics.json` is cross-checked against the seed runs (`AGGREGATE_MISMATCH`); only the
  seed runs are used.
* On the same tree: `compare` gives NOT RESOLVED, +9.14% [−2.20%, +20.48%] (Welch; seed means
  3.283 M → 3.583 M), and `noise` gives CV 0.0407 [0.0244, 0.1170], df 4. These are synthetic
  values, so this checks plumbing only.
* **Regression:** `scripts/validate_inkdelta.py` gives output identical to the committed
  `reports/inkdelta_validation.json`. `scripts/validate_inkdelta_intervals.py` again passes 5/6,
  with every verdict and interval identical; only the `LOG_NOT_FOUND` wording differs.

## Side note: the aggregate's stddev is not a noise estimate

`run_single.py` computes `stddev` with `statistics.pstdev` (ddof 0). That is 29% below the sample SD
at two seeds and 18% below at three. The file is the only place the runner records a spread, since
W&B receives only the means. Anyone estimating run-to-run noise from it under-states the noise by
that much. The inkdelta README
says so.

## Not done

* **No villa action.** The doc/runner mismatch is a villa documentation defect of the kind #1721
  fixed. A PR would need the user's approval and the weekly slot (next ≥ 2026-10-06), and #1928 is
  already open. Draft: `docs/VILLA_DRAFT_autoresearch_runner_section.md`.
* **The #1928 catalogue entry was not edited.** Its example globs still work on the documented
  layout, and pushing to an open PR re-bumps it.
