# DRAFT, NOT POSTED, AND SUBSTANTIALLY WEAKENED

Status: local draft. Nothing here has been sent to villa.

**Revised 2026-08-28 after @TAUIL-Abd-Elilah's real-checkpoint measurement on #1621.** The first
version of this draft argued that the autoresearch loop's anti-gaming guard cannot see a whole
winding error, and implied that this leaves the optimizer an unguarded direction. That evidence now
points the other way, and most of this draft's original value is gone. Keeping it as a record of
what changed rather than deleting it.

House style if any of it is ever used: no em dashes, no en dashes, no prize or submission language.

---

## What the original draft claimed

`spiral-fitting/autoresearch.md` sets up an autonomous optimizer whose objective is
`total_fg_pixels`, ink area recovered through a frozen scorer, and names the satisfaction metrics as
the guard against that objective being gamed:

> if ink coverage climbs while the satisfaction metrics fall off a cliff, be suspicious that you are
> contorting the surface to catch stray ink rather than fitting the scroll better.

The draft argued that this guard has a blind spot in a direction the optimizer is free to move in,
because #1621 measured the satisfaction statistic as invariant to a whole winding displacement.

## Why that is now overstated

@TAUIL-Abd-Elilah ran the check against two real 5,000-step PHercParis4 checkpoints with
point-collection supervision withheld. At the one usable real anchor the self-derived winding
disagreed with the annotation by +8 and +6, replicated across seeds as +8, +7, +7 and +6, +6, +5.

But the native strict metric rejected those patches anyway, at 13.15% and 24.98% strict satisfied
area, and all six patch verdicts were false. The statistic is invariant; the surrounding
computation still refused the patches. A guard that rejects by a different route is not an
unguarded direction.

Two further limits from that work, both of which apply to our synthetic result as well:

* A difference sitting at a near-constant +6 to +8 across seeds is more consistent with a global
  integer gauge offset than with a localized sheet switch, and neither our probe nor that one can
  distinguish them. We imposed the displacement, so we measured invariance under a displacement we
  chose, not prevalence in fits.
* `abs_winding.json` ships 59 anchors across 6 collections, and only one was directly attached in
  that z window. The binding constraint on any prevalence claim is annotation supply, not the
  diagnostic.

## What survives

Narrowly, and only this:

* The acceptance half-width is exactly the radius tolerance in units of `dr_per_winding`, under
  both the reporting and splicing configs, to six decimals.
* The invariance is exact rather than approximate, and the half-winding controls reject, so the
  zeros are informative rather than an inert harness.
* `get_track_satisfied_counts` computes `mode_winding_per_track` and the chunked wrapper that
  `satisfaction_metrics.py` imports discards it, so the quantity a conservative check needs exists
  one call below the boundary.
* `winding_is_absolute` is read by six modules plus a test at `6847063ff`, and zero times by
  `satisfaction_metrics.py` or `tracks.py`.

## What does not survive, and should not be repeated

* That the guard leaves the optimizer an unguarded direction. Not shown, and the real-fit evidence
  is against it.
* That villa cannot detect this. `find_inconsistent_windings.py` already implements the full
  propagation. It is a standalone tool rather than part of the metric, which is a much weaker
  statement than the one the first draft implied.

## If anything here is still worth posting

The one open thread is quad level rather than patch level: in seed 101's second fit an anchor quad
was native-strict-true while disagreeing by +5, inside a patch that still failed. That is a single
quad and does not support a claim on its own. It would need either more anchors or a deliberate
injection study, and the anchor supply says the first is not available.

The honest summary is that this line of argument has been answered better by someone with real
checkpoints than we could answer it ourselves, and the useful next contribution is probably
measurement of something else.
