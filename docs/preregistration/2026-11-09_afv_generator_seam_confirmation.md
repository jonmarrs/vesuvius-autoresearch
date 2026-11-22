# Pre-registration: the fiber generator's two seam changes on ten hand-traced cubes of Scrolls 1 and 5

**Written 2026-11-09, before any field of these cubes was predicted with the generator.** The script is
`scripts/afv_generator_seam_confirmation.py` and its runner `repro/fibers/run_afv_generator_seam_confirmation.sh`, both
committed with this file. The two changes are:
* the amended seam trim, `repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch` (findings 106 and
  107);
* on top of it, the cross-block duplicate change,
  `repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch` (finding 108).

**Pushed at 18:19:23 PST (9f3bf4f6). Run 18:19:29 PST on 11-09 to 12:34:00 PST on 11-10: finding 109,
`reports/afv_generator_seam_confirmation.md`. The gate passed on all ten cubes, and P1 to P5 held (ERLpen at τ = 4
above main's on 10 of 10, median +31.2%, and +23.0% on the four cubes at blocks of 256; above the trim's alone on 10 of
10; merges at τ = 2 325 → 297; median duplicated share 0.409 → 0.043): `CONFIRMED`.**

## The question

Both changes were measured on the same eight Scroll-3 cubes of 512³, each in 8 blocks of 256.
* **The trim** (finding 106): merge-penalized ERL rose on all eight over villa main, by a median +12.8% at τ = 4.
* **The catalogue change on top of it** (finding 108): +5.7% more at τ = 4, on all eight.
* **Together:** +17.6% over main at τ = 4, with merges at τ = 2 439 → 384.

**Do they hold on other scrolls, on cubes no step of this work has used?** The villa PR would claim they do: the
defect sits in the stitching, not in any one scroll.

## Already seen, and not predicted here

* **Finding 106's dev screen:** the eight in-sample ScrollGT cubes of Scrolls 1 and 5, 256³, each in 8 blocks of 128.
  The trim's median gain over main at τ = 4 was +38.6%, on 8 of 8. The trim's length, 16 voxels, was chosen there.
* **Finding 108's dev screen:** the same eight cubes. The catalogue change's median gain over the trim at τ = 4 was
  +17.2%, on 8 of 8.
* **These ten cubes** were used once before, by finding 103, for villa's neural tracer. That step does not touch the
  generator. Their CT and NML hand tracings were checked on 2026-11-02
  (`reports/evidence/fiber_skeletons_unshipped_checks_2026-11-02.json`).
* **The smoke before this was pushed:** `smoke` on finding 106's held-out cube `s3_00994_00494_01994_512`, from finding
  106's cached fields. It predicts nothing, and it sees none of the ten cubes. Its result is
  `reports/evidence/afv_generator_seam_confirmation_smoke_2026-11-09.json`. It reproduced all four rows the gate names
  below exactly, with no identity problems, and arm one was the same under all three stitchings. It took 17 minutes.
  It ran the script as first written; the committed script is that text ruff-formatted, with the same Python syntax
  tree (git blob `ca5f319d` → `52647961`).

## Data

The ten fiber-skeletons Dataset004 cubes that ScrollGT does not ship, as `scripts/seed_heading_confirmation.py` lists
and hashes them:
* **Scroll 1:** three cubes;
* **Scroll 5:** seven cubes;
* **Sizes:** four of 512³ (blocks of 256) and six of 256³ (blocks of 128).

The CT is each cube's `imagesTr` image, the raw scan at 7.91 µm. The hand tracing is its NML, scored as ScrollGT
scores its targets.

**The model** is `Qualzz20/afv_fiber_9um` at `e189af75`, the generator's default.
* Its model card lists its fine-tuning scans: PHerc0125, 0175A, 0191, 0211, 0257, 0268, 0306B, 0358, 0800 and 1447.
  Scroll 1 (PHerc. Paris 4) and Scroll 5 (PHerc. 172) are not among them.
