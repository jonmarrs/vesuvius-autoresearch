# Design and architecture review — the labeled dataset, and one upstream metric defect

Date: 2026-10-13. Baseline: `73c9283e1e9d37481bea57b6540785d5baaba1b9` (main after the
training-step review, finding 86 and the density-scan test fix). Villa pin:
`9afddaf0fdc12efe088bab7b82534c4f9a79e536`; villa `origin/main` checked at `4eecd08fd`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `VesuviusLabeledDataset` in `src/vesuvius_autoresearch/core/vesuvius_loader.py`, which
produces every training and validation patch the loop sees (15 call sites across `scripts/`):
label and mask loading, the label/volume alignment guard, intensity normalisation, the ridge
channel, the Frangi fiber target, and their failure modes. Plus, following the owner's guidance
that the September Progress Prize credited "assorted useful merged villa PRs", one defect found
upstream during the previous reviews, prepared as an SOP-shaped villa patch.

Out of scope, because finding 86 (`reports/loop_v2_constant_control.md`) lists them as the owner's
decisions: the lasagna flattening that has never run on the GPU host, the F1 metric's all-ink
floor, and the noise-tolerance calibration.

## What changed

The ridge channel uses the GPU result instead of discarding it and recomputing on the CPU; a ridge
failure is reported, and is fatal under `strict_reads` (validation), instead of silently becoming
an all-zero channel. A label or mask whose size differs from its volume by more than 2 px per axis
is refused instead of accepted up to 20%. A villa patch and draft PR for `centerline_dice` are
added under `docs/` for the owner to submit.

## Correction: the density-scan regression in #43

