# DRAFT, NOT POSTED

Status: local draft. Nothing here has been sent to villa. It needs Jon's approval before it goes
anywhere, and per the standing rule on issue #1621 (three messages from us in one day) it should not
be posted into that thread until someone replies there. If it is posted at all it may be better as
its own issue, since the subject is the autoresearch guard rather than the metric identity.

House style enforced below: no em dashes, no en dashes, no prize or submission language.

---

## The winding check the autoresearch loop is missing

`spiral-fitting/autoresearch.md` sets up an autonomous optimizer whose objective is
`total_fg_pixels`, the ink area recovered by rendering fitted meshes through a frozen scorer. It
names two guards against that objective being gamed. One is `overall_fg_fraction`. The other is the
satisfaction metrics:

> if ink coverage climbs while the satisfaction metrics fall off a cliff, be suspicious that you are
> contorting the surface to catch stray ink rather than fitting the scroll better.

That second guard has a blind spot in one specific direction, and it is a direction the optimizer is
free to move in.

### What was measured

On issue #1621 we reported that `get_patch_satisfied_areas` snaps the median shifted radius to the
nearest integer winding, which makes it blind to a whole winding displacement. @Bullo27 reproduced
that through the native `unwrap_targets`, bisected the acceptance edge to the tolerance, and pointed
out that `get_track_satisfied_counts` builds its target the same self referential way.

We then ran the track half against villa's own unmodified `tracks.py`. A synthetic track on winding
40 at dr 12.81, displaced and rescored, under the reporting config:

```
 displacement   satisfied   mode_winding
      0.0         24/24          40
      0.5          0/24          40     <- control, rejects
      1.0         24/24          41
      2.0         24/24          42
      5.5          0/24          46     <- control, rejects
     23.0         24/24          63
```

The half winding controls reject, so the harness can produce a rejection and the zeros mean
something. Whole winding displacements, including 23 windings, leave the count untouched.

Two details beyond the source reading. `get_track_satisfied_counts` already returns
`mode_winding_per_track`, and it tracks the displacement exactly. And
`get_track_satisfied_counts_in_chunks`, the entry point `satisfaction_metrics.py` imports, unpacks
five values and returns two, discarding the winding. The quantity a conservative check needs exists
one call below the boundary and is dropped at it.

### The annotation already exists, and is already public

`spiral_datasets/PHercParis4/abs_winding.json` ships 59 annotated points across 6 collections. Every
collection carries `metadata.winding_is_absolute: true`, and every point carries `wind_a`, an
absolute winding number, alongside its 3D position.

At `6847063ff`, `winding_is_absolute` is read by `fit_spiral.py` (10 occurrences), `losses.py`,
`spiral_helpers.py`, `fit_session.py`, `connect_overlapping_patches.py`,
`find_inconsistent_windings.py`, and one test. It is read zero times by `satisfaction_metrics.py` and
zero times by `tracks.py`.

So the fit is supervised by absolute winding, and the statistic used to police the fit is not.

### What villa already has, so that this is not overstated

`find_inconsistent_windings.py` already implements the propagation this would need: absolute anchors
vote directly, relative winding point collections act as graph edges, a backwards BFS over the patch
graph carries anchors to a seed, and within patch transport counts discrete theta zero branch
crossings. That is a complete solution to the underlying problem.

It is a standalone debug tool that does no fitting or training. So the accurate statement is not
that villa cannot detect a whole winding error. It is that the detection exists in a tool a human
runs deliberately, while the statistic wired into the metric, and named in `autoresearch.md` as the
anti gaming cross check, cannot see it.

### The narrow suggestion

Stop discarding the value that already exists. Have
`get_track_satisfied_counts_in_chunks` optionally return the mode windings it currently drops, and
let the satisfaction report compare them against the absolute anchors that are already loaded. A
patch level equivalent needs the caller to derive a winding rather than just forward one, so the
track side is the cheaper starting point.

A diff for the additive part of that change is on #1621. It is strictly additive, with the new
return gated behind a default off flag, so existing two value call sites are unaffected.

### Limits

Synthetic flat track, one geometry, displacement varied and shape held fixed. No fit was run, so
this measures what the metric does with a track placed on a winding, not how often a real fit
misplaces one. The multi winding behaviour was checked separately: the mode shifts by exactly +1
under a whole winding displacement at every drift level tested, and is ambiguous under jitter only
near a drift of one full winding, which is where the satisfied count has already collapsed. So every
fully satisfied track in that sweep had a stable mode.

We have not run the spiral fit ourselves, and cannot yet, so we have not observed an optimizer
actually exploiting this. The claim is about what the guard can and cannot see, not about an
occurrence.
