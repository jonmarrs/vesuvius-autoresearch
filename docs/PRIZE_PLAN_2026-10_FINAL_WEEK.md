# October Progress Prize: readiness and final-week plan

Reviewed **2026-10-23 UTC**. We have a credible submission now, based on three
merged Villa contributions. Additional merges or research results can improve
it; they are not prerequisites for filing the work already completed.

The deadline is **October 31, 2026 at 11:59 p.m. Pacific** (November 1 at
06:59 UTC). Target filing on **October 29**, leaving time to check the receipt.
Do not mark the package filed or create a submission tag until it is actually
submitted and the receipt is preserved.

## What is ready

| Evidence | Verified status |
| --- | --- |
| Villa #2022: runner instructions | Merged October 11 Pacific; fixes launch and silently dropped overrides. |
| Villa #2044: sequential ink-scoring folds | Merged October 11 Pacific; a real outer strip changes from OOM to completing at 13.8 GB. |
| Villa #2155: pip CUDA dependency group | Merged October 21 Pacific; package-selection evidence is in the PR. |
| October detailed filing | 31 existing number/version checks pass, with no skips after checking fresh sibling repositories. |
| Live upstream claim checker | Passes; the three October merges and their Pacific dates match GitHub. |
| Existing filing URLs | All 19 pre-update links returned HTTP 200. Recheck final text on filing day. |
| Live form | October title and four-part contribution question confirmed; required email/name/team/terms and optional Discord field identified. |

[Concise form answers](PRIZE_FILING_2026-10_FORM_ANSWERS.md) now lead with the
three merged fixes. The [longer draft](PRIZE_FILING_2026-10_DRAFT.md) preserves
the benchmark research and its disclosures. Three merges are evidence of
integration, not a guarantee of a particular award or of ongoing usage.

