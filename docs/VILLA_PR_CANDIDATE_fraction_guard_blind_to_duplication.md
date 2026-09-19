# villa PR candidate — DRAFTED, not opened. Needs a judgment call.

A slot is free (2 of 3 open). This is the strongest candidate found since #1805, and it is more
borderline than the four that merged — hence drafted rather than sent.

## The claim in `autoresearch.md`

> "We also track **`overall_fg_fraction`** … as a **secondary / sanity metric**. **It guards against
> gaming**: if a change balloons `total_fg_pixels` only by inflating the surface with garbage
> geometry, the fraction will collapse."

**The conditional is true.** An arm rendered with degenerate geometry (`dup_armBAD`) has fraction
**0.00402** against a baseline **0.00885** — the guard fires exactly as described.

## The blind spot

**Duplicated coverage evades it**, because a duplicated winding carries duplicated *ink*: numerator
and denominator scale together, so the ratio barely moves.

| arm | `total_pixels` | `total_fg_pixels` | `overall_fg_fraction` |
|---|---:|---:|---:|
| baseline, 10 distinct windings | 26,754,900 | 236,683 | 0.00885 |
| **+ an 11th mesh that is a COPY of w015** | 29,792,000 (**+11.4%**) | 270,314 (**+14.2%**) | 0.00907 (**+2.5%**) |
| degenerate geometry, for contrast | 24,175,800 | 97,202 | **0.00402** |

The duplicate arm's **occupied cells are byte-identical to the baseline's** — it adds no papyrus at
all — and it still gains **+12.59%** on the objective, against **+12.83%** for an arm that adds a
genuinely new winding. The fraction **rises** rather than collapsing.

From `reports/duplicate_coverage_inflates_the_objective.md`, pre-registered before any arm was
rendered, verdict SUPPORTED, amended twice in public when a seed-noise floor was applied wrongly and
then corrected.

## Why this is worth a caveat

Converged fits already carry a `gap>=2` overlap of **0.09–0.10%**, so this is not hypothetical
geometry — duplication occurs naturally, just far below the deliberate 10.32% tested. A change that
*increased* overlap would read as an ink gain with a healthy fraction, and both stated guards would
pass it.

The satisfaction cross-check cannot catch it either: those metrics are written into the **fit**
directory by `fit_spiral.py`, while duplication is a property of what gets **rendered**.

## Suggested change — one sentence, in the existing paragraph

> … the fraction will collapse. **Note that duplicated coverage is not caught this way: a repeated
> winding scales foreground and total pixels together, so the fraction holds while
> `total_fg_pixels` rises.**

## Why it was not sent

Unlike #1721, #1722, #1780 and #1805, nothing here is **wrong** in villa's tree. The conditional as
written is accurate; what is offered is a caveat their measurement did not cover. That is closer to a
recommendation, and recommendation-shaped PRs are what got eleven closed before the profile was
understood.

**The case for sending it anyway** is that #1780 was the same shape — it said the doc did not state
what its own robustness rule accepts — and that merged.

**Decision needed.** If sent: re-verify the paragraph against current upstream first, no AI-authorship
marker, and cite the numbers rather than the report.
