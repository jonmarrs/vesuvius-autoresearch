# Can villa's objective be raised without reading more? Three measurements, assembled

**2026-09-19.** A synthesis, not a new measurement. Every number here is from an existing report; what
was missing was the join.

## The question

`total_fg_pixels` is what villa's autoresearch loop optimises. **Can it be raised without recovering
more text?** I spent 2026-09-19 approaching this through strip area and reached a weak negative, not
realising two of the three pieces had been measured on 2026-08-31.

## What is established

**1. The objective rewards duplicated coverage exactly as much as real coverage.**
`reports/duplicate_coverage_inflates_the_objective.md`, pre-registered, verdict SUPPORTED. Three arms
off one fit: arm B carries an eleventh mesh that is a **copy** of w015's geometry, with occupied cells
**byte-identical to baseline** — zero new papyrus. It gains **+12.59%** on `total_fg_pixels`, against
**+12.83%** for arm C, which adds a genuinely new winding.

**So the metric cannot distinguish a duplicated winding from a real one.** That is the clean
demonstration that it is gameable in principle.

**2. Natural duplication is tiny.** `reports/duplicate_coverage_is_an_outer_winding_phenomenon.md`
and `reports/a_cheap_guard_the_metrics_lack.md`: converged fits carry a `gap≥2` overlap of
**0.09–0.10%**, reproducible, 98% concentrated in the outermost windings. Three orders of magnitude
below arm B's deliberate 10.32%. *(That report's explanation for the concentration was withdrawn on
2026-09-01; the measurement stands.)*

**3. The loop's knobs do not move strip extent.** `reports/the_knobs_do_not_move_the_strip.md`, today:
seven arms at w010–011, four distinct manipulations including two loss terms zeroed outright, span
**1.35%** in strip area against 0.44% for seeds alone.

## The answer

**In principle yes; by the routes measured, no.**

The objective is genuinely blind to whether coverage is new — a duplicated winding buys the same
12.6% a real one does. But neither path that could exploit that moves far in practice: natural
duplication sits at 0.1%, and the config knobs the loop tunes move strip extent by ~1%.

**So villa's loop is not quietly winning on duplicated or enlarged surface.** The metric's blindness
is real and worth knowing — it means a *bug* that duplicated windings would read as a large
improvement — but it is not being exercised by the loop's own search.

## What this says about today

The strip-area line asked a weaker version of a question already answered by a sharper experiment.
**Arm B is the better instrument**: it holds the fit fixed and manipulates coverage directly, where
the strip-area approach hoped config variation would move extent as a side effect — and it does not.

The reason I did not connect them: every survey I built this week listed `outer_*` arms. The
duplicate-coverage arms are `dup_*` and the config variants are `seedarm_*`. **Of 56 scored arms on
disk, my listings saw 40**, and the 16 they missed included both pieces of the answer.

## What is still open

Whether `satisfied_area` — the loop's cross-check — is blind in the same way. Arm B's duplicate mesh
adds satisfied area without adding papyrus, so the guard may inherit the defect it is meant to catch.
The arms to test that already exist.
