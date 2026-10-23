# Villa contribution review: fractional fiber seed planes

Checked 2026-10-20. The next concrete contribution is a small correction to the
neural fiber volume tracer's fractional `--plane-spacing`. It arose while
preparing the physically matched seeding study following findings 91 and 92.

Updated at the 2026-10-22 publication review. The fix has real-data CPU
evidence and regression tests. Full tracing with this patch remains unrun.
The separate registered seeding-scale study completed on its pinned,
unpatched Villa code: [finding 93](neural_tracer_seeding.md). All three
predictions failed; this engineering fix does not revise that conclusion.

## Current upstream queue

| Contribution | Verified state | Next action |
| --- | --- | --- |
| [#2141](https://github.com/ScrollPrize/villa/pull/2141), read-only SQLite track DBMs | Open; maintainer feedback addressed in `19575a45`: route all SQLite stores through the reader and preserve existing WAL commits. Five tests pass; the two new regressions fail on the prior PR head. Earlier [Windows validation](https://github.com/ScrollPrize/villa/pull/2141#issuecomment-6290970541) covered the original sidecar fix. | Await upstream review and merge permission. |
| [#2155](https://github.com/ScrollPrize/villa/pull/2155), pip CUDA dependency group | Merged 2026-10-21 Pacific, `e016bc71d9b873b3e52871f42aa3e7a34520cfb1`. | Recorded in the October filing. |
| Fractional plane placement | Reproduced on real published masks; 20 regression cases pass on rebased `242f0798`. | Publish the reviewed fix with its real-data evidence. |

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

The registered arm A used `64 * 7.91 / 9.6 = 52.733333...` grid voxels.
On a published Scroll-1 mask, the old code seeded `z0`, `z52`, `z104`;
the corrected code seeds `z0`, `z52`, `z105`. Each global multiple is now
quantized individually to an integer sampling plane. Duplicate quantized
planes are visited once when spacing is below one voxel.

**Follow-up review:** the initial candidate allocated the nominal subvoxel
planes before deduplicating them. At spacing 1e-9, a 16-voxel interval could
request 16 billion entries. The final patch instead caps sampling density
at one plane per voxel before allocating the indices and rejects zero,
negative and nonfinite spacing. Three allocation-guard tests fail on the
initial candidate and pass on the final patch without requesting large arrays.

The upstream diff is **+8/-2 production lines**, plus 58 lines of tests.
It leaves the smoothing, Hessian, fill-in seeding, model and stop rules alone.

Prepared Villa branch: `fiber-fractional-plane-spacing` in
`/workspace/villa-upstream-review`; reviewed commits `b3fe95e4` and `242f0798`
on upstream `e2254ebe`. These rebase the measured `1ee851d` / `550ff31`
patch without changing the production source bytes. The portable change is
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
[final evidence](villa_fractional_plane_spacing_final_2026-10-20.json) records input
checksums, per-array hashes and the planes observed in all nine comparisons.
A different count at fractional spacing is expected; it is not evidence of
better fibers, coverage or ERL.

The initial real-data comparisons used Villa `9f025888` and the first
candidate; those [original measurements](villa_fractional_plane_spacing_2026-10-20.json)
and the [initial rebase equivalence](villa_fractional_plane_spacing_source_equivalence_2026-10-20.json)
remain recorded. After hardening the patch, all nine comparisons were repeated
against **upstream `f4af1dc` and final commit `550ff31`**. Every result row,
including every seed-array hash, equals the initial measurement. The final
JSON binds the repeated measurements to the measured source-file hashes.
Those complete production files are byte-identical on the reviewed rebased
branch (`e2254ebe` / `242f0798`); all 20 unit cases pass on that base too.

## Regression verification and limits

On the measured upstream base `f4af1dc`:

* Baseline: **17 failed, 3 passed**. The default-spacing controls pass.
* Patched: **20 passed**. Tests exercise `tile_dots`, all three axes, whole
  versus split tiles, default spacing, bounded subvoxel sampling and invalid
  spacing values. The initial candidate separately fails the three
  allocation guards: **3 failed, 3 passed, 14 deselected**.

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
filing's number checks originally passed: **19 passed, 4 skipped**. At the
2026-10-22 publication review, the filing-number, merge-claim and registered
seeding-analysis suites together pass **81 tests, 4 skipped**. The skips
require the separate ScrollGT checkout, which is absent here. The frozen
preregistration is identical to main; no registered experiment was changed.

The [visual record](figures/villa_fractional_plane_spacing_2026-10-20.png)
is a screenshot of the local validation report containing captured stdout
from a fresh real-data check: the check exits 1 on upstream's seeding
functions with `z0, z52, z104`, and exits 0 on the final patch with
`z0, z52, z105`. These are the check's exit codes, not a full tracing CLI run. The
[HTML source](evidence/villa_fractional_plane_spacing_visual_2026-10-20.html)
labels this as CPU seeding, and the raw transcripts are retained alongside
the combined validation output. It is not a claim of full tracing quality.

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

For the shorter example captured in the visual record, run the same command
once for baseline `before.py` and once for patched `volume.py`:

```sh
python -m repro.fibers.check_fractional_plane_spacing_example \
  --volume before.py --mask seeding-data/s1_mask.npz
```

## Research consequence

Do not silently substitute this correction into the completed seeding-scale
study. Finding 93 ran all 42 registered runs with pinned Villa `ccb431818`
and its old plane stepping. Arm A's median ERLpen was 0.67 of native and
arm B's 0.88; all three predictions failed. Any tracing comparison with this
patch requires a new frozen code version and study. The small seed-count
changes here establish no effect on tracing quality or explanation for the
negative registered result.

The production Villa pin, historical measurements, preregistered decision
rules, checkpoint and running loop state have not been changed.
