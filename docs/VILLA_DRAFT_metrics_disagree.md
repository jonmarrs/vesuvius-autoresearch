# DRAFT villa issue — not posted. Slot: 2026-09-07 (1 new issue/week).

Checks run BEFORE drafting this time, because the previous draft passed every process check and was
still false (`docs/VILLA_DRAFT_column_width_4x.md`, withdrawn):

* **both instruments are current**, compared against the code that actually produced our numbers, not
  a convenient ref: `satisfaction_metrics.py` at the fit tree `6847063f` and `get_ink_metrics.py` at
  the render tree `5479453a` are each byte-identical to villa `origin/main` today.
* **both have positive controls**: `satisfied_area` reads 0.1004 on a 100-step fit vs 0.84 converged;
  `total_fg_pixels` falls 59.5% on the same comparison. Neither is inert.
* **prior art**: no villa issue mentions the two metrics disagreeing.
* result is **registered and pre-committed**: `docs/preregistration/2026-09-02_gap_ink_second_look.md`,
  analysis code committed before the five new fits started, tested at a Pocock alpha for a second look.
* no AI-authorship markers.

Reviewer note: 340 words. #1621 was called "excessively verbose"; detail stays collapsed.

---

**Title:** spiral: `satisfied_area` and `total_fg_pixels` can move in opposite directions, so the satisfaction cross-check can pass on an ink regression

**Body:**

`autoresearch.md` prescribes optimising `total_fg_pixels` with a satisfaction cross-check. We have a
measured case where the cross-check would have passed enthusiastically on a change that cost a tenth
of the objective.

Twelve fits of `spiral_datasets/PHercParis4`, six per arm, differing only in
`optimizer_random_seed` and one config flag, all rendered and scored identically on w120-w129:

| | `satisfied_area` | `total_fg_pixels` |
|---|---:|---:|
| baseline (n=6) | 0.83897 | 1,719,984 |
| changed (n=6) | 0.84764 | 1,541,596 |
| | **+1.03%, p = 3.9e-06** | **-10.35%, p = 0.0018** |

Both sets are completely disjoint on both metrics (null probability 0.108% each). The ink result was
pre-registered and tested at alpha = 0.0294 (Pocock, second look); `overall_fg_fraction` agrees at
-10.78%, so it is not a strip-area artefact.

**The config flag itself is not the point** — it is `model_gap_expander_num_windings`, which #1625
already fixed, and our fits predate that. The point is that a change which genuinely improved the
fit's geometry cost 10% of recovered ink, and the prescribed guard reports geometry.

We are not proposing a fix. One config change on one ROI does not establish how often the two
disagree; we checked our three other config arms and every ink delta sits inside the seed-noise
floor, so they cannot answer it either. But if the guard's purpose is to catch ink regressions, a
case where it moves confidently the wrong way seems worth knowing.

<details><summary>method</summary>

`fit_spiral.py` at villa-spiral `6847063f`; `render_ink.py` + `get_ink_metrics.py` extracted at
`5479453a`; ink volume `representations/predictions/ink-3d/`. Welch two-sided on 6 vs 6;
per-arm `satisfied_area` quality gate (spreads 0.0045 and 0.0024, band 0.01) applied within arms and
never pooled across them, since the arms are expected to differ on that metric.

</details>
