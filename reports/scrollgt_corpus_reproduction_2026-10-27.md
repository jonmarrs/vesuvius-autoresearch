# Whole-corpus CPU reproduction of ScrollGT's connected-components baseline

Verified 2026-10-27T17:22:22-07:00 (Pacific),
2026-10-28T00:22:22+00:00 (UTC).

All **21 released fiber targets** reproduce every one of the **15 published
connected-components fields**, for **315 matching field values**. This extends
the [two-example memory check](scrollgt_cpu_reproduction_2026-10-25.md) to the
complete corpus: ten 256³ and eleven 512³ cubes from Scrolls 1, 3 and 5.
Every CLI process completes under a **7 GiB address-space limit** (`RLIMIT_AS`).
That limit is distinct from its measured physical peak RSS.

| Cube size | Exact rows | Per-target wall-time range | Peak RSS range |
| --- | ---: | ---: | ---: |
| 256³ | 10 / 10 | 7.89–17.16 s | 0.57 GiB |
| 512³ | 11 / 11 | 71.99–126.38 s | 2.55–2.57 GiB |

The table summarizes operational resource use only; it does not average quality
across cube sizes or training splits. There is one measurement per target in
the complete pass. Inputs were locally cached and hashed before timing;
download, installation and cold-cache performance are outside this check.
The times include CLI startup and do not establish a general speedup.

## Source and comparison

The source is ScrollGT `38496eb8ce5dc094c94ec852a332ee2293ea73a1`, the published source of the
merged [memory fix, PR #14](https://github.com/jonmarrs/scrollgt/pull/14).
Its target data are unchanged from v0.9.0. The v0.9.0 tag itself predates that
memory fix; this is a check of the patched scorer against the released rows.
Scoring version remains 3. No model, target, annotation, metric definition or
published row changes.

Each invocation recomputes connected components from the shipped mask and
scores that prediction against the shipped skeleton. The comparison uses the
entire `scorecard['metrics']` dictionary, exactly, including splits, merges,
counts, lengths and tolerance. Its other floor rows are read from metadata;
this check does **not** recompute all four floors or any learned tracer.
It verifies the rounded published fields, not unrounded values or every grown
label voxel. The earlier 256³ check separately established unrounded equality.

The [JSON record](evidence/scrollgt_corpus_reproduction_2026-10-27.json)
contains all actual and expected rows, input and source hashes, runtime versions,
per-process measurements and the exact CLI commands. The
[raw archive](evidence/scrollgt_corpus_reproduction_2026-10-27_raw.zip) contains
all 21 scorecards, logs, requests and measurements (84 files), with hashes
verified against the record. Requests do not serialize the inherited environment.

Runtime: Linux x86-64, Python 3.10.21, NumPy 2.2.6,
SciPy 1.15.3, scikit-learn 1.7.2.
OpenMP/OpenBLAS/MKL were each configured to one thread. Each timed CLI had a
fresh measurement wrapper so `RUSAGE_CHILDREN.ru_maxrss` is not a cumulative
peak across targets. No packages were installed and no GPU work was launched.

An initial setup pass was interrupted after five small-cube checks when the
harness's import-order check failed. Those logs are retained separately. The
complete pass restarts all 21 targets with the corrected, unchanged harness;
none of the initial results fills a slot or enters its timing table. Captured
source, input and harness hashes match again at the end of the complete pass.

## Reproduction

With the pinned ScrollGT source and its dependencies already available, run:

```sh
python repro/fibers/verify_scrollgt_cc_corpus.py \
  --scrollgt /path/to/scrollgt --out /path/to/new-output \
  --python /path/to/scrollgt-environment/bin/python
```

The [frozen harness](../repro/fibers/verify_scrollgt_cc_corpus.py) checks the
source revision, requires all 21 targets, refuses outputs overlapping the
source checkout, sets the resource budget, and retains failed exits and logs.
`--launcher` accepts an existing environment launcher where needed. It neither
installs dependencies nor downloads data. Linux resource measurements are
required; other operating systems were not checked. Keep this measured harness
unchanged and use a new dated record for a different implementation.

This is additional reproduction evidence for the benchmark usability fix,
not a new quality gain or an additional merged Villa contribution. The two
prepared October form answers and the submission candidate remain unchanged.
The registered augmentation comparison and live research checkout were not
accessed or deployed as part of this CPU check.