PR #43 (the loop review) made the loader refuse a catalogue with no qualifying patch. That broke
`tests/test_spatial_inspection_contracts.py::test_density_fallback_does_not_claim_at_least_one_ink_pixel`,
which #44 fixed. #43's verification listed that test among "environmental" shared failures,
because its baseline worktree imported the **branch's** `src/` through the shared venv's editable
install, so the baseline failed it too. This review's baseline sets `PYTHONPATH` to the worktree's
own `src/` and asserts, before running, that `vesuvius_autoresearch` resolves inside the tree under
test.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The ridge channel was computed twice per patch, and could silently become zeros.** `_compute_ridges` ran `detect_ridges` on the GPU, then moved the result with `.to(self.device)` — an attribute `VesuviusLabeledDataset` never sets. The `AttributeError` sent every patch to the CPU path, which recomputed the ridges (52 ms per 24×64×64 patch on this review's CPU, ~0.2 s per training step at batch 4). If the CPU path failed too, a bare `except` substituted zeros with no message, unlike `FastVesuviusVolume`'s ridge path, which warns. Production runs `use_ridges: true`, so a ridge failure changes one of the two input channels without trace. | The GPU result is used (`cupy` absent is a quiet CPU path); a GPU failure warns and falls back to the CPU; a CPU failure raises under `strict_reads` (the promotion sample since protocol v2) and otherwise warns before substituting zeros. |
| P2 | **The label/volume guard accepted a 20% size difference.** It was written to catch a transposed volume (a ×5 mismatch) and allowed "minor resolution/crop differences" up to 20% of each side — 1,636 px on the 8,181 px training fragment. A label of a different crop or scale is misregistered everywhere, and the patch sampler's clamping does not realign it. Exports of the same segment differ by rounding: across the eight registered segments in `reports/scorer_vs_labels.json`, label and surface shapes differ by 0 or 1 px. | `LABEL_SHAPE_TOLERANCE_PX = 2`; a larger difference raises, naming the sizes and saying whether it looks like a transposed volume or a different crop/scale. |
| Upstream | **Villa's `centerline_dice` exceeds 1 on slices without ground truth.** `dist_transform` starts at zeros and is filled only where the ground-truth skeleton is non-empty, so every predicted skeleton pixel on an empty slice counts as a hit. Live at villa `origin/main` (`4eecd08fd`); villa's `segmentation/evaluation/configs/recto.yml` and `recto-verso.yml` run it on volumes. | `docs/villa_pr_centerline_dice_empty_slices.patch` (+2/−1: start at infinity) and `docs/VILLA_DRAFT_centerline_dice_empty_slices.md`, written to the SOP (one defect, pasteable evidence, no AI-authorship markers in the villa-facing text). **Not posted**: opening it is the owner's call, after the issue search the draft lists. |

## Reviewed and sound

- Labels and masks are scaled to [0, 1] when stored as 0/255; the shape guard runs before any
  coordinate is derived from them.
- Intensities are normalised by dtype after flattening (uint8 /255, uint16 via int32 /65535,
  float as is); `FastVesuviusVolume` warns on an unknown dtype.
- The Frangi fiber target uses scikit-image on the CPU (a fix from May), warns on failure, and
  returns the documented `[1, 1, H, W]` shape.

## Architecture and compatibility decisions

**Why a hard failure on size.** A misregistered label poisons training and validation without any
other symptom; refusing costs one crashed cycle and names the sizes. The two loop fragments'
label sizes are not recorded in the repository, so the GPU host should check them before the next
shift (below). If either differs by more than 2 px, that is a registration question for the owner,
not something to tolerate silently.

**Why `strict_reads` decides ridge failures.** Validation has used strict reads since protocol v2,
so an incomplete promotion sample is already counted and blocks promotion; a zeroed channel is the
same kind of incomplete read. Training keeps going with a counted warning, as it does for other
per-patch read failures.

### Before the next shift on the GPU host

```sh
uv run python - <<'PY'
import zarr, numpy as np
from PIL import Image
for frag in ("PHercParis2Fr47", "PHercParis2Fr143"):
    root = f"local_data/{frag}"
    vol = zarr.open(f"{root}/surface_volume.zarr", mode="r")
    vol = vol["0"] if hasattr(vol, "keys") else vol
    for name in ("inklabels_refined.png", "inklabels_filled.png", "inklabels.png", "mask.png"):
        try:
            print(frag, name, Image.open(f"{root}/{name}").size[::-1], "volume", vol.shape[1:])
        except FileNotFoundError:
            pass
PY
```

## Remaining observations (not changed)

- `VesuviusS3Dataset` (the UA-MT unlabeled stream) and the labeled dataset's non-strict reads still
  return zero patches on a read error, with a limited warning. That is resilience for training and
  is counted by its warnings; it is not changed here.
- The lasagna, metric-floor and noise-calibration decisions from finding 86 remain open.

## Verification

Environment: CPython 3.10.20 venv with PyTorch 2.9.1 (no GPU visible), scikit-image, pytest, Ruff
0.9.10, mypy; villa sparse-checked-out at the pin, plus `segmentation/evaluation`. No production
data and no CuPy, so the GPU ridge path is exercised with a stand-in module that mimics CuPy's
`asarray`/`asnumpy`. `$PY` is `.venv/bin/python`.

### Reproductions on the baseline

```text
dataset has .device: False
CPU detect_ridges per patch: 52 ms; shape (24, 64, 64), finite True
per step at batch 4 (training only): 0.21 s
```

Registered segments, `reports/scorer_vs_labels.json` (`shape` is the surface, `label_shape` the label):

```text
20230702185753 [6325, 4550] [6325, 4550]     20231012184424 [6350, 9465] [6350, 9465]
20230929220926 [4010, 9475] [4010, 9475]     20231016151002 [3995, 6495] [3995, 6495]
20231007101619 [6505, 13517] [6505, 13518]   20231031143852 [4272, 5502] [4273, 5503]
20231106155351 [4287, 6405] [4288, 6405]     20231210121321 [6375, 4997] [6375, 4998]
```

Villa `centerline_dice`, two slices, ink on slice 0 only, a predicted stroke on slice 1:

```text
main : {'centerline_dice': 1.3125, 'centerline_length_gt': 22.0, 'centerline_length_pred': 42.0, 'centerline_sensitivity': 1.9091, 'centerline_precision': 1.0}
fixed: {'centerline_dice': 0.6875, 'centerline_length_gt': 22.0, 'centerline_length_pred': 42.0, 'centerline_sensitivity': 1.0, 'centerline_precision': 0.5238}
identical on 200/200 random volumes where every slice has ground truth
applies to 4eecd08fd
```

### Tests

New `tests/test_labeled_dataset_contracts.py` (10 tests). Failing-first with only the loader
reverted:

```text
FAILED test_gpu_ridges_are_used_not_recomputed_on_the_cpu
FAILED test_a_ridge_failure_is_reported_not_silently_zeroed
FAILED test_a_ridge_failure_is_fatal_under_strict_reads
FAILED test_a_label_of_another_size_is_refused[label_hw0-different crop or scale]
FAILED test_a_label_of_another_size_is_refused[label_hw1-different crop or scale]
5 failed, 5 passed in 2.60s
```

The five that pass on the baseline pin behaviour that must not change: the quiet CPU path without
CuPy, export rounding of 0–2 px, and the existing transposition guard.

Every test file that constructs the dataset, on the branch:

```text
235 passed, 3 skipped, 3 warnings in 56.85s
```

### Standard validation, baseline versus branch

`scripts/run_validation_tests.py`'s list (now including the new test file), each tree run with
`PYTHONPATH=<tree>/src:<tree>` and a pre-check that `vesuvius_autoresearch.core.vesuvius_loader`
resolves inside that tree (the package is a namespace package, so `__file__` of the package itself is
`None` and its path spans both trees; the first run of this check caught that and was fixed before any
test ran):

```text
baseline: 42 failed, 1871 passed, 10 skipped, 1 xfailed, 2 errors in 170.02s
branch:   42 failed, 1881 passed, 10 skipped, 1 xfailed, 2 errors in 144.25s
failing ids: baseline=44 branch=44
only failing on branch:
only failing on baseline:
```

Interpretation: identical failing sets, and with the isolation in place no baseline-only artefacts.
The 44 shared failures were each traced, not assumed: `s3fs` missing
(`test_surface_render_contracts.py` 21, `test_sota_gt_register.py`), `tensorstore` missing
(`test_zarr_loading.py`), `numba` missing (`test_mesh_preparation_contracts.py`), and villa paths
outside this sparse checkout (`foundation/volume-registration` for `test_geometry_handoff_contracts.py`
14, `segmentation/vc_proofreader` for `test_label_curation_contracts.py` 6). The ten extra passes are
the new tests.

### Lint, formatting and typing

```text
ruff check / ruff format --check (loader, new tests, validation list): All checks passed!, 3 files already formatted
git diff --check: clean
mypy src/vesuvius_autoresearch/core/vesuvius_loader.py tests/test_labeled_dataset_contracts.py:
  the same 2 errors as the baseline (list-item "Tensor | None" in vesuvius_loader.py)
```

## What was NOT tested

- The CuPy path on a GPU (only a stand-in), and the production fragments' label sizes.
- The villa patch against villa's own CI (it has no tests for this metric); it was not posted.

## Reviewer focus

That 2 px is the right line between export rounding and misregistration, and that the villa draft
reads as one careful fix by the SOP's standard before it goes upstream.
