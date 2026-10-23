# Next Villa contribution: bounded native ink retries

Checked 2026-10-23 UTC against Villa `e2254ebe`. Issue
[#1482](https://github.com/ScrollPrize/villa/issues/1482) remains live: native
ink sample retries can enter a deterministic cycle and hang a worker.
The earlier [#1921](https://github.com/ScrollPrize/villa/pull/1921) by @ge-al
was closed unmerged by the inactivity bot. Its comments contain no maintainer
rejection of the fix. Searches by issue number and native/resampling terms
found no active replacement. This candidate follows that issue and prior PR.

## Prepared fix

Branch `fix/native-retry-cycle` in `/workspace/villa-native-retry`, commit
`337c0783f1c4a3f09421bfe5fb9ee5eb4bb2dacb`:

- Track attempted native patches and try each at most once.
- Keep the ordinary seeded replacement chain. Escape a repeated index by
  advancing to an untried one without allocating a full dataset index list.
- Bound attempts at `min(dataset size, 64)`, following #1921. Report the
  attempts and dataset size; a budget failure is not proof that every patch
  in a larger dataset is invalid.
- Preserve flat sampling, a successful first native sample and the existing
  single-patch failure.

The production change is +17 lines. The nine new test cases cover both
native modes, escape to an admissible patch outside a cycle, ordinary seeded
ordering, the retry budget, first-sample success, flat sampling and the
single-patch error and negative indices. A revisit guard makes baseline failures quick and safe.

- [Portable patch](../docs/villa_pr_native_retry_cycle.patch)
- [PR description](../docs/VILLA_DRAFT_native_retry_cycle.md)
- [Reproduction probe](../repro/ink_native/check_retry_cycle.py)

## Actual verification

| Check | Baseline | Patch |
| --- | --- | --- |
| Nine new retry cases | 5 failed, 4 passed | 9 passed |
| Existing native-data cases | Not rerun on baseline | 4 passed, 40 deselected |
| Deliberately supplied invalid mesh regions | 7,358 attempts; watchdog after 2.009 s | 2 attempts; clear RuntimeError |

The existing cases include the replacement-chain test and native sample
equivalence with and without support bands. The timing is evidence of
termination, not a throughput benchmark.

The final combined run passes all **13 selected cases, 40 deselected**. Review
also caught negative indices counting the same logical patch under two
indices; attempted indices are now canonicalized after the normal list
lookup, preserving out-of-range errors. The added negative-index regression
fails on main and passes with the fix. The Autoresearch smoke check reports
**8/11 passed, 3 skipped, 0 failed in 6.4 s**; its skips need absent training
data or the unavailable bg2 augmentation entry point.

The [before](evidence/villa_native_retry_before_2026-10-23.json) and
[after](evidence/villa_native_retry_after_2026-10-23.json) probe records bind
the measured code and input hashes. Captured test summaries are in
[the validation transcript](evidence/villa_native_retry_validation_2026-10-23.txt).

## Real geometry, explicit scope

Input: the published PHercParis4 `20230702185753` mesh on scan
`20260411134726`, at 2.4 µm. Its full-resolution grid is 50,600 by 36,400.
The supplied patches are the top-left and top-right 64-by-64 regions, both
with zero valid tifxyz points. They are selected deliberately to exercise
the rejection consumer, not discovered from a training configuration.

The probe calls the actual `InkDataset` constructor, `__getitem__`,
`_native_sample`, geometry rejection and tifxyz reader. `_open` supplies
sentinel handles that fail on voxel reads: these regions are rejected
before image, ink-label or supervision pixels are needed. No crop decision
or retry result is stubbed. It demonstrates the reported cycle using real
geometry without claiming a full native training reproduction or a default
discovery failure. It does not change model outputs or measure accuracy.

Download the four files into a new directory:

```sh
mkdir mesh
for name in meta.json x.tif y.tif z.tif; do
  curl --fail --location --output "mesh/$name" \
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/20230702185753/mesh/20230702185753-on-20260411134726-2.4um.tifxyz/$name"
done
PYTHONPATH=/path/to/villa/vesuvius/src python \
  /path/to/autoresearch/repro/ink_native/check_retry_cycle.py \
  --mesh mesh --out new-probe.json
```

Run once against the unpatched checkout and once against the patched one,
using different output paths. Expected probe statuses are 1 for the baseline
timeout and 0 for the patched, bounded error. Output files are never
overwritten. The probe checks input SHA-256 hashes and uses a POSIX watchdog.

## Runtime and limitations

CPU validation used cached Python 3.10.21 packages. The top-level `vesuvius`
and `vesuvius.data` package initializers were bypassed to avoid the unrelated
missing NRRD import. The missing `fft_conv_pytorch.fft_conv` augmentation
symbol was supplied as a sentinel that raises if called; these cases use
no FFT augmentation. No retry, geometry or tifxyz implementation was stubbed.
The complete dependency stack requested by current Villa was not available,
and no packages were installed. Full training, GPU and Windows validation
remain unmeasured.

The production Villa pin and registered scientific studies remain unchanged.
This is a new prepared contribution, not a claim that the upstream issue
is closed or that the existing three PRs have merged.
