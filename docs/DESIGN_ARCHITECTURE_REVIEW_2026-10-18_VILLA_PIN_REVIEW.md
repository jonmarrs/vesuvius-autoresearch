# Design and architecture review — the villa pin review's checklist

Date: 2026-10-18. Baseline: `89ab4b6e` (main after #124). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/review_villa_pin.py`, the handoff step that turns the villa upstream audit into the checklist read
before a pin update (`reports/villa_pin_review.{json,md}`). The previous review
(`DESIGN_ARCHITECTURE_REVIEW_2026-10-18_VILLA_UPSTREAM_AUDIT.md`) left two of its defects as observations. Also
read: `scripts/inference/run_ranked_inference.py`, the handoff's inference step, which had no dedicated review.

## What changed

- **The checklist left out the areas that hold a pin update.**
  - `build_markdown_checklist` listed only lasagna, Volume Cartographer and the prize docs. The JSON's
    recommendation becomes `hold_pin_until_required_tests_pass` when a high-risk area changes: optimized inference,
    the ResNet3D decoder, the prize docs.
  - Two of those three, and the medium-risk `vesuvius_data`, never appeared in the Markdown. So the checklist a
    reader follows did not contain the checks the recommendation requires.
  - It now lists every area, unchanged ones ticked.
- **The check those two areas require could not run.**
  - It was `uv run python scripts/smoke_test_villa_optimized_inference.py`, which exits 2 without `--output`,
    `--report` and `--command-out`. The smoke also needs new, separate destinations on every run
    (`docs/CHECKPOINT_EXPORT.md`).
  - The check now makes a fresh `outputs/pin-review.XXXXXX` directory (gitignored) and passes all four options.
    Run here from the repository root with `UV_NO_SYNC=1`, it exits 0 with `"status": "PASS"` and writes the three
    files.
- **Two tests.**
  - The checklist names every area, and a changed high-risk area's checks.
  - The smoke check names every option the real script reports as required when run bare. This ties the check to
    the script, not to a copy of its arguments.

## Verified, no change needed

- **The other checks are runnable.** Each option they pass exists in its script's `--help`, and the inputs they
  name exist:
  - `validate_prize_artifact.py --metadata predictions/pred_10_1000_1000_64x64_meta.json`;
  - `build_lasagna_fiber_worklist.py --ranked … --limit 12`;
  - `rank_scroll23_candidates.py --queue … --prediction-dir … --out …`;
  - the handoff with `--preflight-only`.
- **`run_ranked_inference.py`.**
  - Its default output stem, `pred_{z}_{y}_{x}_{w}x{h}`, does not name the volume. But every row of the committed
    ranked list carries its own `artifact_stem`, and the 110 are distinct, so no two candidates write the same
    files.
  - `--execute` runs serially and stops on the first failure.

## Observations for the owner (not changed)

- **The smoke validates our checkpoint's envelope, not villa's code.** Its report says so ("checkpoint envelope
  validation only"). It is the check the pin review asks for when villa's optimized-inference or decoder code
  changes, so it cannot catch a break in that code. A check that loads the exported checkpoint through villa's
  changed code would.
- **The checks use `uv run`,** which syncs the environment first. Offline, as here, that fails before the script
  starts. `UV_NO_SYNC=1`, which the worktree docs already ask for, avoids it.
- **The committed `reports/villa_pin_review.*` date from June**, as the previous review noted. The next handoff run
  regenerates them.

## Verification

- `pytest tests/test_review_villa_pin.py`: 6 passed (4 before, 2 new).
- **Mutation check.** Each mutation fails a test:
  - the three-area filter restored;
  - the bare smoke command restored.
- **The new check command,** run end to end as above.
- Ruff clean on the changed files.
- The standard suite: see the PR.
