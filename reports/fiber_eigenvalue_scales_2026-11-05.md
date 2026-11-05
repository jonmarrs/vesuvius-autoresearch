# Hessian eigenvalue numerical correction — CPU audit

The fixed epsilon in the old characteristic cubic changed the spectrum at
small scales. A zero matrix returned approximately ±1.732e-6 instead of zero.
On 1,000 deterministic symmetric matrices scaled by 1e-5, 205 eigenvalue signs
disagreed with NumPy. Version 2 scales and centers the problem, returning exact
diagonal spectra. Its method follows
[Eberly, section 5.1](https://www.geometrictools.com/Documentation/RobustEigenSymmetric3x3.pdf).
The eigenvector validity floor, Hessian derivatives and Frangi formula are unchanged.

This is numerical correctness work supporting the official request for
[reliable fiber connections](https://scrollprize.org/2026_open_problems).
It is not evidence of improved tracing, unwrapping, ink detection or prize eligibility.

## Reproduction

Use the published
[Scroll 1 CT](https://dl.ash2txt.org/datasets/fiber-skeletons/Dataset001_sk-fibers-20250124/imagesTr/s1_00497_01497_03997_256_0000.tif),
16,819,802 bytes, SHA-256
`0d38453cc37157f46b180e3711172e99f56eb216948eb6755eca0019ad0dbf60`.
The offline harness refuses other input bytes and evaluates the 64³ crop
`ct[96:160, 96:160, 96:160]`.

```sh
CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python \
  repro/fibers/verify_eigenvalue_scales.py \
  --ct /path/to/s1_00497_01497_03997_256_0000.tif \
  --baseline-ref da4d1e829bb8bcd6a639cc7953279c5ebe57ceee \
  --out /path/to/new-eigenvalue-audit
```

The [receipt](evidence/fiber_eigenvalue_scales_2026-11-05.json) records source,
harness and input hashes, runtime versions and numerical comparisons. NumPy's
`eigvalsh` sees the same symmetrized Hessian. The reference vesselness path changes
only the eigenvalue routine; all other formula and zero-mask behavior stays fixed.

| Input / settings | Old maximum eigenvalue error | Version 2 maximum error |
| --- | ---: | ---: |
| 1,000 synthetic matrices, seed 4090, scale 1e-5 | 1.2580e-5 | 3.2187e-20 |
| Public CT, Gaussian 2 / Hessian 6 | 2.9357e-8 | 9.8255e-15 |
| Public CT, Gaussian 1 / Hessian 2 | 1.0225e-6 | 4.0593e-15 |
| Public CT, Gaussian 2 / Hessian 3 | 4.6845e-7 | 2.4564e-15 |

The candidate has zero robust sign disagreements on the synthetic sample. Both
solvers have **zero sign or tube-gate disagreements on this public CT crop**.
The old public-CT vesselness error is at most 1.0903e-8; version 2 is within
1.3184e-15. These small real-data differences support a precision correction,
not a claim that detection quality improved. No tracing-quality evaluation ran.

Separately, a controlled quadratic volume with two small positive curvatures
and one negative curvature passes the old tube gate, yielding a positive
vesselness response of about 3.245e-12 where the formula requires zero. A
regression test pins this end-to-end failure without replacing the Hessian or
eigenvalue code at runtime. A tiny response is not a demonstrated false fiber.

## Limits and provenance

Repeated or nearly repeated roots retain the weaker accuracy of a trigonometric
solver; tests use norm-scaled bounds there. Tests also cover float32/float64,
extreme finite scales, near-isotropic inputs and ignored lower-triangle entries.
This run used Python 3.10.21, NumPy 2.2.6 and SciPy 1.15.3 on CPU.
Float32 repeated spectra can still produce spurious valid tangents under the
unchanged eigenvector floor, a pre-existing limitation. The production Hessian
path uses float64. This correction does not certify float32 orientation
degeneracy handling.

No GPU parity, memory or throughput measurement ran for version 2. Earlier GPU
timings and historical tracer results remain observations of the legacy solver.
Benchmark measurement provenance now records `hessian_eigensolver_version: 2`,
preventing floor refresh from retaining a tracer row with missing/old solver
provenance. Skeleton labels record the version too; candidate labels already
record the filter source hash. Neural probability caches and connectivity
scoring versions are unchanged. Existing artifacts are not rewritten.
