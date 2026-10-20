# Villa contribution review: fractional fiber seed planes

Checked 2026-10-20. The next concrete contribution is a small correction to the
neural fiber volume tracer's fractional `--plane-spacing`. It arose while
preparing the physically matched seeding study following findings 91 and 92.

The fix is prepared locally, with a PR draft and regression tests. Nothing new
has been posted to Villa. The tracing experiment remains unrun.

## Current upstream queue

| Contribution | Verified state | Next action |
| --- | --- | --- |
| [#2141](https://github.com/ScrollPrize/villa/pull/2141), read-only SQLite track DBMs | Open. The fallback's author independently tested Windows 11 / Python 3.12.10: baseline fails; patched reader passes, 2 passed / 2 skipped. [Their reply](https://github.com/ScrollPrize/villa/pull/2141#issuecomment-6290970541) ends **“LGTM”**. | Keep the focused PR as submitted; record the independent validation. |
| [#2155](https://github.com/ScrollPrize/villa/pull/2155), pip CUDA dependency group | Open; no human comment when checked. | Keep the focused PR as submitted. |
| Fractional plane placement | Reproduced on real published masks, fixed locally, 12 regression cases pass. | Review the [draft](../docs/VILLA_DRAFT_fiber_fractional_plane_spacing.md), then supply the human motivation and verification Villa requests before publication. |

Searches of current issues and PRs for `plane-spacing`, `tile_dots`, and
`fractional` + `fiber` found no contribution fixing this calculation. The
related results describe rendering scale or interpolation, not fiber seed
planes. Many other current defects already have active fixes; duplicating
them would add review work. Our published-data issues such as #1522 and #1654
also do not automatically imply a code patch in Villa.

## Defect and change

The CLI accepts a floating-point spacing. `tile_dots` nevertheless advanced
planes with `range(..., int(spacing))`. The fractional part was lost at every
step, so planes drifted from the requested global grid and could differ when
the same region was split into tiles. A positive spacing below one raised
`ValueError: range() arg 3 must not be zero`.

The proposed arm A asks for `64 * 7.91 / 9.6 = 52.733333...` grid voxels.
On a published Scroll-1 mask, the old code seeded `z0`, `z52`, `z104`;
the corrected code seeds `z0`, `z52`, `z105`. Each global multiple is now
quantized individually to an integer sampling plane. Duplicate quantized
planes are visited once when spacing is below one voxel.

The upstream diff is **+4/-2 production lines**, plus 42 lines of tests.
It leaves the smoothing, Hessian, fill-in seeding, model and stop rules alone.

Prepared Villa branch: `fiber-fractional-plane-spacing` in
`/workspace/villa-upstream-review`; commit `1ee851d` on current upstream
`f4af1dc1ea664321e38d7c84fadb1a271694425e`. The portable change is
[`docs/villa_pr_fiber_fractional_plane_spacing.patch`](../docs/villa_pr_fiber_fractional_plane_spacing.patch).

## Real-data evidence

Inputs are ScrollGT **v0.8.1**'s published `fiber_hz_vt` binary masks, not
synthetic fibers and not the full probability volumes from findings 91/92.
Each mask is averaged over 2x2x2 voxels and converted with
`round(255 * mean)` to the uint8 presence grid, using threshold 128,
dot radius 2 and fill spacing 4. This is a seeding-stage check, not another
measurement of those findings or a new tracing-quality result.

Total seed dots, before → after:

| Cube | Default spacing 64 | Spacing 52.733333... | Spacing 77.673830... |
| --- | --- | --- | --- |
| `s1_00497_01497_03997_256` | 1497 → 1497 | 1589 → 1590 | 1492 → 1492 |
| `s3_00994_00494_01994_512` | 10863 → 10863 | 11213 → 11175 | 10821 → 10825 |
| `s5_03997_01497_03997_256` | 1091 → 1091 | 1154 → 1151 | 1096 → 1096 |

At spacing 64, **all five seed arrays are byte-identical** on all three
scrolls: positions, directions, values, families and plane names. The JSON
[evidence](villa_fractional_plane_spacing_2026-10-20.json) records input
checksums, per-array hashes and the planes observed in all nine comparisons.
A different count at fractional spacing is expected; it is not evidence of
better fibers, coverage or ERL.

The real-data comparisons used Villa `9f025888` before upstream advanced.
Rebased onto `f4af1dc`, which includes #2165's tracing-performance changes.
All four seeding functions and their three constants have identical ASTs
between those upstream versions, and between the two patched versions;
[`source equivalence`](villa_fractional_plane_spacing_source_equivalence_2026-10-20.json)
records the hashes. No seeding result was extrapolated across a code change.

## Regression verification and limits

On the **current** upstream base `f4af1dc`:

* Baseline: **9 failed, 3 passed**. All six fractional-spacing axis cases and
  three subvoxel-spacing cases fail; the default-spacing controls pass.
* Patched: **12 passed**. Tests exercise `tile_dots`, all three axes, whole
  versus split tiles, default spacing, and duplicate integer sampling planes.

The actual Villa module was imported for these tests. The test launcher
only supplies a namespace for the top-level `vesuvius` package to bypass its
unrelated, unavailable NRRD reader; no seeding dependency or function is
stubbed. Runtime: Python 3.10.21, NumPy 2.2.6, SciPy 1.15.3, PyTorch 2.9.1.
Villa currently requests Python 3.14 and PyTorch >=2.12; those versions and
CUDA are unavailable here. No packages were installed. Full tracing and
GPU output parity have not been measured. The standalone real-data probe
compiles the same seeding functions directly from the two source files and
requires only NumPy and SciPy.

Captured [validation output](evidence/villa_fractional_plane_spacing_2026-10-20.txt)
includes the regression summaries and all nine real-data comparisons. The
filing's existing number checks also pass: **19 passed, 4 skipped**; the
skips require the separate ScrollGT checkout, which is absent here.

In a configured Villa environment, the regression command is:

```sh
cd /path/to/villa
AGENTS_AGENT_MODE=1 python -m pytest -q \
  vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/test_volume_seeding.py
```

To reproduce the real-data comparison without model dependencies:

```sh
git -C /path/to/villa show f4af1dc:vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume.py > before.py
mkdir -p seeding-data
for pair in s1:s1_00497_01497_03997_256 s3:s3_00994_00494_01994_512 s5:s5_03997_01497_03997_256; do
  curl --fail --location --output "seeding-data/${pair%%:*}_mask.npz" \
    "https://raw.githubusercontent.com/jonmarrs/scrollgt/v0.8.1/data/fibers_${pair#*:}/mask.npz"
done
python repro/fibers/check_fractional_plane_spacing.py \
  --before before.py \
  --after /path/to/villa/vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume.py \
  --data seeding-data --out new-evidence.json
```

The output must be new. The probe verifies the three published input hashes
and refuses any difference in the default-spacing arrays.

## Research consequence

Do not silently substitute this correction into the proposed seeding-scale
study. Its existing CPU counts were measured with the pinned Villa's old
plane stepping. Before registering and launching a follow-up, choose the
code version, freeze it, and recompute its expected seed counts. The
hard-coded smoothing scale remains a separate experimental question; these
small count changes do not establish its effect on tracing quality.

The production Villa pin, historical measurements, preregistered decision
rules, checkpoint and running loop state have not been changed.
