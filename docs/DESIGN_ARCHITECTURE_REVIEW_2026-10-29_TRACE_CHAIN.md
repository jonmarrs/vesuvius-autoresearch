# Design and architecture review: seed-heading trace completion

Baseline: `33aea5c7` (main after PR #289). This review covers the seed-heading
re-run launcher, restart behavior, completion diagnostics and comparison-record
publication. It does not evaluate a new tracing model or deploy research code.

## Findings and changes

### A failed chain reported success

The shell launcher logged individual `FAILED` traces but always ended with
`CHAIN_COMPLETE` and exit 0. An import probe could also exit nonzero after
printing the expected source path and still pass the source check. These are
control-flow errors: callers could interpret an unsuccessful verification run
as completed engineering evidence.

Failed/incomplete traces now produce `CHAIN_FAILED` and exit 1. All four cases
are still attempted so their individual logs remain available. Completion is
checked again before the final success event. Import probes must exit 0;
setup/inspection refusals exit 3. Setup directory creation and source publication
fail explicitly rather than falling through. Historical records are unchanged.

### Resume and analysis trusted historical completion

The old launcher skipped a run if an AFV existed or any earlier `DONE` appeared
in the log. The old comparison also accepted any `DONE`. A later failed attempt,
missing files or interrupted tile could therefore coexist with an apparently
completed run.

The new standard-library `seed_heading_chain_status.py` owns the mechanical
completion rule shared by the launcher and comparison. The latest run event
must be `DONE`; a later `TRACE` or `FAILED` invalidates it. Nonempty run metadata,
tile records and finished tiles must remain, with no partial tiles. The legacy
AFV launcher additionally requires its export. `SKIP_DONE` is informational and
cannot establish completion on its own.

The status CLI returns JSON and exit 0/1/2 for complete/incomplete/unknown. It
does not load arrays, checkpoints, the scorer or GPU libraries, and writes no
research state. Its scope explicitly leaves contents and input identity
unverified. The comparison checks all four runs before importing ScrollGT, then
retains its numerical tile/AFV comparison and scoring behavior.

### Concurrent use could mix work or replace a record

Two launchers could edit the same work directory and append to the same log.
A `chain.lock` lease now serializes that directory, including source preparation.
It is inherited by the trace process, so that process retains the lease if its
launcher is killed. A refused second launcher leaves the chain log untouched.
Relative/symlink work paths are resolved before changing working directory.
This lease is scoped to `W`; it is not a global GPU reservation or a replacement
for the existing research-host checks.

The comparison's initial existence check also left a race between concurrent
publishers. A record is now fully written, flushed and closed under a temporary
name, then published with an exclusive hard link. An existing target is kept;
temporary files are removed on failure. New record permissions follow the
umask. This requires a local filesystem supporting hard links.

## Verification

The shell tests execute the real launcher and status helper with a stub tracer
and prepared fixture sources. They cover nonzero trace exits, successful exits
with missing/partial outputs, deleted outputs on resume, failed attempts with
leftover files, import-probe failure, concurrent launches, malformed history,
relative symlink paths with spaces and a killed launcher with a surviving
worker. No native tracer, GPU job or live study is involved.

The comparison tests read real small NPZ/JSON fixtures. Its successful `main()`
test substitutes only the external scorer/rasterizer boundary. Other tests check
early refusal, latest-attempt gating, preserved existing records, a concurrent
publisher, final permissions and temporary-file cleanup. Scorer quality is not
assessed by those fixtures.

```sh
MPLCONFIGDIR=/tmp/vesuvius-chain-mpl XDG_CACHE_HOME=/tmp/vesuvius-chain-cache \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python -m pytest -q -rs \
  tests/test_seed_heading_chain_status.py tests/test_villa_seed_heading_rerun.py \
  tests/test_villa_draft_volume_seed_heading.py \
  tests/test_validation_suite_covers_the_loop.py tests/test_file_modes.py
```

The same shell fixture reproduces eight failures with the baseline launcher:
three failed/incomplete trace modes, two bad resume cases, ignored import exit,
missing work-directory exclusion and malformed history accepted. The new status
suite is registered in the curated validation runner.

Final targeted result: **62 passed, 2 skipped in 26.83s**. Both skips require
the absent Villa checkout for its patch/source tests. The work-lease tests also
verify that existing lease contents survive refusal and that symlink/directory
lease paths are rejected before tracing.

CPU smoke: `scripts/smoke_test.py` passed 8 checks, skipped 3 and failed 0.
The skips are two unavailable training URI/inklabel checks and the unavailable
batchgeneratorsv2 transform. Ruff check/format, targeted mypy on the five changed
Python files, `bash -n` and `git diff --check` pass. The verification environment
uses Python 3.10 and the frozen lockfile's dependencies.

The full repository suite, native Villa tracing, public-CT identity, real
ScrollGT scoring and cross-host/process-tree recovery were not rerun. No model
training, deployment, live-study measurement inspection or prize submission was
performed; existing research results and filing answer texts are unchanged.
