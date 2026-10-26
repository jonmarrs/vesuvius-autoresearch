# October benchmark reproduction and scorer memory fix

The final-week plan called for a usable public-data example. A fresh sparse
checkout of ScrollGT v0.9.0 reproduced the held-out Scroll-5 target's published
connected-components row exactly. The Scroll-3 512³ control failed in SciPy's
full-volume distance transform under a 7 GiB address-space limit.

The merged [ScrollGT PR #14](https://github.com/jonmarrs/scrollgt/pull/14)
processes both tolerance growth and precision in 64-plane z slabs with a
`ceil(tolerance)` halo. It preserves the scorer's nearest-label behavior and
skips empty halos, preventing an artificial outside seed from wrapping to a
label at the opposite end of the volume.

| Target | v0.9.0 baseline | Patched scorer |
| --- | --- | --- |
| `s5_13497_01497_02497_256` | 9.04 s; 1.06 GiB peak RSS; exact published row | 7.04 s; 0.57 GiB peak RSS; exact published row |
| `s3_00994_00494_01994_512` | MemoryError after 33.55 s, at 5.50 GiB RSS | 54.93 s; 2.57 GiB peak RSS; exact published row |

All commands used the same **7 GiB address-space limit**, one thread and the
same inputs and runtime. The failure was an allocation refusal, not an OOM
kill. There was one timed run per case; no general throughput claim follows.

Both patched rows match all 15 published fields. On the real 256³ input,
every grown-label voxel and every unrounded score field, including the
run-length list, also equal the original whole-volume implementation. The
512³ baseline does not finish under this budget, so its comparison is to the
released row rather than a completed local baseline. Scoring version remains
3. No model, annotation, ground truth or published score is changed.

The [walkthrough](https://github.com/jonmarrs/scrollgt/blob/38496eb8ce5dc094c94ec852a332ee2293ea73a1/docs/FIBER_SCORER_MEMORY.md)
has commands, input and source hashes, raw scorecards, the measurement method
and limits. It compares two held-out examples of different scrolls and cube
sizes; it does not average their ERLs or infer a scroll effect. Validation used
cached Python 3.10.21, NumPy 2.2.6 and SciPy 1.15.3 on Linux x86-64. No package
installation, fresh model inference or GPU tracing was performed.

This is a benchmark usability improvement, separate from the three merged
Villa fixes in the engineering prize bundle. The released v0.9.0 remains the
research filing's versioned benchmark reference; the new patch is identified
by its PR and measured source commit.

The focused fiber suite passed 213 tests (10 optional heavy cases deselected by the existing configuration), and GitHub CI passed.
