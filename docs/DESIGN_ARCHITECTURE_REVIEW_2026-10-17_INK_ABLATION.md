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
- **Segment A's null p-values are the centre 2048² crop's, and are now labelled so.**
  - `ladder_segA_null.py` scores the centre 2048² of the 4096² frame. The second-segment report showed its p-values,
    and its ladder ρ +0.9429, beside the full-frame AUCs, where ρ is +1.0000 and it2 reads 0.5317 rather than 0.5510.
  - No null was run on segment A's full frame. The table, the roll-null printout and the transfer report's summary
    now say which crop they are.
  - The second-segment report also said "it1 and it2 sitting at chance on both segments", against its own "reads A
    only" for it2. Corrected: it2 clears the null on A's centre crop (p 0.0100), and the full frame, where the
    first report called it chance, was not tested.
- **The intensity convention: the Quick start's, as the owner's 2026-09-15 retraction says.**
  - albumentations' `Normalize` divides by `max_pixel_value`, 255 by default, so the card's "clip to [0, 200] then
    `Normalize(mean=0, std=1)`" is `clip(0,200)/255` (`docs/VILLA_RECORD_issue1659_input_conventions.md`).
  - The repro README's four-convention table predated that retraction. It still labelled the card prose "the
    identity" and `clip(0,200)/255` "documented nowhere"; its second row measured a clip without the division, which
    nothing documents. The rows are relabelled, the conclusion struck through, and `conventions_home.py`'s labels
    match. The README's Input section said the models take z-score input, which saturates three of the four
    members the scale-bug report measured.
  - `run_ink_ablation.py` said `clip(0,200)/255` "matches the published prediction" at 2.82%. That is canon's rate
    over the whole segment; on a 2048² window it5 fires at 18% with it. The docstring now says so. It also said
    the other two conventions saturate "at 67 to 99%", which holds for it5 but not for every member: on the
    scale-bug report's 512² patch, z-score's it0 and raw's it0, it1 and it4 fire on 3.4 to 12.5%. That report's
    own sentence carries the same clarification.
  - The README's "our pipeline runs hot … any result is suspect" paragraph carries a note: the transfer report
    superseded it the same day.
- **The checkpoints are hashed, and kept out of the repository.**
  - `fetch_checkpoints.sh` fetched Hugging Face `main`, unpinned, and the modelling code runs with
    `trust_remote_code`. It wrote 1.9 GB beside itself, into `repro/ink_ablation/it0`–`it5`, which nothing ignored.
  - Each file now downloads to a `.part` and is moved into place only on success, so an interrupted download is
    fetched again rather than kept.
  - Each member's sha256 is recorded, atomically, in `it$i/SHA256SUMS` the first time its files are all present.
    Every later run checks all four, and exits non-zero on a missing or changed file.
  - `DEST` and `REVISION` override the location and the revision. The header says what the hashes do not do: they
    record the first download, `REVISION` applies only to files not yet present, the hashes live beside the files
    rather than in the repository, and nothing that loads the checkpoints reads them.
  - `.gitignore` covers the in-place checkpoint directories, and the `preds_*.npz` and `canon_*.jpg` caches the
    ladder scripts write when run from that directory. Their small `ladder_*.json` results stay committable.
