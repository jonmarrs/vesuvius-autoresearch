# The autoresearch loop has been dormant 70 days, on a track villa has since deprecated

**2026-09-19.** Status, not a finding. Recorded because a dormant component with no status note is an
invitation for a future session to restart it on a dead track.

## The facts

* **`.loop_paused` is dated 2026-07-11** — 70 days. Nothing has run it since.
* The loop operates on the **ink-detection** track (`src/vesuvius_autoresearch/detector/`), which is
  what `docs/` and the loop's own selection metric (`val_f1`, rewired 2026-07-11) are built around.
* **Upstream deprecated that track on 2026-08-17**: `af8bac80e ink-detection: deprecate legacy
  standalone ink-detection pip`. It is the **last commit to touch `ink-detection/` at all**; the two
  before it are from July.
* `spiral-fitting/` by contrast has been touched dozens of times in the same window, and every study
  in this project since July has been on it.

So the loop went dormant **before** the deprecation and the deprecation has since made that permanent.
The directory still exists upstream — it has not been deleted — so nothing will break loudly; it will
simply never move again.

## Why this is worth writing down

The loop is not obviously dead from inside the repository. It has a paused marker rather than a
retirement note, its code is intact and tested, and the CI guards around it still pass. A future
session reading `CLAUDE.md` or the loop's own documentation would find a working component with a
pause flag and reasonably conclude it should be resumed.

**Resuming it would spend compute optimising a detector on a track upstream has stopped developing**,
against a metric chosen for that track, while the live work is elsewhere.

## What this does not claim

* **Not that the loop is broken.** It is untested against current dependencies and no claim is made
  either way; that check was not run, because the answer does not change the recommendation.
* **Not that ink-detection is worthless.** `reports/ink_detection_reproduction_result.md` records
  reading legible ink at 224px on real Scroll-1 segments, and that result stands. The track being
  undeveloped upstream is a statement about villa's direction, not about the physics.
* **Not a decision.** Retiring a component is the owner's call. This records the evidence that the
  question exists.

## The decision this needs

Either **retire it explicitly** — a note in `CLAUDE.md` and the loop's docs saying it is mothballed and
why — or **repurpose it** for spiral-fitting, which would be a substantial rewrite: different
pipeline, different objective (`total_fg_pixels` rather than `val_f1`), different data.

Leaving it as a bare `.loop_paused` marker is the one option that reliably wastes someone's time later.
