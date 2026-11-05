# Pre-registration: does the queued villa seed-heading fix hold on ten hand-traced cubes never traced here?

**Status: REGISTERED 2026-11-03.** Proposed on 2026-11-02 (PR #328) and reviewed in PR #329. The owner approved the
run on 2026-11-03, before any cube was traced. By then only the padded CT had been fetched: one cube's on 11-02, and
the rest's from 10:23 PST on 11-03. The predictions, their thresholds and the decision rule are as proposed. The
chain needs the autoresearch loop stopped for about an hour. The script, the chain and their tests are committed with
it.

**Amended in the open at registration,** after #329's review and before any trace:
* **Data identity.** `fetch`, `presence` and `score` refuse an NML or image whose SHA-256 differs from the 11-02
  records' (`DATA_SHA256`; the NMLs' from PR #326's evidence, the images' from the checks below).
* **A cube with no baseline.** A cube whose `before` run has coverage or merge-penalized ERL 0 has no factor. It is
  listed under `zero_baseline` and left out of P1, P3, P4 and P5; P2 still applies to it. As proposed, `score` stopped
  with an error instead.
* **One result.** `score` refuses to replace an existing result, and it records the ScrollGT commit it scored with.
* **Disclosures,** under "What it cannot say": a neighbouring cube, the manipulation check's breadth, and what the
  chain freezes.

## The question

villa's neural fiber tracer skips a seed dot whose CT axis lies more than 35° from the dot's presence direction.
Finding 100 (`reports/neural_tracer_steep_heading.md`) traced those dots instead. In its `keep` arm they are traced
along villa's own CT axis, as villa's training seeds are. The queued villa fix is that arm as a change to villa's source:
`repro/fibers/villa_volume_seed_heading.patch` deletes the skip. The 10-28 re-run at villa `39a8cf3a` reproduced the
arm point for point (`reports/evidence/villa_volume_seed_heading_rerun_39a8cf3a.json`).

The draft's case rests on two cubes. Keep raised coverage 1.11× and 1.28× on the two held-out Scroll-5 cubes. Finding
100 says: "The gain rests on two cubes of one scroll." **This asks whether the fix behaves the same on ten cubes that
no tracer here has seen.**

## What finding 100 predicts

Across its 21 cubes, keep's coverage factor (after over before, tolerance 2) follows the share of dots the stock run
skipped. That share, `s`, is the stock run's `no_heading` over its `dots`; finding 100 records it as
`no_heading_share`. The two are rank-correlated at Spearman ρ = 0.82 (computed from `reports/neural_tracer_steep_heading.json`):

| cubes | s | keep's coverage factor | keep's precision change |
|---|---|---|---|
| the 11 in-sample cubes | 0.002–0.012 | 0.9965–1.0026 | −0.0021 to +0.0017 |
| the 8 held-out Scroll-3 cubes | 0.011–0.088 | 1.0029–1.0124 | −0.0133 to −0.0019 |
| the 2 held-out Scroll-5 cubes | 0.266, 0.353 | 1.107, 1.281 | −0.017, +0.011 |

Keep's merge-penalized ERL factor lies in 0.978–1.198 on all 21 cubes. No cube skipped between 0.088 and 0.266.

## The cubes

villa's fiber-skeletons Dataset004 holds 31 hand-traced cubes. ScrollGT ships 21 of them. The other ten have never
been traced, scored or used here. None, padded by 128 voxels, intersects any of ScrollGT's cubes
(`reports/evidence/fiber_skeletons_unshipped_2026-11-02.json`, PR #326); one padded context does meet another's
(below):
* **Seven were first released in Dataset002**, whose 13 + 5 cubes match the presence model's (fiber_hz_vt's) training
  set. Its presence is in-sample on them: `s1_02494_01494_03994_512`, `s5_05497_01997_02997_256`,
  `s5_05497_02497_02497_256`, `s5_08994_02994_03994_512`, `s5_08997_02497_04997_256`, `s5_11497_05497_03997_256` and
  `s5_16997_03497_03997_256`.
* **Three were first released in Dataset003**, so they are held out from it: `s1_08994_02494_03494_512`,
  `s1_09997_02497_03497_256` and `s5_15494_04494_02494_512`.
* **The tracer's checkpoint lists no fiber-skeletons release among its training data.** fiber_single_small's dataset
  config lists Paris 4 (Scroll 1) fibers from a manifest, plus model-made AFVs. Three of the ten are Scroll-1 cubes;
  whether those Paris 4 fibers pass through them is not public (PR #326).

**Checked on the CPU on 2026-11-02** (`reports/evidence/fiber_skeletons_unshipped_checks_2026-11-02.json`):
* **Labels.** On every cube, the NML's in-bounds nodes land on villa's semantic label at 0.99998–1.0. ScrollGT's gate
  is 0.999.
* **CT.** Two 4×64×64 corners of each Dataset004 image equal the public raw scan voxel for voxel. On one cube the
  whole 256³ core of the padded CT does.
* **Padding.** The 128-voxel padding lies inside the scan on all ten.
* **Ground truth from the NML.** For these cubes it is built straight from the NML. On two shipped cubes this scores
  finding 97's runs exactly as ScrollGT's shipped targets do, at both tolerances.
* **Not checked:** the NML against the CT itself. ScrollGT's second gate needs fiber_hz_vt's probability.

## The protocol

Finding 97's protocol throughout, through `scripts/seed_heading_confirmation.py` and
`repro/fibers/run_seed_heading_confirmation_chain.sh`:
* **CT:** each cube padded by 128 voxels of the public raw scan, converted as villa's dataset generator made the cubes.
  The core must equal the Dataset004 image exactly, or the chain refuses to start (`fetch`, run beforehand with the
  loop running).
* **Presence:** fiber_hz_vt on each cube's own image, on the GPU, from the model directory finding 91 recorded and
  with its patch, step and AMP. The cached inference identity, which hashes the model files, keys the cache to that
  directory as it is now; `presence.json` records the hashes, and nothing here compares them with finding 91's.
  finding 91's 2×2×2 block mean is placed in the padded trace grid, with zeros outside the cube.
* **Tracer:** villa's own CLI at `39a8cf3a`. `before` runs the source as villa has it; `after` runs it with the patch.
  Both run in finding 97's tracer environment, with checkpoint `fiber_single_small@451182558c` and finding 97's flags.
  The box is the cube, and `--no-fibers` is set because villa #2316 binds exports to an open-data volume. The chain
  checks that `before` holds the skip and `after` does not, and that each side imports its own `volume.py`.
* **Smoke:** `before` on `s5_13497_01497_02497_256`, with finding 97's inputs, must reproduce finding 97's run point
  for point, or nothing is traced.
* **Scoring:** each run's fibers come from its finished tiles. They are scored in the cube's frame with ScrollGT
  scoring version 3 at tolerances 2 and 4, against the NML's fibers with more than one node inside the cube.

## Registered predictions

`s` is each cube's skip share in its `before` run. Factors are after over before, at tolerance 2.

| | prediction | from finding 100 |
|---|---|---|
| **P1** (high) | on every cube with s < 0.02, coverage factor in 0.99–1.01 | 0.9965–1.0053 on the 12 such cubes |
| **P2** (moderate) | precision at most 0.03 lower on every cube | at most 0.017 lower on all 21 |
| **P3** (moderate) | on every cube with s ≥ 0.20, coverage factor at least 1.05 | 1.107 and 1.281 on the 2 such cubes |
| **P4** (low) | Spearman ρ between s and the coverage factor at least 0.5, over the ten | 0.82 over 21 |
| **P5** (moderate) | merge-penalized ERL factor at least 0.95 on every cube | 0.978–1.198 on all 21 |

P1 is not tested if no cube has s < 0.02, and P3 is not tested if no cube has s ≥ 0.20; each is then recorded as
`null`. Most of the ten are presence-in-sample, and all eleven of finding 100's in-sample cubes skipped under 0.02, so **P3 may
well go untested**. That outcome is registered as an outcome, below. It is not a reason to add cubes or move the
threshold.

**Manipulation check:** `after` skips no dot on any cube (`no_heading` 0). That held on finding 100's 21 keep runs
and on the re-run's two. A failure makes the status `MANIPULATION_FAILED` and the decision void.

## Decision rule (status `OK` only)

For the villa draft (`docs/VILLA_DRAFT_volume_seed_heading.md`):
* **`HOLD`, if P2 or P5 fails.** The fix costs precision or merge-penalized ERL on a cube it was never measured on,
  and the draft is held.
* **Otherwise, by P3:**
  * **`REPLICATED`:** the draft may say the coverage gain replicated on the named unseen cubes.
  * **`NOT_REPLICATED`:** the draft says the gain did not replicate, and that it rests on finding 100's two cubes.
  * **`NO_HIGH_SKIP_CUBE`:** the draft says no unseen cube skipped 20% of its dots, so the gain rests on finding 100's
    two cubes. It may say the fix cost at most 0.03 precision and 5% of merge-penalized ERL on each of ten unseen
    cubes.
* **P1 and P4 are reported, not decisive.** If P1 fails, the draft may not say that coverage stays put where few dots
  are skipped.

## What it cannot say

* **One checkpoint at its defaults, one presence model, and finding 97's protocol.** It says nothing about villa's
  volume tracer at villa main. Since `39a8cf3a`, villa #2359 rewrote it. The patch still applies there, 201 lines up,
  and the skip is still there. But villa main's tracer needs a rebuild of villa's native `vc_object_store` before it
  imports here. Re-checking the draft at the commit it would be posted against is a separate step, the draft's
  "Before posting" step 3.
* **Presence quality and skip share are confounded.** Seven cubes have in-sample presence, and in-sample presence is
  where finding 100 saw no skips. A gain conditioned on `s` is still not a test that tilt causes it (finding 100,
  "What it does not say").
* **Ten cubes, three of them held out from the presence model.**
* **One cube neighbours one of finding 100's.** `s5_16997_03497_03997_256` lies 244 voxels from the held-out
  `s5_16997_03997_04497_256` in y and in x, at the same z. Padded by 128 voxels each, their CT contexts share a
  12 × 12-voxel column (in y and x) through their whole depth; their cubes and labels do not overlap.
* **The manipulation check is stricter than the patch.** At the pin, villa counts a dot `no_heading` both when its
  heading raises `SeedHeadingError` and when it fails the 35° test. The patch removes only the second. So an `after`
  run with any `no_heading` voids the study without showing that the patch failed. It was 0 on all 21 of finding
  100's keep runs.
* **The chain freezes `scripts/`, not `src/`.** `presence` imports `vesuvius_autoresearch` from the checkout's `src/`.
  The run is made from the registration commit's own worktree, which nothing edits while it runs.

## The run

1. **CPU, loop running:** `scripts/seed_heading_confirmation.py fetch --work $W` downloads the padded CT.
   * Scroll 5 comes from the public zarr. Scroll 1 comes from raw TIFF slices by byte range: the three Scroll-1
     cubes are 2,048 padded slices in all. Neither rate is on record here; on 11-03 the first Scroll-1 cube ran at
     about 0.35 slices a second.
   * The fetch is resumable and writes `$W/prepared.json`.
2. **GPU, loop stopped:** `repro/fibers/run_seed_heading_confirmation_chain.sh`, which refuses to start while the loop
   runs. A wrapper stops the loop before it and starts it again afterwards, whatever the chain did, as the 10-28
   re-run's wrapper did (`repro/fibers/run_villa_seed_heading_rerun_paused.sh`).
   * Presence for the ten cubes. fiber_hz_vt's time per cube is not on record here; at 128³ patches with step 0.5,
     it runs 27 patches on a 256³ cube and 343 on a 512³ cube.
   * The smoke.
   * Twenty traces. Finding 100's chain log gives 0.96 min per padded 256³ run and 3.86 min per 512³ run, so about
     43 minutes in all.
3. **CPU, loop running:** `$W/code/seed_heading_confirmation.py score --work $W` writes
   `reports/seed_heading_confirmation.json`.
