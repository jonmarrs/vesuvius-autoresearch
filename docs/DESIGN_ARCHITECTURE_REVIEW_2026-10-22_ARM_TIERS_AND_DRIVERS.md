# Design and architecture review — the arm tier table against the drivers that record what ran

Date: 2026-10-22. Baseline: `674bc399` (main after #187).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how the spiral studies decide which code tier an arm belongs to, and the record that decision rests on.
- **The table.** `scripts/arm_tiers.py` is the single table of arm → tier (pinned `6847063f`, current, upstream).
  It raises on an unclassified arm.
- **The record.** `repro/spiral_fits/` holds 74 vendored scripts, 52 of them fit drivers and 22 launchers or
  analysis scripts. No review had named this directory.
- **The other encodings.** `measure_noise_floor.py` cross-checks its groups against the table at import. Four other
  scripts declare tiered arm groups of their own:
  - `soft_count_study.py`;
  - `survey_manipulation_effects.py`;
  - `seed_as_shared_nuisance.py`;
  - `analyse_spiralcheck_pinned_replication.py`.

Mixing tiers is invalid: the current tier reads 67.6% more ink through a byte-identical scorer. `arm_tiers.py` exists
because a misfiled arm once moved a published correlation (r −0.121 → −0.008) with nothing failing.

Main has not moved since #187. There are no open pull requests. This round covers the 13:13 UTC firing.

## What changed

- **The tier table was checked against itself, never against the evidence.**
  - `arm_tiers.py` asks that an arm be classified "by a human who knows which tree it ran on". The drivers in
    `repro/spiral_fits/` are that record. Each exports `FIT_SPIRAL_RUN_TAG` and changes into the villa tree it
    fits with.
  - `tests/test_arm_tiers.py` checked the table against fixed expectations and against `measure_noise_floor.py`'s
    groups, but not against the drivers.
  - **Measured:**
    - 52 drivers set a run tag;
    - every classified one (41) fits on the tree its tier names, by its `PYTHONPATH`, its `cd` and its
      interpreter alike;
    - every rule in the table is backed by at least one driver;
    - the unclassified eleven are smoke and exploratory arms, which raise by design.
  - **Change:** two tests now hold the table to the drivers.
    - One checks tree against tier for every classified tag. It requires every line that decides what runs to name
      one tree, refuses a tag set by two drivers, and holds the eleven unclassified tags exact. So a parsing slip
      cannot pass as "unclassified".
    - The other checks that every rule has a driver.
    - A driver whose tag is built from `$SEED` (`fit_upfit.sh`) covers each of its seeds.
- **Three arms the analyses use have no vendored driver.**
  - `nosamecur_s4`, `s5` and `s6` are the same-winding extension's arms. They carry
    `reports/samewinding_extension_verdict.md`, and `soft_count_study.py` groups them.
  - Their drivers were never copied into `repro/spiral_fits/`, though every other grouped arm's was, including
    `curbase_s4`–`s9` on the day they launched. The README's own opening describes this as the reproducibility
    hole the directory exists to close.
  - The preregistration specifies them exactly: `fit_nosamecur_s1.sh` with only the seed (4, 5, 6) and the tag
    changed. The vendored s1–s3 drivers differ from each other in only those two lines.
  - **Change:**
    - The README lists the three as not vendored, with that specification.
    - A test holds the set of grouped arms without a driver to exactly these three, and requires the README to name
      them. Vendoring them means emptying `_NOT_VENDORED`.
    - Nothing is reconstructed, since the directory holds copies of what ran.
- **Four scripts' tier groups were unchecked encodings of the same fact.** These all agree with the table today:
  - `soft_count_study.py`'s `PINNED` and `CURRENT`;
  - `survey_manipulation_effects.py`'s `STUDIES` (each study's arms and tier);
  - `seed_as_shared_nuisance.py`'s `LAYOUTS`;
  - `analyse_spiralcheck_pinned_replication.py`'s 24-arm pinned sample.

  **Change:** one test reads each group and checks every arm's tier. Two of the scripts import packages that live
  only on the owner's machine, so their tables are read from the source, evaluated with only `tuple`, `list` and
  `range`. The same groups feed the vendored-driver check.
- **`correlate_geometry_ink.py` knew two tiers.** It built `{"pinned": [], "current": []}` and indexed it by
  `tier_of`, so an upstream fit would raise `KeyError`. **Change:** it takes the table's `TIERS`, and a test runs it
  on one fit of each tier.
- **`audit_arm_coverage.py`'s tag pattern** left out `nosamecur_s4`–`s6` and `upfit_`, so its phantom check (tags a
  script names with no scored directory) could not see them. **Change:** the pattern covers every classified
  family, and a test checks it.
- **Two dated reports give `be09a8503` as `curbase_s4`–`s9`'s fit tree.** These are
  `upstream_fitter_no_detected_change.md` (09-25) and `fit_rng_dominates_the_flatten_was_never_binding.md` (09-22).
  The 09-27 correction found they were fitted on the unrefreshed `d8c5f488a` copy, and rendered on `be09a8503`. No
  `spiral-fitting/` file differs between the two, so neither result changes. **Change:** each has a dated note at its
  head. Reports that say "render-clean arms, all on `be09a8503`" mean the render tree, and are right.
- **The README was out of date.**
  - It said "60 files"; 74 are here, 14 of them copied as studies launched.
  - It listed only the anchor pilot, not `anchor10cov_s2` and `s3`.
  - It described two tiers, though `fit_upfit.sh` has been the upstream tier since 2026-09-24.
  - **Change:** it names the three tiers and points to `arm_tiers.py` as the table and the test that checks it. It
    lists the deliberately unclassified drivers, and gives the counts.
