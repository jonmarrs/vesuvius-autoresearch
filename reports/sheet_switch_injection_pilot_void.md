# Injection pilot: VOID. The injection does not manufacture a sheet switch

**2026-08-29.** One seed, five arms, 200 injections per arm, against the frozen detector
(`scripts/detect_sheet_switches.py`) and the pre-registered injection
(`scripts/inject_sheet_switches.py`, committed before it ran).

## The pilot result, which is not a detector verdict

```
k=0.0   injected   0   recall  0.0%   flags elsewhere 1773
k=0.5   injected 200   recall  0.0%   flags elsewhere 1773
k=1.0   injected 200   recall  1.0%   flags elsewhere 1773
k=1.5   injected 200   recall  3.0%   flags elsewhere 1773
k=2.0   injected 200   recall  5.5%   flags elsewhere 1773
```

The `k = 0` null control **passes**: injecting nothing leaves the flag set at exactly the baseline
1,773. Recall is near zero everywhere else, where a half-patch displaced by a full winding should be
caught almost always.

## Why this is void rather than negative

Recall near zero has two explanations, and they demand opposite responses: the detector cannot see
planted switches, or the injection never plants one. A diagnostic separates them.

```
sanity: max |zyx| change on an injected patch at k=1:  16.087   (dr = 16.173)

                     satisfied quads (median)   mean #windings   mean minority fraction
baseline                            293              0.950                0.0000
injected k=1.0                      126              1.017                0.0001
injected k=2.0                       90              1.167                0.0299
```

**The displacement is applied**, by almost exactly `dr`, so this is not a silent no-op in the
dataclass reconstruction. But injected patches **lose more than half their satisfied quads** while
their winding count barely moves.

The displaced half becomes **unsatisfied**, not satisfied on a neighbouring winding. Since the
detector counts windings only among satisfied quads, the injected region drops out of the statistic
entirely instead of reading as a second winding.

**So the injection does not model a sheet switch.** A real switch is geometry that plausibly fits the
*wrong* wrap: it satisfies the metric, on the wrong winding. This injection produces geometry that
fits *nothing*.

## The likely mechanism, stated as a hypothesis

The displacement is radial about the umbilicus in **scan space**, but the scan-to-spiral mapping is a
learned deformation. A rigid radial shift in scan coordinates is therefore not a clean winding shift
in spiral space, and the displaced quads land off-spiral: outside the radius tolerance, outside the
scan-distance tolerance, or both. This is untested; it is the next thing to check, not a conclusion.

## What must change, and what must not

**The injection changes. The detector does not.** The detector was frozen on 2026-08-29 before any
of this and stays frozen; its 5.02%-against-a-5%-bar standing is unaffected by a void pilot.

The redesign is to displace in **spiral space** and map back through `transform.inv()`, so the
injected region lands on winding `w + k` and can satisfy the metric there. That is the condition the
detector was built to see, and the condition the pilot failed to create.

**On the propriety of changing it after a bad result:** the justification is mechanical and
evidenced, not outcome-driven. The diagnostic shows the injection fails to produce the intended
condition, measured by satisfied-quad collapse and a flat winding count, and that evidence would
read the same way whatever the recall had been. The pre-registration's arms
(`k in {0, 0.5, 1, 1.5, 2}`), the contiguous-half construction, the clean-patch eligibility rule and
the decision rule are all unchanged.

## Cost, honestly

This is a real setback. The injection study is the only handle on recall, the gate is 2026-09-15, and
the harness that was supposed to deliver it needs rebuilding in a coordinate space I have not yet
worked in. Seventeen days remain. The pilot cost about ten minutes of compute and found the flaw
before three seeds were spent on it, which is the argument for running pilots.

---

## Second attempt, 2026-08-30: the spiral-space injection is ALSO invalid

Rebuilt to displace in spiral space and map back through `transform.inv()`, on the reasoning that a
rigid radial shift in scan coordinates is not a winding shift. It ran to completion:

```
transform device: cuda:0
k=0.0   injected   0   recall  0.0%   flags elsewhere 1773
k=0.5   injected 200   recall  0.5%
k=1.0   injected 200   recall  1.0%
k=1.5   injected 200   recall  1.0%
k=2.0   injected 200   recall  1.0%
```

Recall flat at ~1%, which is 2 patches in 200, i.e. noise. Flatness *across magnitudes* is the tell:
if geometry were landing on neighbouring wraps, integer windings should behave differently from half
windings. The diagnostic confirms it:

```
sanity: max |zyx| change at k=1: 90.948  (dr = 16.173)   <- 5.6x too large

                    satisfied quads (median)   mean #windings   mean minority fraction
baseline                           293              0.950              0.0000
injected k=1.0                     141              1.000              0.0000
injected k=2.0                      82              0.950              0.0000
```

Displacing by one winding should move a point about `dr` = 16 voxels. It moved **91**. Satisfied
quads collapse as before, the winding count stays flat, and the minority fraction is exactly zero.

**The cause is mine and specific.** I took `th = atan2(spiral_y, spiral_x)`, which is the *wrapped*
angle in `(-pi, pi]`. The spiral's radius depends on the *unwrapped* angle, which accumulates across
windings, so reconstructing a point from a wrapped theta lands it somewhere else entirely. The
metric's own target build uses `theta_all`, an unwrapped quantity it maintains, not an `atan2`.

## The sanity check said OK, and should not have

```
'OK' if moved > 0.5 * dr else 'NO-OP, everything below is meaningless'
```

It was written to catch a silent no-op, which was the previous failure, and so it could not see an
overshoot. It printed **OK** on a 5.6x error.

That is the same defect this project keeps recording: a check that cannot see the thing it is being
used to rule out. It is now the second time in this specific work, after the pre-registered `L`
sweep that could not see that boundary length was the wrong statistic. The check should assert a
*band* around `dr`, not a floor.

## Where this leaves the September bet

**Recall remains unmeasured after three attempts**, and the honest reading is that I do not yet
understand the spiral coordinate system well enough to construct a valid injection. Two designs have
failed for two different reasons, and each cost roughly half an hour of build plus a four-minute run.

What has NOT changed: the detector is frozen and untouched, the seed-agreement result stands, and
the baseline characterisation stands. Every failure so far is in the validation harness.

The gate is 2026-09-15. Rule 2 commits us to filing nothing if the detector cannot be shown to beat
its floors, and a detector whose recall cannot be measured cannot be shown to beat anything. That
outcome is now more likely than not, and saying so is cheaper than discovering it on the 15th.

The next attempt, if there is one, must use the metric's own unwrapped theta rather than
reconstructing an angle, and must assert the displacement lands within a band around `dr` before any
arm is scored.
