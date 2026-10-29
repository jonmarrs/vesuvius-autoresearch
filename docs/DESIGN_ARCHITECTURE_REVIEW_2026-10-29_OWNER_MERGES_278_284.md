# Design and architecture review — the owner's #278 and #281–#284 (export check, seed-heading re-run, patch datasets)

Date: 2026-10-29. Baseline: `2190e36b` (main after #287, which merged these five).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 00:13–04:12 UTC firings. Two read-only reviews ran beside mine: the patch datasets
(#282, #283), and the export check, the seed-heading re-run and the October plan (#278, #281, #284). I checked
each of their findings before acting on it.
- **#278** lets the Villa export check take `--ct` only where it matches the CT its run recorded.
- **#281** prepares the seed-heading re-run at Villa 39a8cf3a, whose tracer writes an object store instead of
  `.afv`, and records the 322cb0899 run's comparison from its tiles.
- **#282** publishes patch selections with a manifest, staged and renamed, and refuses unsafe inputs.
- **#283** makes the patch selection and spatial balance checks refuse malformed inputs.
- **#284** records the October readiness on 10-28.

## What changed

- **The seed-heading re-run no longer replaces the record the draft cites** (`scripts/villa_seed_heading_rerun.py`).
  - Without `--out`, the script wrote `reports/evidence/villa_volume_seed_heading_rerun.json`. That is the
    322cb0899 record the draft and its tests cite. The launcher's documented next step has no `--out`, so the
    39a8cf3a re-run would have replaced it.
  - The default output is now named by the villa commit in the run's `chain.log`
    (`…_rerun_<commit>_from_tiles.json`, as #281's 322cb0899 file is named). An existing record is never replaced.
  - The test drives `main()` and fails on the old script.
- **The re-run launcher ties its sources to `VILLA_SHA`** (`repro/fibers/run_villa_seed_heading_rerun.sh`).
  - Villa's sources are extracted once per work directory. A later launch with another `VILLA_SHA` and the same
    `W` traced the first commit's code while `CHAIN_START` named the second. The #278–#284 review reproduced this:
    322cb0899's `volume.py` was traced, and the record said 39a8cf3a.
  - `W` now records its sources' commit. A launch at another commit, or into a `W` whose sources have no record,
    is refused.
  - Two tests run the launcher in dry-run mode against a scratch Villa repository; both fail on the old launcher.
  - The default `W` already contains the commit, so this guards a reused, explicit `W`.
- **The Villa draft's test counts** (`docs/VILLA_DRAFT_volume_seed_heading.md`).
  - It said Villa's tests at 39a8cf3a give "the same counts as at 322cb0899". The unpatched runs ran different
    files: 5 failed and 15 passed at 39a8cf3a, with the performance tests beside the seed-heading tests, against 5
    failed and 4 passed.
  - What matches is the result: the same five seed-heading cases fail, and all 20 pass with the patch. The draft
    now says so. A test binds the failing set in both transcripts and the sentence.
- **Three patch-dataset tests checked their guard** (`tests/test_patch_dataset_artifacts.py`).
  - Each passed with its guard removed, refused for another reason:
    - a reversed bbox, by the fit its zero weight breaks;
    - an unsafe ID, by the missing directory it names;
    - an output inside a bootstrap container, by the bootstrap recheck tripping over the staging directory.
  - Each now checks its guard's message and fails without it.

## Verified, no change needed

- **#282 and #283** (the patch-dataset review).
  - The selection and spatial statistics match a hand computation on small cases. Thresholds and exit codes match
    `docs/PATCH_DATASET_SELECTION.md`.
  - Empty, malformed, dangling, overlapping and drifting inputs are refused with no output and no staging left.
  - On 3,000 synthetic patches, the old and new builders select the same BOOTSTRAP, RANDOM and STRIPMATCH patches.
    The spatial results agree within 6e-12.
  - The `profile()` target no longer depends on `PYTHONHASHSEED`.
- **#278** (the #278–#284 review). The override uses the exporter's own precedence (`ct or ct_zarr or ct`) and
  refuses a `--ct` that differs from a recorded CT. The new test fails on the old verifier.
- **#281** (the #278–#284 review).
  - The patch applies at 39a8cf3a, with one hunk moved by one line, and `_seed_heading` is unchanged.
  - The committed from-tiles JSON matches the script's output format.
  - Every count and score equals the .afv record and finding 100's. The JSON cannot be recomputed here: the
    tiles and ScrollGT are absent.
- **#284** (the #278–#284 review).
  - The plan's merge dates, open PRs and deadline match the readiness JSON and the records it cites. The deadline
    is 23:59 PDT on October 31, 06:59 UTC on November 1.
  - So do the 91 filing tests, the answer word counts (371 and 554) and the ScrollGT 0.9.1 identities.
- **The checks pass** (mine). Ruff 0.9.10 `check` and `format` are clean on the five merges' 18 Python files and
  this round's. Mypy is clean over the whole repository (830 files).

## Observations for the owner (not changed)

- **#281's tests do not run the analysis.** Before this round, no test called `main()`. Reverting `main()` to the
  .afv version left all 7 passing. The launcher test greps three strings.
- **A failed re-run still ends with `CHAIN_COMPLETE` and exit 0.** The launcher runs `set -uo pipefail` without
  `-e`, so four FAILED traces end like a success. The 322cb0899 wrapper evidence treats exit 0 as success; only a
  test's separate "no FAILED in the log" check catches it.
- **#278: for a legacy record, `--ct` cannot be checked.** A record with no recorded CT accepts any open-data store
  given with `--ct` and a matching `--volume`. EXACT then certifies the export and readback, not the CT's identity.
- **#284: the filing candidate cannot be checked from the repository.** The candidate zip is not committed. Its
  readiness snapshot hash matches none of the five committed readiness JSONs.
- **The patch datasets** (#282, #283):
  - **The manifest is written but not read.** Neither STRIPMATCH nor the checks read the bootstrap's manifest, so
    a bootstrap built from another reference, or a RANDOM arm passed as `--bootstrap`, is accepted.
  - **The selection check compares arms by name.** The same directory given as both arms passes, and two IDs
    linking to one patch count twice.
  - **The area gates disagree.** STRIPMATCH accepts a 1% relative area gap; the selection check fails above 0.5
    points of total area. At the real study's 76% the two can disagree, which fails safe.
  - **Smaller points:**
    - an n = 2 arm's p25 falls outside [0, 1];
    - a dangling symlink anywhere in the source now aborts the build;
    - some guards have no test: the link-mapping recheck, an empty output directory appearing mid-build, the 2×3
      bbox shape, and a source that already has a manifest.
- **Villa's `.git` grew by about 27 MB.** The #278–#284 review's `git show` calls in the partial Villa clone
  fetched five promisor packs (2026-10-29 00:15–00:18 UTC). Refs, HEAD (ccb43181) and the tree are unchanged.
- **Doc audit:** 7154682e1, in #281's draft, is a Villa commit.

## Verification

- **This round's test files** give 10 + 13 + 41 passed (the re-run, the draft and the patch datasets). Each new or
  tightened test fails on the code before its fix.
- **The standard suite** gives the same 43 failures as on main, from `s3fs`, `numba`, `jsonschema` and Villa
  files absent here.
