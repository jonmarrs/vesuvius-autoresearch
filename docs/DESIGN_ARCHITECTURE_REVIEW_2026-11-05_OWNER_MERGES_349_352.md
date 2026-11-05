# Design and architecture review — the owner's #349 and #352

Date: 2026-11-05. Baseline: `5142a9d5` (main after #352).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 16:14 UTC firing.
- **#349 bounds the workspace status command's config read.** It merged after round #150's firing and was left for
  this round.
  - `Snapshot.read` opens nonblocking. It checks the opened descriptor is a regular file and its size is within the
    limit, then reads at most limit + 1 bytes. A path swapped for a FIFO cannot make it wait.
  - `workspace_status.py` reads the config through it, with a 1 MiB default budget (16 MiB at most). It records the
    capture's SHA-256.
- **#352 replaces the Hessian's 3×3 eigenvalue solver.**
  - The old closed-form cubic carried fixed absolute epsilons, which fabricated curvature at small scales.
  - Version 2 scales by the largest entry, centres, and returns exact diagonals.
  - `hessian_eigensolver_version: 2` now goes into the benchmark's measurement provenance and the skeleton-label
    metadata.
  - A CPU audit report and its receipt come with it.

This round changes no library code. It does three things:
- corrects one figure in #352's report;
- adds a test binding that report to its receipt;
- extends two tests so they reach the guards they are named for.

## What changed

- **#352's report misquoted one figure** (`reports/fiber_eigenvalue_scales_2026-11-05.md`).
  - It gave the old solver's public-CT vesselness error as "at most 1.0904e-8". The receipt's largest is
    1.0903301804e-8, which rounds to 1.0903e-8. The line now says so.
  - Every other figure in the report matches the receipt.
  - The new `tests/test_fiber_eigenvalue_scales_record.py`, listed in the suite, binds them all:
    - the table;
    - the sign, gate and vesselness figures;
    - the CT hash, crop, baseline commit and runtime.
  - Seven mutants of the report fail it, the old figure among them.
- **#352's normalization test did not reach the normalization** (`tests/test_fiber_eigenvalue_scales.py`).
  - With the max-component scaling removed, all 130 tests passed.
  - At the test's scales, 1e±150, centring and the cubic stay finite without that scaling. Only entries near 1e±154
    and beyond overflow or underflow when squared.
  - The test now also runs at 1e±200. It passes as merged and fails at both new scales with the scaling removed.
- **#349's size check before reading had no test** (`tests/test_text_snapshot.py`).
  - #349's review notes say "its size is checked before reading". With that check removed, all 35 tests passed: the
    read-length check refuses the same files later.
  - The new test makes `fstat` report one byte over the limit while the file's bytes would fit. So only the size
    check can refuse it.
  - It passes as merged and fails with the check removed.

## Verified, no change needed

- **#352's solver is accurate.** I compared it with `numpy.linalg.eigvalsh`, relative to the largest entry.
  - **Random matrices:** about 1e-14 at scales 1e-6 to 1e6. The old solver's error was 6.0 at 1e-6 and 2e-10 at 1.
  - **Rank-1 and near-repeated spectra:** about 2e-8, the √ε limit of any trigonometric solver at a double root. The
    old solver's error was 770 for rank-1 at 1e-6.
  - **Scaling:** results scale with the matrix to about 5e-16 from 1e-100 to 1e100.
  - **Diagonals:** returned exactly, including zero and 1e±300 entries.
- **#352's receipt reproduces where it can be reproduced here.**
  - The synthetic row's errors recompute from the old and new solvers: 1.2580e-5 and 3.2187e-20.
  - So does the zero matrix's old spectrum, ±1.732e-6.
  - The public-CT rows need the CT file and were not re-run.
- **#352's mutants.**
  - Dropping the exact-diagonal branch fails 10 tests. Dropping the centring fails 20.
  - Setting the version to 1 fails the provenance tests in `test_nml_import_contracts.py` and
    `test_fiber_label_generation.py`.
  - Computing the middle root from the third trigonometric formula, instead of from the trace, is an equivalent
    mutant.
- **#349's guards.**
  - Each of these fails a test:
    - the nonblocking open removed;
    - the regular-descriptor check removed;
    - the limit validation removed;
    - the workspace budget bounds loosened;
    - the repository-resolution guard removed;
    - `RuntimeError` dropped from the config handler;
    - the recorded config source dropped.
  - Every other caller of `Snapshot.read` passes an integer constant, so its stricter limit check breaks none.
- **Round #148's floors observation is settled for existing reports.**
  - The measurement provenance now includes the eigensolver version, so a floors refresh no longer carries a prior
    report's `tracer_strict_relink` row.
  - Every existing report predates the field. The new contract test covers a missing version and version 1.
  - A future walk change alone would still not be detected, because the walk version is not in the provenance.

## Observations for the owner (not changed)

- **Repeated roots stay at √ε accuracy**, as #352's report says. The vesselness ratios divide by the two larger
  eigenvalues, which are near-repeated on a tube. The report's public-CT comparison found no gate disagreement.

## Verification

- **The touched modules**, `test_text_snapshot`, `test_workspace_status`, `test_fiber_eigenvalue_scales`,
  `test_fiber_eigenvalue_scales_record`, `test_nml_import_contracts` and `test_fiber_label_generation`, pass.
- **Ruff and mypy.**
- **The standard suite.**
- **The test modules outside the suite.**
- **The doc audit**, run alone.
