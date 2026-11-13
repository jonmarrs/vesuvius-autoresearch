# Design and architecture review — the owner's #401

Date: 2026-11-13. Baseline: `b00f7d9` (main after round #163's merge, which carries #401).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 04:12 UTC firing on 2026-11-13. The owner merged #401 at 03:40 UTC, during round #163. It
reports the kill test of the First Letters campaign: the published PHerc. 343 image, rebuilt on the owner's machine
on 2026-11-10 from the two published windings onward. The verdict is `REPRODUCED`, for the part of the chain that was
run. #401 also updates the research strategy to say so.

## What changed

### Eight more figures are bound to the record (`tests/test_first_letters_343_reproduction_report.py`)

This round made 55 single-figure mutants: 51 of the report and 4 of the strategy's new sentences. #401's tests killed
43. Two new tests bind eight of the twelve survivors to `reports/first_letters_343_reproduction.json`:
- **In the report:** the host's 4 cores and 31 GB; the 8 ink jobs as 4 models on the plain and the padded render at
  depth +1; the render's 66 layers of 2560 × 6720; the renderer's source tree.
- **In the strategy:** the render's 8 minutes, the ink step's 17 minutes, the 3,174 MiB peak, the 22 minutes the
  training loop was stopped, and the four sentences that date the kill test to November 10.

Each new test passes as merged and fails with its mutant (11 of 11: the eight survivors, one more of the strategy's
dates, and two mutants of the record itself).

The other four survivors have nothing in the record to bind to: "1/31 of the GPU time", the 14 GB working directory,
the torch version and the render's "about 1.5 GB".

### The prize roadmap carries a dated update (`docs/PRIZE_ROADMAP_2026-11-12.md`)

The roadmap merged in #410 was written from main before #401 was on it. It said the kill test was waiting on a
decision about the training loop. #401 shows that the test ran on November 10 and that the decision was made. The
roadmap now opens with an update that says so, names the lines it supersedes, and points the next step at the
recipe's mesh step, as the strategy does. Its body is unchanged.

## Verified, no change needed

- **Every figure I recomputed from the record matches the report.**
  - The whole image: 8,727 of 16,865,374 pixels differ (5854 × 2881), 0.052%, by at most 5.
  - The panel: IoU 0.9999, and at least 0.9997 in each of the 18 letter boxes.
  - The shift control: IoU 0.570, 0.179 and 0.052, with correlations 0.800, 0.228 and 0.006.
  - The image built without the published statistics: IoU 0.7324, correlation 0.956, and letter boxes at 0.514
    lowest and 0.811 median.
  - The job times: 171 to 190 s, 157 to 180 s and 424 to 427 s.
- **The arithmetic holds.**
  - The plain render's three villa jobs sum to 533 s against a recorded 535 s, and the padded render's to 495 s
    against 495 s. Together they are the 17 min 10 s.
  - 31 × 1,030 s is 8.9 hours.
  - 09:58 to 10:20 is 22 minutes.
- **The letter boxes sit on ink.** The share of each box drawn as ink in the published image runs from 0.13 to 0.80,
  with a median of 0.40, against 0.085 for the whole panel. So the per-letter IoUs are about letters and not blank
  papyrus.
- **The report states its scope as the record does.** Its "What this does not show" matches the record's
  `not_measured` list and its `scope`: the windings, the row lines, the letter boxes and the pooled statistics
  were taken from the publication.

## Observations for the owner (not changed)

- **The sweep is counted two ways.** The report gives the full recipe as "496 GPU jobs" and the full sweep here as
  "31 × 1,030 s, about 9 hours". The second is 31 depths of the 8 jobs that were run, which is 248 jobs. If a depth
  of the full recipe takes 16 jobs, the sweep here is about 18 hours and one depth is 1/62 of it, not 1/31. I could
  not read the recipe to tell: its repository is outside this session's access. `make_record.py` holds both 496
  and 8 as typed constants.
- **The comparison scripts have no tests.** `compare_image.py`, `check_render.py` and `make_record.py` ran on the
  owner's machine against the recipe's checkout and its outputs, neither of which is in this repository. They
  cannot be rerun here. Read alone, `compare_image.py` does what the report says: R − B as the ink tint, a
  threshold of 8, IoU and correlation on the panel, the same on a panel rolled by 16, 64 and 256 pixels, and the
  same in each letter box.
- **Parts of the record are typed, not measured**: the scope lists, the renderer's source, the job counts and the
  checkpoint notes are strings in `make_record.py`.
- **The renderer's tree identity was not checked here.** The report says villa `75c79ac5f` has the same
  `volume-cartographer` tree as `41701aa`. This container has no villa checkout.
- **The ink times are upper bounds**, as the report says: finding 109 used the GPU during the run.

## Verification

- **The touched module passes.** `test_first_letters_343_reproduction_report.py` gives 10 passed, against 8 as
  merged.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 216 modules give the same failing ids on `b00f7d9` and on this branch.
- **The test modules outside the suite.** The 250 modules give the same failing ids on `b00f7d9` and on this branch,
  and two more passes: the new tests.
- **The doc audit**, run alone, lists the same unresolved references as on `b00f7d9`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

The failing ids are this container's, as in the last two rounds: it has no villa checkout.

## A note on this round's work

- **This is a review of a report, not a rerun.** Nothing here ran the recipe, a render or an ink model.
- **Still not reviewed:** #396, #403 and #404, and the estimator and resampler of #390.
- **One request was refused.** I asked for read access to the recipe's public repository, to settle the job count
  above. The session's permission check denied it, and I did not look for another way in.
