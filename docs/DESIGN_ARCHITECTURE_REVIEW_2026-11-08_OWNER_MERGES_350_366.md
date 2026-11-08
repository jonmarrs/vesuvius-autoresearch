# Design and architecture review — the owner's #350, #355 and #357–#366

Date: 2026-11-08. Baseline: `e0558761` (main after #366).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the firings from 20:12 UTC on 2026-11-05 to 14:13 UTC on 2026-11-08, which queued while the
session's worker was down. It reviews twelve merges.

- **Code**
  - **#357** checks the detector's training inputs for aliased CT files and validates its epoch and batch budgets.
  - **#359** protects the detector's evaluation inputs, scores against the mask captured during inference and reports
    prediction coverage.
  - **#365** makes regional, ensemble and production inference read CT strictly and fail on failed ridge features.
  - **#366** adds production's artifact plan, its `--dry-run` and `--artifact-stem`, and a checkpoint captured once
    for hashing and loading.
- **Research**
  - **#355** screens trims at the neural tracer's confidence stops.
  - **#358** locates its off-reference length.
  - **#361** registers and reports finding 105 (splicing the tracer's kept overlaps).
  - **#362** adds the splice tool and its polyline check.
  - **#363** drafts the villa issue for it.
- **Drafts**
  - **#360** rebases the villa seed-heading fix onto villa main and reruns its tests with the native readers stubbed.
  - **#350 and #364** start and update the November filing draft.

The owner's #371, #369 and #372 merged at 15:38, 16:26 and 17:32 UTC, after this round began.
- **#371:** confidence-weighted pseudo-label loss.
- **#369:** finding 106, the generator's block seams.
- **#372:** scan-quality statistics.

I merged main into this branch so it stays mergeable. Their own tests are in the validation below, but the next round
reviews them.

## What changed

### The code PRs: eight guards no test reached (`tests/`)

I made 30 mutants of #365, 28 of #366 and 35 of #357 and #359. Every survivor that breaks a documented promise
now has a test. Each test passes as merged and fails with its guard removed.

- **#365: an unpickled strict volume checks the source it reopens** (`test_volume_read_contracts.py`).
  - A DataLoader worker unpickles the volume and reopens its source. `__setstate__` re-reads the shape and validates
    it, and no test reached that.
  - The new test shrinks the source after pickling. It also makes the reopened volume empty.
- **#366: outputs cannot be written inside the source volume group** (`test_production_artifact_plan.py`).
  - Protecting the source root, and not just its level-0 array, is what refuses output beside `0/` in the CT group.
    Without that protection the run wrote into the group.
- **#366: an output directory that is a file fails before the checkpoint is loaded.** Without that check the command
  ran inference and only then failed in `makedirs`.
- **#366: the recorded digest comes from the captured bytes.** The checkpoint is replaced as soon as it is captured.
  A digest recomputed from the path then describes other bytes. The existing test replaced it only during
  `torch.load`, after the digest.
- **#366: the run reads the array its plan protected.** The group's level link is repointed after planning. Reading
  the URI again would then open an array the plan never checked.
- **#366: a descriptor that under-reports its size is not captured truncated** (`test_text_snapshot.py`).
  - `fstat` says 4 bytes and the file has 10. Only the captured-length check refuses it.
  - Without that check, `capture_bytes` returned 5 bytes as the whole checkpoint.
- **#359: an input alias made while scoring is refused before publication** (`test_detector_evaluation_inputs.py`).
  - `evaluate()` checks its inputs when it starts, and #359's document says the publisher checks them again.
  - #359's own test makes its alias during inference, before the first check, so dropping the second check failed
    nothing. The new test makes the alias while scoring.
- **#359: the measurement table shows each row's coverage counts.** #359's document says the Markdown displays them.
  The existing test checked only the header, so a table printing "unknown" passed.

### The research and draft PRs

- **The November draft would have failed its own filing-day check** (`docs/PRIZE_FILING_2026-11_DRAFT.md`, #364).
  - It said "our #360 (merged 2026-11-06)". `check_filing_upstream_claims.py` reads `#N … (merged DATE` as a villa merge
    claim, so step 3 would have looked up villa's #360, an old PR, and failed.
  - It now reads "our #360, merged 2026-11-06". After the merge with main, the draft's only claim is villa's #2258.
  - `test_the_upstream_check_reads_only_the_november_merges` fails on the old text.
- **#360's stubbed test runner did not fail closed** (`repro/fibers/run_villa_seed_heading_tests_stubbed.sh`).
  - `run()` ends in `|| true` and keeps only pytest's count and failure lines. With no pytest on `PY` it wrote four
    empty sections and exited 0.
  - It now still writes the record, but exits 1 unless every section shows a pytest count and the patched side's new
    tests all pass. The committed record passes the check.
  - `test_the_runner_fails_closed` runs it on a stand-in villa with four pytest outcomes.
- **Finding 105 and the villa splice draft said "no more merges"** (`reports/neural_tracer_link_splice.md`,
  `docs/VILLA_DRAFT_volume_splice.md`).
  - At tolerance 2, where P2 is judged, summed held-out merges went 1,740 → 1,761 (+1.2%) for the labelling and
    1,740 → 1,757 for the polylines. Both are within P2's 5%, but neither is "no more". The draft's own table showed
    the rise.
  - The finding's title now says "with 1.2% more merges at tolerance 2". Its bullet "No more wrong connections" is now
    "Few more", and the draft says "barely more merges".
  - The draft also said the rule "was registered before the ten cubes below were scored". Its table holds the
    polylines, which were checked afterwards. It now says which part was registered.
  - Tests in `test_neural_tracer_link_splice_report.py` and `test_villa_draft_volume_splice.py` fail on the old text.
- **The splice tool read unfinished tiles and could overwrite its output** (`scripts/neural_tracer_splice.py`, #362).
  - **Unfinished tiles.** villa's `save_tile` writes `TILE.partial.npz` and then renames it, and villa's readers skip
    the partial name. The tool globbed `*.npz`, so it read a partial tile's pieces, or failed on a truncated one.
  - **Overwriting.** `np.savez` appends `.npz` after the tool's `exists()` check, so `--write out/spliced` replaced an
    existing `out/spliced.npz`.
  - It now skips partial tiles and requires a `.npz` path. Both new tests fail on the merged tool.
  - The tool is not registered: the registration names `neural_tracer_link_splice.py`, which is unchanged.
- **The November draft's tests could fetch from villa's remote** (`tests/test_november_prize_draft.py`).
  - `_villa` runs `git -C villa show`, and villa is a `blob:none` partial clone. A missing blob is fetched rather than
    skipped.
  - Every other test that reads villa objects sets `GIT_NO_LAZY_FETCH=1`; this one now does too, with a test.
  - The out-of-suite run below ran these tests before the change. Whether that fetched anything is not recorded.
- **Records and guards bound.**
  - **#355 and #358.** Each script's `main()` now rewrites its committed record byte for byte from the recorded
    per-cube results. That binds the summaries, the gates and the settings. Of 35 mutants of the two scripts, 22
    survived the merged tests; all are now killed.
  - **#361 and #362.** Of 55 mutants of the three splice scripts, the tests now kill all but three. Those three:
    - a tie for Q's nearer end, which the registration does not specify;
    - the self-link guard, which a negative dot product already covers;
    - an unreachable `seen` check.
  - **#350 and #364.** 19 changes to the draft's figures, finding numbers and commits passed the merged tests. Each
    now fails a test. They include finding 103's 0.167 and 1.040×, the October deadline and the rollover record's title
    and HTTP status.
  - **#360.** The patch's hunk headers, the stub's two modules, the runner's default villa commit and steps, and the
    November draft's rebase commit are bound.

## Verified, no change needed

- **#365's guards.** 28 of 30 mutants fail its tests. Of the two survivors:
  - the re-validation on unpickling now has a test (above);
  - `VesuviusS3Dataset`'s boolean check repeats the volume's own, which runs first. It is redundant, not missing.
- **#366's guards.**
  - 22 of 28 mutants fail its tests, and five of the six survivors now have tests.
  - The sixth drops the dry run's stdout redirect. It is equivalent: the reader is given the selected array's path
    and never prints the OME-level notice.
  - The dry run's arithmetic tile count equals `len(tile_starts)` for every length, size and stride up to 128.
- **#357's and #359's guards.** 31 of 35 mutants fail their modules' tests. Of the four survivors:
  - two now have tests (above);
  - dropping the checkpoint's `detector_training` record fails the two training modules, which hold the readback;
  - dropping `math.isfinite` from the batch-fraction check is equivalent, because `0 < x <= 1` already refuses NaN and
    infinity.
- **#357's preflight.** With the regular-file check removed, the FIFO test hangs in `open`, which is what the check
  prevents.
- **The owner's review documents' counts:**
  - #365's 56 cases;
  - #357's 32;
  - #359's 30;
  - #366's 56 across production planning, production inference and capture (32 + 11 + 13).
  Each matches what pytest collects.
- **#355's and #358's reports match their records**, including both tables, the shares (summing to 100.0%), "16%"
  and finding 101's "two-thirds". Neither script is registered.
- **#361 follows its registration.**
  - The registration was committed at a70e71ae, before the result at bd2f260d.
  - The script applies the registered rule, ties and gates.
  - The registered rule applied to the record gives `SUPPORTED_AT_TOL4_ONLY`.
  - Every figure in the report, the polyline section and the villa draft recomputes.
- **The November draft's figures recompute from their sources:** finding 100's arms, finding 103, the polylines and
  #2258's 0.339%.

## Observations for the owner (not changed)

- **Wording in #358's report.**
  - "At tolerance 2, precision mostly measures placement": the share beside the followed fiber is 39.2%, the largest
    but not a majority.
  - Three bounds are exceeded by their exact values: "within 0.10 voxel" (0.1047), "at most a third" (33.52%) and
    "at most 0.101" (0.10144).
- **#355's and #358's scripts.**
  - They check `--out` only at start and write it non-atomically, like their siblings.
  - `locate` counts zero-length runs in its `_n` counts. The recorded counts may include a few.
- **The splice scripts.**
  - The registration's "over its last 4 points" reads as three steps; the script, committed with it, uses four.
  - `relabel` would raise if the highest-numbered spliced piece had no voxel in the cube. It did not on the 21 cubes.
  - The polyline check would divide by zero on a zero baseline.
  - The 39% share the report cites comes from the in-sample cubes.
  - `docs/RESEARCH_STRATEGY.md` still calls the polyline tool untested.
- **The November draft.**
  - "Merges 1,740 → 1,757" does not say tolerance 2.
  - Its "still needed before posting" list omits the villa draft's slot and AI-marker steps.
- **The stubbed seed-heading runner** never removes its temporary directory: two copies of villa's `vesuvius/`, about
  21 MB each.
- **The villa seed-heading draft's "volume.py hunks … unchanged"** holds for the changed lines. One context line and
  the hunk offsets differ.
- **#357's alias check** compares inodes, so copied layers still pass, as its document says.

## Verification

VALIDATION_PLACEHOLDER

A note on this round's own work.
- **A brief mutation in the main checkout.** I first checked the unpickling test's mutant in the main checkout, for
  about three seconds, while the standard suite was running there. I restored the file at once. That suite gave round
  #152's failing ids. Every later mutation ran in a separate worktree.
- **The detector mutants had to be rerun.** A worker restart stopped their first run and left one mutant applied in
  that worktree, which I restored before rerunning.
- **The regular-file mutant hung its test.** With #357's regular-file check removed,
  `test_special_layer_files_are_refused_without_opening_them` opened its FIFO and blocked in `wait_for_partner`. I
  stopped it and counted it as killed.
