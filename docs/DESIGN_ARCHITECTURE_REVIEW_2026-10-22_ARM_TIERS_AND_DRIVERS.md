# Design and architecture review — the arm tier table against the drivers that record what ran

Date: 2026-10-22. Baseline: `674bc399` (main after #187).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how the spiral studies decide which code tier an arm belongs to, and the record that decision rests on.
- **The table.** `scripts/arm_tiers.py` is the single table of arm → tier (pinned `6847063f`, current, upstream).
  It raises on an unclassified arm.
- **The record.** `repro/spiral_fits/` holds 74 vendored fit drivers. No review had named this directory.
- **The other encodings.** `measure_noise_floor.py` cross-checks its groups against the table at import.
  `soft_count_study.py` carries groups of its own.

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
    - 51 drivers set a run tag;
    - every classified one (41) fits on the tree its tier names;
    - every rule in the table is backed by at least one driver;
    - the unclassified ten are smoke and exploratory arms, which raise by design.
  - **Change:** two tests now hold the table to the drivers. One checks tree against tier for every classified tag;
    the other checks that every rule has a driver.
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
- **`soft_count_study.py`'s tier groups were a third, unchecked encoding.** Its `PINNED` and `CURRENT` groups agree
  with the table today. **Change:** a test checks them, as the noise-floor groups are.
- **The README was out of date.**
  - It said "60 files"; 74 are here, 14 of them copied as studies launched.
  - It listed only the anchor pilot, not `anchor10cov_s2` and `s3`.
  - It described two tiers, though `fit_upfit.sh` has been the upstream tier since 2026-09-24.
  - **Change:** it names the three tiers and points to `arm_tiers.py` as the table and the test that checks it. It
    lists the deliberately unclassified drivers, and gives the counts.
- **A stale comment.** `measure_noise_floor.py` called the `anchor10cov` group "registered but not yet run". It
  ran (`reports/anchor_ablation_verdict.md`) and is a row of `reports/noise_floor_by_tier.md` (0.0419). The comment
  is corrected; the code is unchanged.
- **Tests** (`tests/test_arm_tiers.py`, +4, outside the standard suite as before).
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

## Verified, no change needed

- **`curbase_s*` and `nosamecur_s*` name both trees.** The pinned name appears in a header comment about the
  pinned corpus; `PYTHONPATH`, `cd` and the interpreter are all `villa-spiral-current`.
- **`fit_curbase_s4.sh` matches its own claim.** It is identical to s1 apart from its seed and the
  forward-prediction comment; both fit dataset `spiral_s1`.
- **`anchor10cov_s1`** appears only in comments explaining why the pilot keeps its own tag.
- **The other scripts that mention tiers** carry per-tier constants or comments, not arm groups.
  `correlate_geometry_ink.py` imports the table, which an existing test checks.

## Observations for the owner (not changed)

- **Copy the three drivers.** They are in `spiral_out` (`nosamecur_s4`–`s6`). Then empty `_NOT_VENDORED`.
- **Live copies aren't compared.** The vendored drivers are copies, and nothing here compares them with the live
  ones on the owner's machine. A driver changed in `spiral_out` after vendoring would not show.
- **Within-tier trees.** `measure_noise_floor.py` and `soft_count_study.py` split `curbase` by tree within the
  current tier (`d8c5f488a` / `be09a8503`). That split lives in their groups, not in the tier table. The noise-floor
  comment records that it was measured immaterial.

## Verification

VERIFICATION
