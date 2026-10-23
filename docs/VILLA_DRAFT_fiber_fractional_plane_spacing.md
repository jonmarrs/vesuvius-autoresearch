# Draft: fiber volume seeding keeps fractional planes on the global grid

PR description prepared from the measured research workflow. Villa's
[contribution guidelines](https://github.com/ScrollPrize/villa/blob/f4af1dc1ea664321e38d7c84fadb1a271694425e/CONTRIBUTING.md)
request human commentary; the personal attestation below remains unchecked.
Do not check the personal-verification box on someone else's behalf.
The captured validation transcript is saved at
`reports/evidence/villa_fractional_plane_spacing_2026-10-20.txt`. The visual
record at `reports/figures/villa_fractional_plane_spacing_2026-10-20.png`
is a screenshot of captured real-data CPU check output. Include it with the
submission and preserve that scope description.

---

**In one sentence:** Fractional `--plane-spacing` values now place fiber
seeds on the requested global grid, consistently across tile boundaries.

**One real example:** While preparing a seeding-scale comparison at
`64 * 7.91 / 9.6 = 52.733333...` grid voxels, Villa's CPU seeding stage on
the published ScrollGT `s1_00497_01497_03997_256` mask used `z0`, `z52`,
`z104`; the corrected calculation uses `z0`, `z52`, `z105`.

**Before:** The argument is a float, but the plane loop advances by
`int(plane_spacing)`. The error accumulates within each tile. Positive
spacing below one also raises `ValueError` from a zero `range` step.

**After this PR:** Each global multiple is quantized separately to an
integer plane; repeated integer planes are sampled once.
The sampling density is bounded to one plane per voxel before allocation;
zero, negative and nonfinite spacing are refused.

**Proof:** On masks from Scrolls 1, 3 and 5, the default 64-voxel setting
produces identical positions, directions, values, families and plane names.
At 52.733333... the seed counts change 1589 → 1590, 11213 → 11175 and
1154 → 1151, respectively. These are thresholded model masks averaged
2x2x2 to uint8 presence, not synthetic data or full tracer inference.
The twenty regression cases exercise all axes, fractional and integer
spacing, tiling invariance, bounded subvoxel spacing, and invalid values.
Baseline `f4af1dc`: 17 fail / 3 pass; patched: 20 pass.

**Why / where this is useful:** Comparing physical seed spacing at 7.91 and
9.6 µm requires noninteger grid spacing. This fixes the placement requested
by that workflow. The registered study has since completed on its pinned,
unpatched Villa version (finding 93); all three predictions failed. This
patch does not change that result or establish a quality improvement.
Full GPU tracing has not been run with the patch.

- [ ] I personally verified that the example and proof above were produced
      by this PR on the stated data.

## Details

* Reviewed branch: `242f0798cbf3d512f372db050be08203018e71d1` on
  `e2254ebe` (20 tests pass). All nine real-data comparisons used the same
  production source bytes before the rebase (`f4af1dc` / `550ff31`);
  the original measurements and source hashes are retained.
* Production change: eight added lines, two removed. Smoothing, Hessian,
  fill-in seeding and tracing rules are unchanged.
* Data: ScrollGT v0.8.1 masks for `s1_00497_01497_03997_256`,
  `s3_00994_00494_01994_512`, `s5_03997_01497_03997_256`.
* CPU runtime: Python 3.10.21, NumPy 2.2.6, SciPy 1.15.3, PyTorch 2.9.1;
  the package's requested Python 3.14 / PyTorch >=2.12 stack is not
  available here. The top-level NRRD import is bypassed for unit tests;
  the seed functions and their dependencies are not stubbed.
* Reproduction commands, input and output hashes:
  `reports/villa_fractional_plane_spacing_2026-10-20.md` and its JSON.
