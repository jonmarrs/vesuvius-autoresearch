# Villa PR review, October 26

Reviewed the three open Villa PRs, their discussion timelines, exact diffs,
review threads and checks. Their heads are unchanged. No further source
defect was found in these three PRs; #2141 already addresses the maintainer's
SQLite dispatch and uncheckpointed-WAL comments.

| PR | Reviewed head | Local verification |
| --- | --- | --- |
| [#2141](https://github.com/ScrollPrize/villa/pull/2141), SQLite track stores | `19575a45` | 5 tests pass, including the read-only directory and WAL cases. |
| [#2258](https://github.com/ScrollPrize/villa/pull/2258), fractional seed planes | `242f0798` | 20 tests pass. |
| [#2259](https://github.com/ScrollPrize/villa/pull/2259), headless AppImage CLI | `d119561f` | Extracted `AppRun vc_render_tifxyz --help` exits 0 with no display; 7,422 bytes of help. |

Available GitHub Actions runs succeed. All three still have a failing Vercel
authorization status. Villa reports `push=false`, `maintain=false` and
`admin=false`. A normal merge of #2141, guarded by its reviewed head, again
returned HTTP 403, “Resource not accessible by integration”. No merge was
forced or status bypassed. The same permission applies to the other two.

The prepared native-retry branch still passes its 13 selected checks
(40 deselected). The targeted dataset source is unchanged between its
October 23 base and current Villa main `322cb0899`. The provenance evidence
and fractional-seeding/headless records also pass their supporting checks.
The [dated JSON](../reports/evidence/villa_pr_review_2026-10-26.json) preserves
the remote states, test results, blockers and source hashes.

## Fixed in the prepared seed-heading proposal

The [seed-heading draft](VILLA_DRAFT_volume_seed_heading.md) removed the 35°
seed rejection but left the run identity unchanged. Production resume
validation therefore accepted both a pre-change run with no selection field
and a record explicitly naming the old rule. Finished tiles stay in place,
so a partial run could silently combine tiles generated with different rules.

The follow-up patch records `seed_heading_selection='signed_ct_axis_v1'` in
the volume's `run.json`. The existing settings comparison now rejects a
missing or different selection before loading finished tiles. Matching
records still resume, and rejection leaves the saved record unchanged.
The shared CT heading definition used by training is unchanged.

Three regressions call the real CLI settings validation, replacing only
model/volume construction and stopping before tile loading. The missing and
old selection cases fail with the original proposal; the matching case
passes. With the follow-up, all three pass. These are configuration checks,
not new real-data or GPU measurements.

The original measured heading patch is unchanged. Apply the two patches in
order; the second affects resume compatibility and adds its tests:

```sh
git apply /path/to/vesuvius-autoresearch/repro/fibers/villa_volume_seed_heading.patch
git apply /path/to/vesuvius-autoresearch/repro/fibers/villa_volume_seed_resume.patch
AGENTS_AGENT_MODE=1 python -m pytest -q \
  vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/test_volume_seed_heading.py \
  vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/test_volume_seed_resume.py \
  vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tests/test_volume_performance.py
```

All 23 cases pass on current Villa main plus the patches. Local verification
used cached Python 3.10.21 dependencies and bypassed the unrelated package
initializer. An initial local launcher reran pytest inside spawned workers;
after correcting its main guard, the multiprocessing checks pass. No
repository multiprocessing code, packages or GPU jobs were changed.

Both patches are committed and pushed at `d1de9ec1e2e17ecd0f06754041141dfda243ddb3`
on `jonmarrs/villa:fix/volume-seed-heading`. The owner-repository checks now
exercise both patch applications and accept `VILLA_REVIEW_ROOT`, allowing
the two previously skipped source checks to run. All 94 selected owner
contribution and filing checks pass without skips.

No new upstream PR was opened: the three-open-PR cap is full. The proposal
also retains the required human-written motivation and unchecked personal
verification attestation. The original GPU comparison remains evidence for
fresh runs; no new GPU run, training run or Windows/macOS validation was
performed. Use a new output directory for the new rule, or the old code to
finish an old run; do not relabel its record or import its completed tiles.