* It was fine-tuned from `scrollprize/fiber_hz_vt`, whose training set (fiber-skeletons Dataset002) holds seven of
  the ten cubes. The other three, `BASE_MODEL_UNSEEN`, are reported apart.

## Method, fixed now

villa's defaults, as in findings 106–108: threshold 60%, margin 32, join angle 45°, minimum length 100, black
distance 16, no mirroring, no `--extend`.

For each cube:
* **Arm one:** the cube predicted and generated as one block.
* **Arm real:** the cube in 8 blocks of half its side, each predicted from its own crop with the margin, as
  `cli.generate` predicts a multi-block zone.
* **Arm real is stitched three ways:**
  * `main`: villa main's stitching;
  * `trim`: the amended trim, with the cube as the zone;
  * `trim+dup`: the trim and the patched `catalog.py`.

**Scoring,** as findings 106 and 108 scored:
* ScrollGT `score_tracing` at τ = 2 and 4 against the hand tracing;
* the duplicated share (written length within 1.5 voxels of a different written fiber of the same family);
* the face crossings of arm one's fibers.

The runner does the 256³ cubes first, then the 512³ ones, then `verdict`. The run is on the CPU at nice 19, about 17
hours (finding 106's timings: about 900 s per block of 256 and 4,900 s per one-block 512³ cube).

## Gate; any failure means no verdict

Per cube:
1. `afv_generator_block_seams.identity()` and `afv_generator_cross_block_duplicates.catalog_problems()`, as in finding
   108.
2. The image and the NML are the registered files (sha256 in the script).
3. villa's `resolve_model` reports revision `e189af75`. The record keeps the reported value.
4. Arm one is the same with `trim` and with `trim+dup` as with `main`: one block has no inner border and one source
   job.

Checks 1–3 stop a cube before any field is predicted.

**Before the run:** the smoke must reproduce, exactly, finding 106's `one/main`, `real/main` and `real/patched` rows
and finding 108's `trim+dup` row of its cube. That shows the harness stitches as those findings did.

## Predictions (the ten cubes, arm real)

1. **P1 (moderate):** with both changes, ERLpen at τ = 4 is above main's on at least 8 of 10 cubes.
2. **P2 (moderate):** the median gain of both changes over main at τ = 4 is at least 0.10. On Scroll 3 it was 0.176.
3. **P3 (moderate):** summed merges at τ = 2 with both changes are at most 1.05 times main's.
4. **P4 (moderate):** ERLpen at τ = 4 with both changes is above the trim's alone on at least 7 of 10 cubes.
5. **P5 (high):** the median duplicated share with both changes is at most 0.5 times main's.

Reported, not deciding:
* the gains at τ = 2;
* coverage and precision;
* the trim alone against main;
* the face crossings;
* each arm as a fraction of arm one;
* Scroll 1 and Scroll 5 apart, the 256³ and 512³ cubes apart, and `BASE_MODEL_UNSEEN` apart.

## Decision rule

| Outcome | Conclusion |
| --- | --- |
| A gate check fails | `NO_VERDICT`. |
| P1 or P3 misses | `NOT_CONFIRMED`: the two changes do not hold on other scrolls; the villa PR cannot claim they do. |
| P4 misses (P1 and P3 hold) | `TRIM_ONLY`: the trim holds; the catalogue change is not confirmed, so do not bundle it. |
| P2 or P5 misses | `PARTIAL`: they help, by less than on Scroll 3; the PR states the smaller figure. |
| All hold | `CONFIRMED`: the PR can state both scrolls' figures; posting is the owner's decision. |

## What it cannot say

* **Ten cubes, one hand tracing each, at 7.91 µm,** finer than the model's 8.64–9.36 µm training pitch.
* **Blocks of 128 on six of the ten,** not villa's default 512. A 256³ cube has one inner face per axis only at 128.
* **Seven cubes are in the base model's training set.** The changes are to the stitching, so the comparison is within
  one field per cube, but the fields may be better than on unseen data.
* **The cubes' crops are the cube.** There is no scan around them, so a block at a cube face reads no context beyond
  it, as in finding 106.
