# Native ink crop retry — prepared PR

Candidate: [Villa #1482](https://github.com/ScrollPrize/villa/issues/1482).
The earlier [#1921](https://github.com/ScrollPrize/villa/pull/1921) by @ge-al
expired unmerged under the 14-day inactivity rule. This follows that work;
it is not a new diagnosis. No active replacement was found when checked.

Local branch `fix/native-retry-cycle`, commit
`337c0783f1c4a3f09421bfe5fb9ee5eb4bb2dacb`, on Villa `e2254ebe`.

---

**In one sentence:** A rejected native ink crop can no longer trap a
DataLoader worker in a deterministic retry cycle.

**One real example:** A focused CPU probe supplies two deliberately empty
64-by-64 regions from the published Scroll-1 segment `20230702185753` mesh.
The actual native geometry code rejects both. Current main then alternates
between the same patches: 7,358 attempts before the two-second watchdog.
The patched `__getitem__` raises a descriptive error after two attempts.

**Before:** Every rejected patch deterministically selects another patch,
with no cycle detection or attempt bound. An admissible patch outside a
reached cycle can never be selected.

**After this PR:** Each patch is tried at most once, up to 64 distinct
patches. Ordinary seeded replacements stay the same; a repeated replacement
advances to an untried index. Failure reports the attempts and dataset size.
The fallback scans across the small visited set instead of allocating an
index list for the whole dataset.

**Proof:** Nine regression cases pass. On main, five fail and four pass;
the test guard catches a revisit promptly instead of hanging the test
runner. Four existing native-data cases also pass, including the existing
seeded replacement-chain test. Input hashes and both mesh-probe outputs
are preserved in the accompanying report.

**Why / where this is useful:** This completes the unmerged fix for #1482
and makes invalid native crops diagnosable instead of leaving training
workers silent. It preserves flat sampling and successful ordinary retries.

- [ ] I personally verified that the example and proof above were produced
      by this PR on the stated data.

## Details

Production change: +17 lines in `data/dataset.py`, plus nine regression
cases. The existing single-patch error is preserved. The 64-attempt budget
follows #1921; it can refuse a sample even if a valid patch exists elsewhere
in a larger dataset, so the error does not claim every patch is unusable.

```sh
cd vesuvius
python -m pytest -q tests/ink_detection/test_native_retry_bounded.py
python -m pytest -q tests/ink_detection/test_data_foundation.py \
  -k 'native_sample_retry_follows_replacement_chain or native_samples_are_the_same_with_and_without_bands'
```

Local CPU validation used cached Python 3.10.21 dependencies. The unavailable
NRRD package initializers were bypassed, and an unused FFT augmentation import
was stubbed to raise if invoked. Retry logic, native geometry, tifxyz reading
and the selected existing tests used the actual upstream code.

The mesh probe uses the real `InkDataset` constructor, `__getitem__`, native
sample method and tifxyz reader, with an explicitly supplied patch list.
Unused volume handles are sentinels: no image or label voxels are read. It
does not establish that default patch discovery produces those invalid
regions. Full training, GPU behavior and Windows were not tested.

Report: `reports/villa_native_retry_cycle_2026-10-23.md`.
