# Pre-registration: <the question, as a question>

**Written <date>, before <the thing that must not exist yet>.**

> This template is the shape 44 registrations converged on, plus the checks that the week of
> 2026-09-19 to 21 paid for. Copy it; delete this note. Every section below exists because its
> absence cost something once. Do not skip the ones that feel obvious — those are the ones that did.

## The question

One paragraph. What would be different about the world if the answer were yes versus no. If you
cannot say what changes, stop here; the study is not worth its compute.

## Reachability — checked BEFORE designing the validation

**Ask whether the manipulation can occur before pre-registering how to measure it.** The sheet-switch
detector was registered, built, and validated before anyone checked its premise was reachable; it
was not. The flat-surface displacement study checked that villa's own loader accepted the displaced
tifxyz, that the shift survived the round trip to 0.000 vx, and that the point count was unchanged —
*then* registered.

State what was checked and what it showed. Numbers, not "confirmed".

## The floor — MEASURED, never inherited

**Name the floor this study is powered against, and where it was measured.** If it came from a
report, say which measurement in that report, and check that the report *measured* it rather than
attributed it. The 1.42% "pipeline determinism" floor was attributed to the nnU-Net scorer; the scorer
is 0.0032%; the flatten was the source; a whole study design was invalidated by inheriting it.

If the floor is being measured *by* this study, write every threshold below as a multiple of it
(`F`, `3F`) so the rule is fixed before the floor is.

**Quote the interval, not the point estimate.** A CV at df=5 spans a factor of ~4. Three published
floors (0.0125 → 0.0263 → 0.0536) were each retracted when the next arm landed inside the interval
that was never printed.

## Arms

| arm | what varies | what is held fixed | verified how |
|---|---|---|---|

Every arm on one pinned `VILLA_REF` **and** one `RENDER_IMAGE` — there are two pins, and `VILLA_SHA`
alone described the Python stage while the C++ sampler lived in a Docker image built from a different
commit. Every arm written by one tool: a delta-0 rebuild that differed from villa's tifs by 0.000244 vx
moved the ink count by 107 px.

**If arms differ by a re-flatten, the flatten's 3.04% (7 vx) is in your floor.** Either reuse one
flatten (`RENDER_REUSE_FLATTEN=1`) if the manipulation acts on a fixed surface, or make it
deterministic (`FLATTEN_DETERMINISTIC=1`, 9.5× flatten cost) if it does not.

## Predictions, fixed now

Numbered. Each with a magnitude or a direction, and the reasoning. **Withhold a prediction where the
reasoning does not support one** — the OUT arm of the displacement study carried none and lost 4.48%,
which was more informative than a guess would have been.

Recorded so each can be a miss. Missed magnitudes this week: 3 of 4.

## Decision rule

| outcome | conclusion |
|---|---|

Include the **failure branch** — the row where the instrument, not the hypothesis, is what the data
speak to (e.g. "F > 1.5%: the redesign failed, do not interpret single arms"). Include the row where
the *mechanism attribution behind this study* turns out wrong. The rule that cannot say "I was wrong
about why" will not.

**The analysis script implementing this table is committed before any arm scores**, with a test that
the failure branch refuses to also emit a verdict, and a test that partial samples are refused.

## What the result cannot do — computed before it arrives

The over-reading you will be tempted to make when the number lands. Compute now whether the data
could support it. "A tighter floor reopens the nulls" did not survive arithmetic: no published null
became decisive in any band.

## Limits

One dataset, one ROI, one scorer, one machine — say which. Say what the arm count is a point estimate
of and what it is not. If a per-voxel or per-unit ratio appears anywhere above, note that such ratios
failed to extrapolate three times in one day and must not be.

## Cost

Wall time, serial, with the constraint that forces serial (renders hold ~24 GB). No fits / no new
data if true — say so, it changes what the study can claim.

---

### Before launching — the checks that a banner does not satisfy

- [ ] `VILLA_REF` pinned and `VILLA_REF_EXPLICIT=1`; `preflight.sh` PASS
- [ ] every arm's `VILLA_SHA` identical (`sort -u | wc -l` → 1) and `RENDER_IMAGE` present
- [ ] input meshes hash-identical where they should be (`md5sum` on the tif *contents*, filenames
      stripped — a hash that includes paths differs between workdirs and once produced a false alarm)
- [ ] if deterministic: the shim's **own activation line** appears in the flatten subprocess's log,
      and `/proc/<pid>/environ` shows `CUBLAS_WORKSPACE_CONFIG` — the `run_render` banner is not
      evidence; it printed while the flatten ran at stock speed
- [ ] launched with `setsid nohup … & disown`; `run_in_background` gets reaped
- [ ] monitor filter includes failure signatures, not only the success line
- [ ] kill loops match on `/proc/*/comm` or exclude `$$` — `pgrep -f <string>` matched the shell
      running it six times this month

### After the result — before writing

- [ ] run the registered script; do not compute the verdict by hand first
- [ ] check the probe tracks the target (per-slice intensity had the wrong sign for the scored ink)
- [ ] if a ratio or share appears, ask whether one pair can support it (a "59%" could not: df=1 CI 3–100%)
- [ ] if the result names a mechanism, say which part is *shown* and which is *consistent with*
- [ ] any quotation of another project's doc: `grep` the source line, do not reconstruct it
