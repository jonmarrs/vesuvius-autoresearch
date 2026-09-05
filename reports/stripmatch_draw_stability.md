# The STRIPMATCH control does not depend on which draw it got

**2026-09-05, written while arms 2-3 were still running, with every endpoint unread.** Input-side
only. Reproduce: `scripts/build_stripmatch_dataset.py --stability 4`, tested in
`tests/test_build_stripmatch_dataset.py`.

## The limitation this addresses

`docs/preregistration/2026-09-04_stripmatch_followup.md` inherits a limitation the parent study
recorded before its own data existed: the control is **one draw, not a distribution over draws**, so
an unusually good or bad subset would bias the comparison.

For the parent's RANDOM arm that was discharged by showing the draw tracked the full population
(quality 0.7986 vs 0.8003; largest radial band gap 0.26 points). **That argument does not transfer to
STRIPMATCH**, which is *deliberately* unrepresentative: it is pinned to BOOTSTRAP's in-strip share of
0.4120 while the population sits at 0.4648. Matching the population is precisely what it must not do.

The right question is instead whether independent draws **under the same constraints** agree.

## Four draws

| seed | n | area vs target | in-strip share | mean satisfaction | overlap with seed 0 |
|---:|---:|---:|---:|---:|---:|
| 0 (the one in use) | 29,661 | 100.00% | 0.4120 | 0.8084 | — |
| 1 | 28,536 | 100.01% | 0.4120 | 0.8100 | 76.2% |
| 2 | 29,552 | 100.00% | 0.4121 | 0.8113 | 78.7% |
| 3 | 28,622 | 100.01% | 0.4120 | 0.8097 | 76.3% |

**In-strip share spans 0.0001. Mean satisfaction spans 0.0029.** Patch counts vary by about 4%, and
the draws overlap only **76-79%** — so these are genuinely different subsets, not re-orderings of one
set, and they still agree on everything the comparison rests on.

Against the effect being measured, the margin is large: the quality contrast this study manipulates
is BOOTSTRAP 0.9908 against STRIPMATCH ~0.809, a gap of **0.18**, roughly **60x** the 0.0029 spread
across draws.

## What this does and does not license

It licenses treating the seed-0 draw as representative **of draws meeting these constraints**, which
is the population the design actually cares about. The registration's fallback — "if the result is
close, the cheap follow-up is a second draw rather than more seeds" — is correspondingly less likely
to be needed.

It does not license anything about dimensions the constraints do not touch. The draws are pinned on
total area, in-strip share and (as a consequence) mean satisfaction; they are not pinned on spatial
position outside the strip, winding, or trace provenance, and two draws agreeing on the former says
nothing about the latter.

Nothing here is an outcome. Arms 2 and 3 are still running and no endpoint has been read.
