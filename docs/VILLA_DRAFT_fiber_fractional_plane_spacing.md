# Draft: fiber volume seeding keeps fractional planes on the global grid

Local draft only. Add the human motivation/verification required by Villa's
[contribution guidelines](https://github.com/ScrollPrize/villa/blob/f4af1dc1ea664321e38d7c84fadb1a271694425e/CONTRIBUTING.md)
and capture the actual command output for the submission before opening it.
Do not check the personal-verification box on someone else's behalf.
The captured validation transcript is saved at
`reports/evidence/villa_fractional_plane_spacing_2026-10-20.txt`; a visual
record of the real command run is still needed for Villa's bugfix guidelines.

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

**Proof:** On masks from Scrolls 1, 3 and 5, the default 64-voxel setting
produces identical positions, directions, values, families and plane names.
At 52.733333... the seed counts change 1589 → 1590, 11213 → 11175 and
1154 → 1151, respectively. These are thresholded model masks averaged
2x2x2 to uint8 presence, not synthetic data or full tracer inference.
The twelve regression cases exercise all axes, fractional and integer
spacing, tiling invariance, and subvoxel spacing. Current main: 9 fail /
3 pass; patched: 12 pass.

**Why / where this is useful:** The physically matched seeding study needs
noninteger spacing when comparing 7.91 and 9.6 µm inputs. This fixes the
placement it requests. It does not establish a quality improvement, and
full GPU tracing has not been run with the patch.

- [ ] I personally verified that the example and proof above were produced
      by this PR on the stated data.

## Details

* Current base: `f4af1dc1ea664321e38d7c84fadb1a271694425e`, including #2165.
  Seeding functions are unchanged from `9f025888`, where the real-data
  comparison ran; the regression tests were repeated on the current base.
* Production change: four added lines, two removed. Smoothing, Hessian,
  fill-in seeding and tracing rules are unchanged.
* Data: ScrollGT v0.8.1 masks for `s1_00497_01497_03997_256`,
  `s3_00994_00494_01994_512`, `s5_03997_01497_03997_256`.
* CPU runtime: Python 3.10.21, NumPy 2.2.6, SciPy 1.15.3, PyTorch 2.9.1;
  the package's requested Python 3.14 / PyTorch >=2.12 stack is not
  available here. The top-level NRRD import is bypassed for unit tests;
  the seed functions and their dependencies are not stubbed.
* Reproduction commands, input and output hashes:
  `reports/villa_fractional_plane_spacing_2026-10-20.md` and its JSON.
