# DRAFT (NOT POSTED) — comment on villa #191, fiber half

**Status: drafted 2026-08-23, NOT posted.** Jon's call.

Target: a comment on https://github.com/ScrollPrize/villa/issues/191.

Why this and not the surface half: the surface work in that thread is crowded and expert
(5-6 people, preregistered hash-verified ablations, active 2026-08-22). We would add nothing.
The fiber half is different: the issue's own success criterion is "long connected components
without branching", and across ~80 comments the words ERL, run length and branching never
appear. Nobody has tested against the criterion the issue itself states.

Constraints held deliberately:

- **Offers an instrument, claims no result.** We have no tracer worth showing: connected
  components beats ours on every cube. The comment says so outright. This thread audits
  ruthlessly (count mismatches, byte corruption, unit errors and inflated significance all
  caught and corrected publicly within days), so an overclaim would be caught and deserved.
- **Builds on Jinhojeong's own argument rather than lecturing.** Their VOI critique ("the
  blend collapses them into 1/(1+total)", so a fused pair scores perfectly) is structurally
  the same finding as ours, on surfaces instead of fibers. Citing it makes this an extension
  of the thread's reasoning, not an outsider's correction.
- **No prize mention, no listing request, no link to our submission.** It answers a gap they
  defined.
- **Numbers are the shipped floor table**, reproducible offline from the public repo.

House style: no em-dashes or en-dashes.

---

## Comment body

The surface side of this thread has gone deep on connectivity measurement, and the fiber side
has not. I think that gap is worth naming, because this issue defines fiber success as "long
connected components without branching" and I cannot find a single measurement of that
anywhere in the thread.

@Jinhojeong's point about VOI applies almost verbatim to fibers. The argument there was that
blending split and merge into `1/(1+total)` lets a fused pair of sheets score perfectly,
because two touching sheets are already one connected component before any model runs. The
fiber analogue is worse, because the usual per-voxel scores are not merely blunt, they are
constant. On one 256 cube from villa's `fiber-skeletons` dataset, four completely different
instance labellings score identically:

```
labelling                  ERL   ERLpen  coverage  precision
oracle (disclosed)      258.27   239.46    1.0000     1.0000
one instance for all    199.18     0.00    0.9177     0.2194
connected components    197.11    37.13    0.9177     0.2194
one instance per voxel    0.94     0.94    0.9177     0.2194
50 random instances       0.98     0.00    0.9177     0.2194
```

Coverage and precision cannot separate an oracle from `numpy.random`, because both are
properties of the shared fiber mask rather than of the labelling. Only expected run length
and the merge count move.

Raw ERL alone is gameable in the same way the VOI blend is: labelling everything as one
instance scores 199.18 against the oracle's 258.27, within 23 percent, while its
merge-penalized ERL is exactly 0.00. So the pair is needed, not either alone.

If it is useful, the instrument exists and is public: 11 hand-traced cubes from the
`fiber-skeletons` dataset packaged as scoring targets with the floors above published
alongside, MIT, scoring offline with no GPU and no network.
https://github.com/jonmarrs/scrollgt

Two caveats so this is not mistaken for a claim. First, I am not showing a good tracer:
connected components beats our own on every cube, on both ERL and merge-penalized ERL, which
is the main reason I trust the metric. Second, ERL is a length statistic and does not compare
across cube sizes, so 512 cubes need their own class (our 512 oracles run 497 to 513 against
222 to 262 for the 256 cubes, roughly 2x, for purely geometric reasons).

Happy to run any labelling you want scored against these, or to leave the targets and floors
for whoever wants them.
