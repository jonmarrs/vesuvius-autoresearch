# October 2026: proposed directions (for the user to choose; nothing started)

**Written 2026-09-27**, after the catalogue check that `check-catalogue-before-picking-research`
requires. It was run against villa `f4570bfa6`:

* `scrollprize.org/docs/20_community_projects.md`, all 421 lines, read in full.
* `37_2026_open_problems.md`.

## What the check found

* **Spiral geometry tooling is crowded.** Catalogue entries include spiralcheck (which we
  validated), winding-ruler, winding-sync, spiral-fit-consumer-gpu, eligible-spiral-dataset,
  windcheck and TIFXYZ Doctor. Another geometry evaluator would not be unique.
* **Nothing in the catalogue measures whether the spiral loop's own objective can be trusted.** The
  loop in villa's `autoresearch.md` optimises `total_fg_pixels` through a frozen scorer. This
  project's body of work is exactly that measurement:
  * seed noise: fit-only CV 0.074 [0.051, 0.134];
  * the two-seed check accepts a null 1 time in 6;
  * flatten non-determinism: 3.04%, reproducible when asked;
  * install route: +5.0% to +9.2% (findings 65–66);
  * silently skipped re-renders (finding 65);
  * fitter and render-stage changes: finding 62 (no detected change) and finding 64 (inert).
* **The open-problems page asks for this directly.** Its fifth "how you can help" callout: *"Devise
  better evaluation suites and loss functions to improve the global spiral fit."* Its bottleneck
  table asks for "stronger diagnostics".
* **We are not listed at all.** A different project, `mojomast/vesuvius-autoresearch`, is. Recent
  third-party catalogue additions (#1896 ARGUS, #1718 eligible-spiral-dataset) merged within days.

## Recommended: A. An objective-hygiene checker for the spiral loop (engineering, ~1–2 weeks)

**The gap:** our findings are real but live in reports and one-off scripts, so nobody else can use
them. The Progress Prize scores *community use*, which this month rests on one item: #1886 fixing our
#1660.

**The tool:** a small, standalone, CPU-only checker a loop user runs on two finished runs, answering
"is this difference real?":

1. **Provenance gates:** same `vc_render_tifxyz` build and slice step (warn on the pre/post-#1146
   route mismatch); same scorer snapshot (#1805 records it); flatten determinism recorded.
2. **Render integrity:** refuse a run whose render log shows `all slices exist, skipping`, or an
   all-zero strip.
3. **Significance against a measured floor:**
   * report the difference with an interval, using a supplied floor or ours (fit-only CV 0.074,
     labelled as region- and tier-specific);
   * state the two-seed rule's exact false-positive rate, 1/C(2k, k).

**Validate it on our own corpus before release,** pre-registered: it must flag every known-bad
comparison (the skipped `smp_pub`, the install-route pairs) and pass the known-good ones.

**Why this over more measurement:** each additional finding adds a report nobody runs. A tool that
turns six of them into one command is the form in which they can be *used*.

## B. A catalogue listing PR (outward: needs the user's approval)

This would follow A once it exists: one entry in `20_community_projects.md` under Segmentation →
Tools, pointing at the checker and at ScrollGT.

* Our earlier listing attempt (#901) was declined. Recent third-party listings merged.
* The weekly new-item slot opens 2026-09-29.
* The villa SOP applies: small, evidence in the body, no AI markers.

## Not recommended now

* **Another geometry knob expecting an ink gain.** Six registered manipulations; zero improved
  reading (`no-lever-has-improved-reading`).
* **More sampler characterisation.** Findings 65–66 answer the question; more surfaces would narrow
  a range that is already actionable.
* **Anything that depends on unmerged villa PRs** (#1905) or a refreshed published image (#1588).
  Wait for upstream.

## Housekeeping: DONE 2026-09-27 (user approved)

* **Deleted the 530 GB of scratch caches** (`sampler_repro/src16|src4/home`, `sampler_memstat/src4m|pr1905/home`).
  Free disk went from 445 to 975 GB. Every result from them is committed.
* **Removed 18 merged worktrees and their local branches.** An earlier draft said "nineteen", which
  wrongly counted this one. Before removal each branch was verified to be on `origin/main` and to
  have nothing uncommitted besides the `.venv` symlink; `branch -d` re-checked the merge. The remote
  `worktree-*` branches on GitHub were not touched.

**User decision 2026-09-27: A, then B.**
