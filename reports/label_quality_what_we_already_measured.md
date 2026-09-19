# What our patch studies already say about villa's label-quality bottleneck

**2026-09-15.** No new measurement. This connects results we already hold to an open problem villa
names in `scrollprize.org/docs/37_2026_open_problems.md`, and states what would actually settle it.
Written after checking `20_community_projects.md`: the catalogue lists many labelling *tools*, and no
label-snapping or active-learning project.

## Villa's claim

> "label quality is now one of the main unwrapping bottlenecks"

with two proposed directions — **label snapping** (move approximate labels onto the most plausible
surface using the raw CT signal) and **active learning** — and a hypothesis:

> "a smaller set of precise labels in hard regions may be more useful than a larger set of approximate
> labels in easy regions"

## What we measured, and how it bears on that

`reports/patch_bootstrap_verdict.md` tested a label-selection rule on the spiral fit: keep only the
patches the previous fit satisfied well (`fraction >= 0.90`), refit, and score reading.

* **Reading did not improve.** Ink **−0.83%, p=0.89** against an area-matched random control.
* **Geometry did, sharply: +17.66%, p<1e-4** — and that is close to circular, since the selection
  criterion *is* the geometry residual.
* **The follow-up ruled out the obvious escape.** `STRIPMATCH` equalised the in-strip evidence the
  selection had removed, and reading still did not improve (**−3.80%, p=0.55**). So the failure is not
  merely that selection starved the scored strip.

**The part that speaks directly to villa's hypothesis:** patch satisfaction **falls with radius,
r = −0.21 over 35,963 patches**, so a 0.90 threshold drops *outer* patches disproportionately. Our
selection rule kept the regions the fit already agreed with — the **easy** ones — and discarded
harder ones.

So the measured result is: **selecting labels by the fit's own agreement does not improve reading, and
selecting the easy regions specifically does not.** That is consistent with villa's hypothesis, which
says the value lies in *hard* regions. It does not confirm it — we never tested the hard direction.

## What this does NOT show, stated plainly

**We did not test label snapping.** Our selection criterion is the fit's own residual, which is
circular: refitting on what a fit already satisfied cannot discover anything the fit did not already
believe. Villa's proposal is different in the way that matters — snapping uses the **raw CT signal**,
which is independent of the fit. **Our negative does not transfer to it.** It narrows the search
space: it rules out the circular operationalisation, leaving the non-circular one as where any value
must be.

## What would actually settle it

A test with the same structure as the studies above, but with a **non-circular** selection signal:

1. Move labels using the CT signal alone (snapping), never the fit residual.
2. Refit, and score **reading** — `total_fg_pixels` on the scored strip — not geometry. Every study
   here that scored geometry alone would have reported a win where reading was flat; that pattern has
   now recurred four times.
3. Include an **area-matched control**, because changing labels also changes how much evidence the fit
   gets, and a two-arm design cannot separate "better labels" from "different amounts of label".
4. Power it honestly: at the current-tier seed CV of **0.0536** and three fits per arm, the loop
   resolves about **12%**. A null below that bounds nothing and must be reported as "no effect larger
   than ~12%". *(Corrected 2026-09-19 from 0.0263/6%: six unused `curbase` seeds doubled the floor —
   `reports/six_unused_seeds_double_the_current_floor.md`. This makes the design MORE demanding.)*

Points 2–4 are the parts this project has already paid to learn, and they are transferable regardless
of who runs the study.
