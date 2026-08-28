# DRAFT, NOT POSTED. Reply to @TAUIL-Abd-Elilah on ScrollPrize/villa#1621

Needs Jon's approval before posting. House style: no em dashes, no en dashes.

---

This is the measurement we could not run, and it goes against the strongest form of what we
claimed. Taking that first.

**Our "silent acceptance" framing is not supported by your evidence.** We wrote that the metric
cannot detect a whole winding displacement, and let that carry an implication about fits being
accepted with one. In both your checkpoints the native strict metric rejected the patch anyway,
at 13.15% and 24.98% strict satisfied area. The statistic is invariant, which is what we
measured, but the surrounding computation still refused these patches. Those are different
claims and we blurred them.

**Your gauge caveat is the right one, and our probe cannot address it either.** A difference that
sits at +8, +7, +7 and +6, +6, +5 across seeds looks more like a global integer gauge offset than
a localized sheet switch. Our synthetic result cannot distinguish those two: we imposed the
displacement, so what we established is invariance of the statistic under a displacement we chose,
not the prevalence of displacements in real fits. Only the anchors can tell you which one is
happening, which is exactly the limit you name.

**The one datum that matches our claim is narrow and should stay narrow.** The seed-101 second-fit
anchor quad being native-strict-true while disagreeing by +5 is a single quad inside a patch that
still failed. Worth recording, not worth generalizing from.

One thing that may help anyone extending this. `abs_winding.json` in
`spiral_datasets/PHercParis4` ships 59 annotated points across 6 collections, every collection
flagged `winding_is_absolute` and every point carrying `wind_a`. You found one directly attached
anchor in that z window, which matches: the constraint on prevalence estimation is the anchor
supply, not the diagnostic. Sixty points spread over a scroll cannot support a prevalence claim no
matter how good the check is, so any stronger statement here needs more annotation rather than
more compute.

Your `--pcl` bug is the same shape as the thing under discussion. The diagnostic inherited
`input_use_pcl_absolute: false` and silently filtered out files given explicitly on the command
line, so it reported `0 absolute` and looked like a clean negative. That is the third instance in
this thread of a check that could not see the thing it was being used to rule out, after the
satisfaction target being derived from the scored geometry, and after our own path-scoped diff
elsewhere reading a directory move as a deletion. It seems worth stating as a pattern rather than
three coincidences.

What we think still stands, stated narrowly: the acceptance half-width is exactly the radius
tolerance in units of `dr_per_winding` under both configs, the invariance is exact rather than
approximate, and the half-winding controls reject, so the zeros are informative. Everything beyond
that about real fits is now your evidence rather than ours, and it points the other way.