The official rules favor early releases, actual use, real-data improvements,
useful fixes, actionable analysis and documentation. They explicitly ask for
small bug fixes to be bundled. The checked source is Villa `e2254ebe`,
[`scrollprize.org/docs/34_prizes.md`](https://github.com/ScrollPrize/villa/blob/e2254ebe0168a232e5ba7b94997c749b4e6a4544/scrollprize.org/docs/34_prizes.md#progress-prizes).
The live form loaded successfully; direct access to the deployed prizes page
returned HTTP 403, so the current repository source supplied the rules.

## Work ranked for the time remaining

| Priority | Work and useful outcome | Finish condition / dependency |
| --- | --- | --- |
| 1 | Complete the existing Villa contributions: #2141 SQLite track reader, #2258 fractional seeding, #2259 headless CLI docs. These address real workflows and already have measured evidence. | Available GitHub Actions runs pass and local checks pass. Incorporate new review feedback if it appears. A maintainer must merge: the linked account has read-only Villa permissions and normal merge returned HTTP 403. Vercel preview authorization is also outstanding. |
| 2 | Publish the prepared #1482 native retry fix when permissions and an upstream PR slot allow. It turns deterministic hangs into bounded, descriptive failures. | Branch `jonmarrs/villa:fix/native-retry-cycle` is pushed; 13 selected tests pass. The real-mesh probe proves termination for deliberately supplied invalid regions. It does not reproduce full training or default discovery. Get a reproducible complete-environment or real-training confirmation if available. |
| 3 | Make the existing benchmark easier to use: a compact example showing a real held-out Scroll-5 miss beside a Scroll-3 control, with exact commands, fixed versions and clear in-sample disclosure. | A fresh user can reproduce the published rows with documented inputs. Use the current released ScrollGT v0.8.2 and public artifacts; no retuning or new quality claim. A full cold-run check is still to be done here; the readiness review checked the cited versions and released metadata only. |
| 4 | Run one focused research follow-up: test tracing context on the 24 octants from Finding 95. | Conditional on GPU access and the original cubes/checkpoint/output artifacts, which are unavailable in this execution environment. Prepare the registration before outcomes; pin the prior study's tracer, scorer, checkpoint and global seed grid. Compare independent octant runs with existing crops of whole-cube runs on the same ground truth at tolerances 2 and 4. Estimate runtime from a pilot and cap the job at one GPU day. Do not retune thresholds on these results or describe cropped outputs as new tracing runs. |
| 5 | Publish the eight-line reference-provenance clarification, after the code fix. It helps readers interpret tracer-assisted references. | Pushed branch `jonmarrs/villa:docs/fiber-reference-provenance`, backed by all 853 public annotation files. This establishes provenance, not score bias or an improved tracer. It shares the upstream publication permission blocker. |

The integration's creation and merge errors are preserved in
[the review record](../reports/evidence/villa_pr_review_2026-10-23.json).
No upstream comments or messages were sent as part of this planning review.
Open or pushed work stays separate from the filing's merged credits.

## Suggested sequence

- **October 23–24:** finish the filing evidence checks and concise narrative;
  keep the existing PRs ready for maintainer review. Prepare the native retry
  handoff and the benchmark reproduction example.
- **October 25–27:** finish that CPU reproduction work. If GPU access and
  inputs are available, run the one registered tracing-context test and
  preserve every outcome, including a null or failure. Otherwise keep the
  completed Finding 95 result; it already answers the scoring-size question.
- **October 28:** freeze the submission narrative and public evidence links.
  Review each claim against its source; make pending/merged status explicit.
- **October 29:** recheck the current rules and form, complete personal fields
  and terms, submit, then save the receipt and exact submitted answers.
- **October 30–31:** reserve for receipt issues and material updates. A new
  merge can be included if the form's update mechanism permits it; first
  check whether the receipt supplies an edit link.

Avoid a broad architecture rewrite or a last-week model sweep: neither has
a demonstrated path to a useful community result within this schedule.
Additional test counts and internal refactors are verification, not separate
claims of improved reading. A separate research filing is warranted only if
the result has its own clear contribution and evidence; the small-fix bundle
is ready to proceed independently.

## Checks performed

The [dated readiness record](../reports/evidence/october_prize_readiness_2026-10-23.json)
preserves live merge timestamps, rules/form fingerprints, the public form's
required questions, sibling repository revisions and all HTTP link results.
The concise contribution answer is 371 words. The detailed draft now includes
Finding 95 with a new numeric binding test; the concise answer stays focused
on the three merged fixes.

```sh
VILLA_REVIEW_ROOT=/workspace/villa-native-retry AGENTS_AGENT_MODE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
/workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 \
  /workspace/villa-review-evidence/run_python.py -m pytest -q \
  tests/test_filing_2026_10_numbers.py \
  tests/test_october_prize_form_answers.py \
  tests/test_check_filing_upstream_claims.py tests/test_octant_crop_report.py
# 59 passed in 0.55s

python3 scripts/check_filing_upstream_claims.py --month 2026-10 \
  --filing docs/PRIZE_FILING_2026-10_DRAFT.md
python3 scripts/check_filing_upstream_claims.py --month 2026-10 \
  --filing docs/PRIZE_FILING_2026-10_FORM_ANSWERS.md
# Both: PASS: every upstream claim in the filing matches GitHub.

VILLA_REVIEW_ROOT=/workspace/villa-native-retry AGENTS_AGENT_MODE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
/workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 \
  /workspace/villa-review-evidence/run_python.py scripts/smoke_test.py
# 8/11 passed, 3 skipped, 0 failed in 6.7s
```

The smoke skips need absent training data or the unavailable bg2 augmentation
entry point. No packages were installed. Fresh sparse checkouts supplied the
tools' actual version files and ScrollGT's tagged metadata, so the filing's
four previously skipped sibling checks now run. This does not constitute a
fresh run of the complete benchmark or its GPU entrants.
