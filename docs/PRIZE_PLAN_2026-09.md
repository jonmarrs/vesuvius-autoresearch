# September 2026 Progress Prize: plan

> ## CLOSED 2026-08-30: the bet below is dead, and nothing is filed on it
>
> The sheet-switch detector's premise does not survive reading the satisfaction metric: the
> two-winding condition it detects cannot be produced by displaced geometry, so neither an injected
> switch nor a real one would register. See `reports/sheet_switch_detector_premise_broken.md` and the
> closure note in `docs/preregistration/2026-08-29_sheet_switch_detector.md`.
>
> Pre-registered rule 2 committed us to filing nothing if the detector could not be shown to beat its
> floors. It cannot, so nothing is filed on it. **September has no bet as of this date**, and 16 days
> remain. What survives is reusable: the offline winding extractor, the reproducible spiral fit, the
> seed-agreement tooling, and `docs/RUNNING_THE_SPIRAL_FIT.md`.

**Written 2026-08-29, unstarted.** Deadline is the end of September; August was filed on the 23rd.

## What the prize actually says, checked rather than remembered

* **Eligibility is broader than "makes the collection easier to read."** The terms say *"Any
  contribution that makes any of the Open Problems easier to address will be eligible for a Progress
  Prize."* Eligibility is tied to the Open Problems document, not to reading text directly.
* **It is tiered**, not winner-take-all: $20,000 / $10,000 / $5,000 / $2,500 / $1,000 / $500 by
  significance, awarded monthly, multiple awards per month permitted.
* **The "public wishlist" is the `help wanted` label**, which is three issues (#191, #192, #193),
  unchanged since 2025-04-18. The broader surface is
  `scrollprize.org/docs/37_2026_open_problems.md`: six callouts plus a bottleneck table.

## The bet

**An evaluation suite for the global spiral fit, including a conservative sheet-switch detector.**

Two places in the wish list point here:

* Callout 5: *"Devise better **evaluation suites** and loss functions to improve the global spiral
  fit, or find efficient and automated ways to introduce exploitable prior information."*
* The bottleneck table, row **Sheet switches**: current approach *"VC3D inspection and manual
  correction"*, what would help: *"stronger local continuity constraints and **conservative failure
  detection**."*

## Why us, specifically

Not enthusiasm. Assets nobody else visibly combines:

1. **A published evaluation suite with anti-gaming floors** (ScrollGT v0.3.1). Floors now ship with
   every score in all three families, computed from the target rather than quoted.
2. **A working spiral fit on consumer hardware**, with a converged 30,000-step checkpoint at 65.4%
   satisfied patches, and `docs/RUNNING_THE_SPIRAL_FIT.md` so a judge can reproduce it.
3. **A record of publishing negative results and retracting our own claims**, which is the exact
   disposition a *conservative* failure detector needs: it must prefer silence to a false alarm.

## Why the previous attempt failed, and what changes

Issue #1621 argued villa's satisfaction metric *should* detect sheet switches. @pmh47 closed it:
the periodicity is intended, since in general no absolute winding exists per patch. That was
correct and we conceded.

The re-aim: **build the detector the wish list asks for, rather than claim an existing metric is
one.** That moves the claim from someone else's design onto our own artifact, which is where this
project's record is strong. The three concessions of 2026-08-27/29 were all claims about villa's
code; the four defects found the same week were all in ours, found by running things.

## Deliverable

A tool that takes a fitted spiral checkpoint and reports, with floors:

1. **Sheet-switch candidates**, ranked, with a conservative operating point.
2. **Floors**, so the number means something: flag-nothing, flag-everything, flag-random-at-matched-
   rate, and flag-by-a-trivial-geometric-proxy. Same discipline as ScrollGT's other families.
3. **Reproduction**, on public data, on one 24 GB GPU, from the existing guide.

## Pre-registered validation, to be committed UNRUN before any scoring

The shelved injection design is repurposed. Its old target (does the *satisfaction metric* accept a
displaced patch?) is dead. Its new target is legitimate:

> Planting a known whole-winding displacement in a converged fit, what fraction does the detector
> catch, and what does it flag when nothing was planted?

* **Controls that can fail:** a zero-injection arm must produce the detector's baseline false-alarm
  rate, and a half-winding injection must be caught at least as often as a whole-winding one, since
  it is a grosser error.
* **Decision rule fixed in advance**, including the outcome that costs us: if the detector does not
  beat the trivial floors, that is the finding, and it gets published as one.
* **Powered:** the baseline fit has 38,439 scored patches and 25,148 satisfied, so unlike the
  shelved study there is no risk of an `N < 30` denominator.

## Go / no-go gate, before writing any submission text

By **2026-09-15**, the detector must beat `flag-random-at-matched-rate` on planted switches by a
margin larger than the seed-to-seed spread across three seeds.

If it does not, **do not file this**. File nothing, or file the reproduction guide alone as a
smaller contribution. A second-order tool that does not beat its own floor is exactly the kind of
thing this project has learned to withhold.

## Risks, stated plainly

* **Crowded.** @Bullo27, @TAUIL-Abd-Elilah and @Jinhojeong are all active, rigorous, and faster than
  us on their own ground. TAUIL already has a winding diagnostic in PR #1626.
* **Second-order.** An evaluation tool does not itself read a scroll. Realistic placement is the
  lower tiers, not $20,000.
* **Our last contribution in this exact area was conceded.** That is an argument for building rather
  than claiming, not for avoiding the area.
* **No adoption.** ScrollGT still has no known users. A second tool with no users is a real
  possibility, and the honest mitigation is that eligibility does not require adoption, only that a
  contribution makes an Open Problem easier to address.

## What August claimed, so September does not repeat it

August was titled *"We audited our own benchmark in public and it got more honest"*: two retractions,
each paired with a guard in code. September must not be a third self-correction filing. If the
detector fails its gate, the correct move is to file nothing rather than to file another audit.

## Not doing

* PyPI publication (decided against).
* Competing on the spiral fit itself, or on ink detection: villa has more compute and an active
  internal loop, and `ink-detection/` is deprecated upstream.
* Opening a third lane.