- **A stale comment.** `measure_noise_floor.py` called the `anchor10cov` group "registered but not yet run". It
  ran (`reports/anchor_ablation_verdict.md`) and is a row of `reports/noise_floor_by_tier.md` (0.0419). The comment
  is corrected; the code is unchanged.
- **Tests** (outside the standard suite, as before):
  - `tests/test_arm_tiers.py`, +5;
  - `tests/test_correlate_geometry_ink.py`, +1;
  - `tests/test_audit_arm_coverage.py`, +1.
- **Mutants.** Each of these fails a new test:
  - in the table:
    - `upfit_` filed as current;
    - a rule with no driver;
  - in the drivers:
    - `fit_boot090s1.sh` changing into the current tree;
    - `fit_upfit.sh`'s tree pointed at pinned;
    - `fit_upfit.sh` deleted;
  - in the gap list and README:
    - `nosamecur_s4` dropped from the gap list;
    - the README not naming the gap;
  - in `soft_count_study.py`:
    - a pinned arm grouped as current;
    - a seventh `nosamecur` arm with no driver.
  - second commit:
    - `fit_curbase_s9.sh`'s `PYTHONPATH` and interpreter on the pinned tree, its `cd` left alone;
    - a second `boot090s1` driver on the current tree;
    - `gap133smoke.sh`'s tag quoted;
    - a current arm in `seed_as_shared_nuisance.py`'s pinned layout;
    - the stripmatch study marked current in `survey_manipulation_effects.py`;
    - a current arm in the pinned spiralcheck sample;
    - `correlate_geometry_ink.py`'s two-key dict restored;
    - `audit_arm_coverage.py`'s narrow pattern restored.

    The reviewer's three surviving mutants are the first three.

## Verified, no change needed

- **`curbase_s*` and `nosamecur_s*` name both trees.** The pinned name appears in a header comment about the
  pinned corpus; `PYTHONPATH`, `cd` and the interpreter are all `villa-spiral-current`.
- **`fit_curbase_s4.sh` matches its own claim.** It is identical to s1 apart from its seed and the
  forward-prediction comment; both fit dataset `spiral_s1`.
- **`anchor10cov_s1`** appears only in comments explaining why the pilot keeps its own tag.
- **The 22 scripts that set no run tag** are launchers or analysis scripts. Where a `run_*.sh` launcher names a villa
  tree (`VILLA`), it is the render tree; their fits run from the vendored `fit_<tag>.sh` drivers.

## Observations for the owner (not changed)

- **Copy the three drivers.** They are in `spiral_out` (`nosamecur_s4`–`s6`). Then empty `_NOT_VENDORED`.
- **Live copies aren't compared.** The vendored drivers are copies, and nothing here compares them with the live
  ones on the owner's machine. A driver changed in `spiral_out` after vendoring would not show.
- **Within-tier trees.** `measure_noise_floor.py` and `soft_count_study.py` split `curbase` by tree within the
  current tier (`d8c5f488a` / `be09a8503`). That split lives in their groups, not in the tier table. The noise-floor
  comment records that it was measured immaterial.
- **A directory name is not a commit.** The driver check maps `villa-spiral` to `6847063f` by name. Only
  `fit_upfit.sh` checks its tree's SHA. `reports/fit_tree_provenance.md` draws the same lesson.
- **`test_the_pooled_correlation_is_not_reported`** runs `correlate_geometry_ink.py` against the owner's `spiral_out`.
  It fails wherever that is absent, on main as here. It is outside the standard suite.

## Verification

- `pytest tests/test_arm_tiers.py tests/test_soft_count_study.py tests/test_correlate_geometry_ink.py
  tests/test_audit_arm_coverage.py`: all pass except `test_the_pooled_correlation_is_not_reported`, which needs the
  owner's `spiral_out` and fails on main too.
- **The mutants above** were run in scratch worktrees, each restoring its file after it ran. All 17 fail a new test.
- **Guards and audit:** the nine doc-guard files and the four test files above were run on main and on the branch,
  with the doc audit (`audit_doc_references.audit()`).
  - They differ only by the seven new tests: 147 passed on main, 154 on the branch.
  - The two failures are the same: `test_live_documents_stay_clean`, from villa paths, and the pooled-correlation
    test above.
  - The audit gains no entries.
- Ruff 0.9.10 `check` and `format` are clean on the changed Python files, which were formatted before.
- **The standard suite** with the locked-package overlay gave 2799 passed, 22 skipped and 1 xfailed, as on main,
  with the same ten environmental failures.
  - The first run overlapped a stash of the working tree. It was re-run on the committed tree with the same result.
  - No suite file runs or reads the scripts and tests changed after it.
- **Independent review** of the first commit, in a worktree without villa. It found nothing blocking.
  - **It confirmed:**
    - every tier against the drivers and the reports;
    - the README's counts;
    - that the 22 untagged scripts are launchers;
    - the preregistered specification of `nosamecur_s4`–`s6`;
    - the noise-floor comment.

    It found no other unvendored fit arm in `scripts/`, `reports/` or `docs/`.
  - **Its should-fix findings:**
    - three more scripts with tier groups, against this doc's claim that there were none;
    - the driver check reading only `cd`;
    - loose thresholds and a swallowed exception, which let a duplicate or a mis-parsed tag pass.
  - **Its nits:**
    - the counts (52 drivers and 11 unclassified, where the first commit's message says 51 and ten);
    - "74 vendored fit drivers";
    - the `$SEED` tag;
    - directory names standing for commits;
    - the reports that disagree on `curbase_s4`–`s9`'s fit tree;
    - `correlate_geometry_ink.py`'s two tiers;
    - `audit_arm_coverage.py`'s pattern.
  - All are addressed above. Directory names standing for commits is left as an observation.
