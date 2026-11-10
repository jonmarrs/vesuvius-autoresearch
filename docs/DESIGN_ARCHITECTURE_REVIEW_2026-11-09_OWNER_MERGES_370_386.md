# Design and architecture review — the owner's #370, #385 and #386

Date: 2026-11-09. Baseline: `79de9088` (main after #386).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 23:12 UTC firing on 2026-11-09. The 21:12 and 22:13 firings found main unchanged. The owner
merged three PRs at about 22:59 UTC:
- **#370** refuses to rank an active-learning catalog that the loader did not score in full.
- **#385** points the pre-commit mypy hook at the locked packages in `.venv`.
- **#386** is finding 107: the seam trim at villa's default block size of 512, on one 1024³ zone of the Scroll-3 scan.
  The decision is `BITES_AT_DEFAULTS`.

## What changed

### #386: 28 of finding 107's guards tested without the owner's files (`tests/test_afv_generator_default_zone.py`)

This round made 50 mutants of `afv_generator_default_zone.py`. On a machine without the owner's files, #386's tests
killed 20. Four of its tests skip here: they need the #1934 head's `cli.py`, ScrollGT or the owner's villa worktree.
The new tests replace torch, zarr, ScrollGT and the generator with stand-ins, so they run anywhere. Each passes as
merged and fails with its guard removed. Together they kill 28 of the 30 survivors:

- **The run as registered** (one test on a zone shrunk to 2 × 2 × 2 blocks). It kills nine mutants:
  - the zone's origin, read box and crops;
  - the trim on `patched` only, with the zone's reach rather than the block's crop;
  - the cube's offset in the zone, its inside count and its duplicated share;
  - the zone's share counted over every sample, not only the cube's.
- **Each of the five gate checks stops the run before any field is predicted**: the module identity, the patched
  `stitch.py` digest, the cube's core, the crops and the model revision. Six mutants, including a gate that records a
  problem but never stops.
- **Amendment 1's fetch.**
  - The scan is read 16 slices at a time, and the last slab is clipped (five mutants).
  - The file is renamed into place only after its core matches the cube's own CT (three mutants).
  - Amendment 1's own slab test needs ScrollGT, so it skips here.
- **The verdict step writes the record once.** A second run refuses and leaves the first record as it was.
- **The decision rule.**
  - A duplicated share of exactly 0.05 meets P1 ("at least 0.05").
  - The rows apply in the table's order: a P3 miss outranks a P2 miss, a P1 miss outranks both, and a gate failure
    outranks everything.
- **The cube's share counts a neighbour outside the cube.** A sample inside is duplicated when its same-family
  neighbour lies just past the cube's face.

The two remaining mutants are equivalent on this zone:
- Leaving the crop's upper edge unclipped changes nothing, since 544 + 512 + 32 = 1088, the array's side.
- An empty box's share (1.0 instead of 0.0) is never computed: the cube always holds samples, and nothing documents
  the empty case.

By construction, three of the 28 (the zone's origin, read box and crops) should also fail the owner's test that needs
the #1934 head's `cli.py`. Four of the slab mutants should fail amendment 1's test, which needs ScrollGT. Neither test
can run here, so neither was checked.

### #386: the zone and its blocks are bound to the record (two document tests)

This round made 91 single-figure mutants of the report, the registration, the villa draft, the research strategy
and the prize draft. #386's tests killed 66. Two new tests bind seven more figures to the record's `zone`, `block`,
`margin`, `pad` and `cut_end`:
- the report's zone, block count, read size, face coordinate and trim length;
- the strategy's "8 blocks of 512";
- three places where the villa draft states the zone or the block.

The other 18 survivors are not record figures:
- dates and wall-clock times;
- commit hashes and the scan id;
- "18%", the registration's arithmetic and its "Already known" figures;
- "Blocks 1 and 6", "no one-block arm", "17 hours" and "23 of 25".

Where they can be checked offline, they are right.

## Verified, no change needed

- **Finding 107's decision recomputes.** `verdict(record["result"])` equals the stored verdict, and the record file
  is byte for byte what the verdict step writes. Every margin is far from its threshold:
  - P1: 0.1203 against at least 0.05;
  - P2: 0.4347 of main's share against at most 0.6;
  - P3: ERLpen +15.98%, against any rise;
  - P4: merges 92 → 82, against a limit of 96.6.
- **Every figure #386 states recomputes from the record.** This covers the report's headline, its table and its
  comparisons with finding 106, the villa draft, the research strategy, the prize draft and the registration's result
  header.
- **The order of events.**
  - The registration (904419d5) came first, then the launcher's quoting fix (a1060b39), then amendment 1 (1f0f632a).
    The results (b81cb6a4) came after the run ended.
  - `bash -n` refuses the launcher at 904419d5 and accepts it at a1060b39, as the report's first launch says.
  - The four scripts the run used are unchanged from amendment 1 to the merge.
  - This checkout's fetch log has 1f0f632a on origin by 18:12:54 PST, before the run's recorded start at 18:21:17.
- **Every field came from the recorded run.** The record times all eight blocks, and a block is timed only when it is
  predicted, so none was reused from the run that was killed. Prediction took 61,036.2 s, inside the 62,832 s between
  the run's start and end.
- **Amendment 1 changes only the fetch.** `run()`, `verdict()`, the gate, the predictions and the decision rule are
  as registered.
- **The script matches the registration.**
  - The zone is 8 blocks of 512, each read as 576³ (origin 32, `PAD` 288, `SIDE` 1088).
  - The trim runs on `patched` only, with the zone's reach.
  - The cube is scored at tolerances 2 and 4.
  - The gate runs before any prediction.
  - The held-out cube `s3_04494_00994_01494_512` is the lower of the two middle gains (0.111; the other is 0.146).
- **#370 refuses an incomplete scoring.**
  - A loader that drops the last batch, a batch sampler that does, or an iterator that stops early is refused before
    ranking, and no review queue is published.
  - The only caller is the script's `main()`, whose `DataLoader(batch_size=8, shuffle=False)` delivers every patch.
  - Both mutants fail #370's tests: the check removed, and `!=` weakened to `>`.
- **#385's hook.** The mypy entry now passes `--python-executable ./.venv/bin/python`, and #385's test reads the
  entry from `.pre-commit-config.yaml`. This round's whole-repository mypy ran with that flag (below).

## Observations for the owner (not changed)

- **The model-revision gate passes when the revision is missing.** `provenance.get("revision", bs.REVISION)` treats an
  absent key as the expected revision. The record's `settings.revision` is the constant, not the value villa reported.
  So the record cannot show the model revision, and the report test's `startswith("e189af75")` always holds. The
  script is registered and the check is inherited from finding 106's `afv_generator_block_seams.py`, so I did not
  change it. Whether villa's `resolve_model` can omit the key cannot be checked here.
- **The record names no commit.** It has no commit hash and no wall-clock time; the launcher prints `ZONE_START` and
  the commit only to its log.
- **The registration gained a result header after the run** (b81cb6a4), as finding 106's did. Its figures are right
  and tested.
- **"Nothing was written."** The report says this of the run that systemd-oomd killed. That run did write the
  1,088-slice cache, which the recorded run reused; amendment 1 says so.
- **The prize draft's villa limits.** "three open PRs, two code fixes a week" rule the PR out before about 11-13. If
  #2464 is closed, as the villa draft says, only the code-fix limit binds. The sentence is still true as a whole.
- **Not checkable offline:**
  - the push times;
  - the villa main commit the draft was checked at, and "the patch applies" there;
  - "Blocks 1 and 6 ran beside a full test suite";
  - the smoke script's voxel-for-voxel and 23-of-25 claims.

  The smoke script has no test; it reads files under `/home/jon`.

## Verification

- **The touched modules pass.**
  - Finding 107's three test modules give 45 passed and 4 skipped, against 28 passed and 4 skipped as merged. That
    is 17 new cases from eight new test functions and four new decision-rule rows.
  - With `test_afv_generator_block_seams.py` and the suite guard, they give 60 passed and 4 skipped.
  - #370's and #385's modules give 46 passed.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` and `format` are clean on the three changed test files.
  - Mypy is clean over the whole repository: 937 files. It ran as #385's hook now runs it, with
    `--python-executable ./.venv/bin/python`.
- **The standard suite.**
  - On `79de9088`, the 192 modules give round #153's 70 failing ids.
  - On this branch, with #388's three added modules, the 195 give the same 70.
- **The test modules outside the suite.**
  - The 250 modules give 2,387 passed, 86 skipped, 13 failed and 21 errors. The failing ids are round #153's 34.
  - Against round #158's 2,366 passed and 82 skipped: #388 moved two modules (18 tests) into the suite, and #386
    added two modules. #386's tests and this round's account for the other 39 passes and the 4 skips.
- **The doc audit**, run alone, lists round #158's unresolved references and three more, all from #386:
  - the report's villa main commit and model revision;
  - the villa draft's newer villa main commit.

  These are villa and model-hub hashes, which this checkout cannot resolve. Finding 106's report already lists the
  same two, and the draft already listed the older villa main commit. The audit checks 2,238 path and 832 commit
  references, against 2,226 and 825 then.

## A note on this round's work

- **The owner merged two more PRs during this round.** Both are merged into this branch, and their review is left to
  the next round:
  - #388, at 23:23 UTC ("Require complete paired evidence for confidence analysis"). The verification above includes
    it.
  - #389, at 23:54 UTC ("Check ink pyramids for silent depth truncation"). It arrived after the verification above.
    Its module, `test_ink_pyramid_depth.py`, passes on this branch together with this round's three modules and the
    suite guard: 80 passed and 4 skipped. Ruff and mypy are clean on its two Python files.
- **A helper agent made finding 107's mutants and wrote its tests.** I reran 11 of the kills myself (eight script
  mutants and three document mutants). Each new test passed as merged and failed with its mutant.
- **Finding 107's review and mutation runs were done in a sparse worktree.** There the two tests that scan the whole
  checkout fail, because `v3_training/` is not checked out. In the main checkout they pass.
