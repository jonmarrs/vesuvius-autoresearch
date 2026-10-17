# Design and architecture review — the ink ablation study and the SegFormer reproduction

Date: 2026-10-17. Baseline: `6ef91dc9` (main after #104). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: two areas no earlier review covered.
- `repro/ink_ablation/` with `scripts/run_ink_ablation.py` and `scripts/measure_calibration_transfer.py`: the
  released PHerc.1667 ablation checkpoints run on Scroll 1.
- The four reports it backs: `ink_ablation_scale_bug.md`, `ink_ablation_transfer_result.md`,
  `ink_ablation_second_segment.md` and `ink_calibration_does_not_transfer.md`.
- `repro/ink_segformer/`: the 224 px SegFormer positive control, with FINDINGS' account of it.

The scripts read checkpoints and data that are not in the repository and write their results to the working
directory, so the reports' numbers were checked for internal consistency rather than against committed data.

## What changed

- **it3 does not clear the misalignment null on segment B, though two places said it did.**
  - `ink_ablation_second_segment.md`'s own table gives it3 p 0.0550 on segment B ("borderline"), and only it0, it4
    and it5 "read both". Yet its summary said "the four highest rungs clearing on both".
  - `ink_ablation_transfer_result.md` said "it3/it0/it4/it5 at p<0.0025" on two segments.
  - `ladder_two_nulls.py` printed the same.
  - All three now give it0, it4 and it5 on both segments, and it3 on segment A only, with the corrections dated.
- **The intensity convention is described as measured.**
  - `run_ink_ablation.py` and `measure_calibration_transfer.py` called `clip(x, 0, 200) / 255` "the documented
    Quick-start convention" that "matches the published prediction" (2.82%).
  - The study's own README measured four conventions on a 2048² window of the home segment. The Quick start as
    written, clip then `Normalize(mean=0, std=1)`, is the identity and saturates like the other two (91–99%). The
    /255 is documented nowhere, and with it iteration-5 fires at 18%, not 2.82%.
  - The docstrings now say it is the only convention tried that does not saturate. `ink_ablation_scale_bug.md`
    carries a dated note to the same effect.
  - The README's "our pipeline runs hot … any result is suspect" paragraph carries a note: the transfer report
    superseded it the same day.
- **The checkpoints are hashed, and kept out of the repository.**
  - `fetch_checkpoints.sh` fetched Hugging Face `main`, unpinned, and the modelling code runs with
    `trust_remote_code`. It wrote 1.9 GB beside itself, into `repro/ink_ablation/it0`–`it5`, which nothing ignored.
  - It now records each member's sha256 in `it$i/SHA256SUMS` the first time its files are all present. Every later
    run checks them and exits non-zero on a change, as on a missing file.
  - `DEST` and `REVISION` override the location and the revision, and `.gitignore` covers the in-place directories.
- **Smaller clarifications.**
  - `ink_calibration_does_not_transfer.md`'s "3.6x to 3.9x" is it5's, while the members shift 3.3x to 7.4x.
  - Its "Limits" paragraph ("six locations per scroll, one segment per scroll … two scrolls") predated the box
    above it.
  - FINDINGS' SegFormer row gives F0.5 0.506 at a threshold chosen on the held-out fragment itself, so the row is
    optimistic. The AUC is selection-free only because the curve was monotone: `train.py` saves its best epoch by
    held-out AUC.
  - `train.py`'s `--val` help says so.

## Verified, no change needed

- **The second-segment report's statistics are consistent.**
  - The exact label-permutation p-values are 1/720 = 0.0014 for ρ = 1, and 6/720 = 0.0083 for ρ = 0.9429 (ρ = 1
    plus the five adjacent swaps).
  - The roll-null p-values are 51/400 = 0.1275 and 25/400 = 0.0625.
  - "Within 0.0034" matches the transfer report's table against the 4096² reproduction.
- **The calibration table** is consistent: all six shift ratios, the 8.0–27.1% home range, the 58.5–88.4% held-out
  range, and the six locations (3 × 2 fractions). The AUC range 0.68–0.72 matches the transfer report's members.
- **The prediction frames line up.** 4096 level-0 px give 1024 model outputs and 512 at ds8, indexed at
  `Y0 // 8` into canon's ds8 preview. The roll null excludes only shifts under 40 px on both axes, and it keeps
  texture statistics exactly.
- **`repro/ink_segformer`.** The TTA inverses (rot90 and flip), the masked BCE and Dice, F0.5 (β² = 0.25) and the
  overlap-averaged inference are correct.

## Observations for the owner (not changed)

- **The ScrollGT label these AUCs score against carries the old warp's shift.** The 2026-10-17 warp review covers
  this, and both reports already note it. The ladder's magnitudes move with any re-export.
- **The calibration check's tolerance is loose.** `measure_calibration_transfer.py` accepts a home rate from 0.2× to
  5× the member's own published preview. For it5 that is anything from 5% to 131%. It is a threshold, so it is the
  owner's call.
- **Results are not committed.** The ladder scripts write their JSON and caches to the working directory, and the
  reports' tables have no data beside them in the repository.
- **Absolute paths.** The ladder scripts read `/home/jon/...` and `preds_*.npz` from the working directory, as other
  analyses here do.
- **Revisions.** Hugging Face was not reachable from this review, so the checkpoints' revisions could not be pinned.
  On the owner's machine, the first run of the new `fetch_checkpoints.sh` over the existing `it0`–`it5` records the
  hashes of the files the 2026-08-30 runs used.

## Verification

Environment: CPython 3.10 venv (no GPU visible), pytest, Ruff. No checkpoint or scroll data here.

- The fetcher, simulated with placeholder files in a `DEST`:
  - the first run records six `SHA256SUMS`;
  - a second run verifies them, rc 0;
  - after one byte of `it3/modeling_inkdetection.py` changes, it prints `CHANGED it3` and exits 1.
- `.gitignore`: `git check-ignore` matches `repro/ink_ablation/it0/model.safetensors`.
- Ruff is clean on the changed Python files.
- `tests/test_ink_repro_{losses,dataset,model}.py`: 6 passed. No test reads the reports or scripts edited here.
- The standard suite: see the PR.