- **Smaller clarifications.**
  - `ink_calibration_does_not_transfer.md`'s "3.6x to 3.9x" is it5's, while the members shift 3.3x to 7.4x.
    `measure_segment_vintage.py`, which runs it5 only, said 3.3-7.4x.
  - Its "Limits" paragraph ("six locations per scroll, one segment per scroll … two scrolls") predated the box
    above it, which adds two more Scroll 1 segments for it5 and two further scrolls.
  - The transfer report's Limits ("One segment, one scroll") notes the second segment.
  - FINDINGS' SegFormer row gives F0.5 0.506 at a threshold chosen on the held-out fragment itself, so the row is
    optimistic. `train.py` saves its best epoch by held-out AUC; with the curve monotone that is the last, so the AUC
    carries no checkpoint selection. No per-epoch log is committed, and the 18 epochs (the config's default is 25)
    were set after a 6-epoch run had been scored on Fr47. `train.py`'s `--val` help says the checkpoint is selected.

## Verified, no change needed

- **The second-segment report's statistics are consistent.**
  - The exact label-permutation p-values are 1/720 = 0.0014 for ρ = 1, and 6/720 = 0.0083 for ρ = 0.9429 (ρ = 1
    plus the five adjacent swaps). The slope p-values are 1/720, 2/720 and 3/720.
  - The roll-null p-values are whole counts out of 400, among them 51/400 = 0.1275 and 25/400 = 0.0625.
  - "Within 0.0034" matches the transfer report's table against the 4096² reproduction.
- **The calibration table** is consistent: all six shift ratios, the 8.0–27.1% home range, the 58.5–88.4% held-out
  range, and the six locations (3 × 2 fractions). The AUC range 0.68–0.72 matches the transfer report's members.
- **The roll nulls** exclude shifts under 40 ds8 px on segment B and under 160 px on segment A's crop, on both axes,
  and keep texture statistics exactly.
- **`repro/ink_segformer`.** The TTA inverses (rot90 and flip), the masked BCE and Dice, F0.5 (β² = 0.25), the
  overlap-averaged inference, and the train/infer normalisation all match.

## Observations for the owner (not changed)

- **The ScrollGT label these AUCs score against carries the old warp's shift.** The 2026-10-17 warp review covers
  this, and both reports already note it. The ladder's magnitudes move with any re-export.
- **Segment B's frames are offset by half a ds8 pixel in x.** The window starts at level-0 x 37860 (`75720 // 2`),
  which is not a multiple of 8, so canon's ds8 pixel `37860 // 8` starts 4 px earlier
  (`ladder_permutation_null.py`, `ladder_second_segment.py`, `ladder_null_control.py`). The offset is the same for
  every member, so it would lower segment B's AUCs slightly and not reorder them.
- **Ties in the ladder AUCs.** The `ladder_*.py` AUCs rank with an ordinal mergesort, not midranks. If a map has
  many exactly equal values (float32 sigmoid is exactly 1.0 above a logit of about 17), the AUC then depends on raster
  order. Whether the maps tie could not be measured here; `(P[k] == 1).mean()` would show it.
- **The calibration check's tolerance is loose.** `measure_calibration_transfer.py` accepts a home rate from 0.2× to
  5× the member's own published preview. For it5 that is anything from 5% to 131%. It is a threshold, so it is the
  owner's call.
- **Results are not committed.** The ladder scripts write their JSON and caches to the working directory, and the
  reports' tables have no data beside them in the repository.
- **Absolute paths.** The ladder scripts read `/home/jon/...` and `preds_*.npz` from the working directory, as other
  analyses here do.
- **Revisions.** Hugging Face was not reachable from this review, so the checkpoints' revisions could not be pinned.
  The checkpoints the 2026-08-30 runs used are in `/home/jon/openclaw-workspace/Neo-VM/data/ink_ablation/`, so
  `DEST=` that directory would record their hashes on its first run; without `DEST` the script fetches fresh copies
  beside itself. Committing those `SHA256SUMS`, or the Hugging Face commit, would pin them for anyone else.

## Verification

Environment: CPython 3.10 venv (no GPU visible), pytest, Ruff. No checkpoint or scroll data here.

- An independent review of this round's first commit found that it had repeated the convention claim the owner
  retracted on 2026-09-15, and that the it2 sentence it added scored a different crop. Both are corrected above.
- The fetcher, simulated with a stand-in `curl` and placeholder files in a `DEST`:
  - a run killed mid-download leaves only a `.part`; the next run fetches the file again, records six `SHA256SUMS`,
    and none holds the truncated content;
  - a second run verifies them with no downloads, rc 0;
  - after one byte of `it3/modeling_inkdetection.py` changes, it prints `CHANGED it3` and exits 1;
  - a three-line `SHA256SUMS` is reported as changed, rc 1;
  - a missing file that fails to download prints `MISS` and `CHANGED`, rc 1;
  - a leftover `SHA256SUMS.part` is ignored, and a complete `SHA256SUMS` is recorded.
- `.gitignore`: `git check-ignore` matches `it4/SHA256SUMS`, `preds_segB.npz` and `canon_20231012184424.jpg` under
  `repro/ink_ablation/`, and not `ladder_segA_null.json`.
- Ruff is clean on the changed Python files, and `bash -n` on the fetcher.
- `tests/test_ink_repro_{losses,dataset,model}.py`: 6 passed. No test reads the reports or scripts edited here.
- The standard suite: see the PR.
