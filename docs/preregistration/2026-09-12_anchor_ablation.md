# Pre-registration: how many absolute winding anchors does READING need?

**Written 2026-09-12, before the pilot gate was read and before any arm existed.** Analysis code
`scripts/analyse_anchor_ablation.py` and its tests were committed in the same state of ignorance.

**This study runs only if `docs/preregistration/2026-09-12_anchor_ablation_gate.md` returns PROCEED.**
If the gate fails, this registration is retired unrun and reported as retired.

## The question, and whose it is

villa's `39_winding_annotations.md` says relative winding annotations "seem to have a great impact on
the spiral fit" and asks for automation. The open-problems page names the bottleneck: "the fastest way
to unroll scrolls at scale is to develop methods for creating winding constraints that are precise
and fast enough to use widely."

**Every winding-constraint project in villa's catalogue validates on geometry** — winding-sync,
winding-ruler, spiralcheck, FASP, axiosdevs' annotator. None measures the constraints against
recovered ink. That is the gap this fills, and it is worth filling because we have four
pre-registered cases on the superseded tree where geometry and ink moved independently.

The companion result is already in hand: removing **5,413 same-winding (relative)** constraints
changes reading by **+0.28%, 95% CI [−2.56%, +3.13%]**. This asks the same question of the **59
absolute anchors**, which are far fewer, higher-leverage, and the ones villa asks humans to draw.

## Arms

| arm | `abs_winding.json` | n | status |
|---|---|---:|---|
| **BASELINE** | all 59 anchors (**50 inside the fit's z-ROI**) | 3 | already fitted and scored (`curbase_s1..s3`) |
| **ABLATED** | 10 anchors, **z-coverage matched** | 3 | new (`anchor10cov_s1..s3`, seeds 1-3) |

### Amendment, 2026-09-12, before any arm was started

Inspecting the anchor coordinates — which this registration should have done before quoting a number
— found two things wrong with the paragraph above as first written:

1. **Nine of the 59 anchors lie outside the fit's z-ROI** (z 8459 and 10673, against a ROI of
   13056-18432) and are never used. The manipulation is **50 → 10**, not 59 → 10.
2. **The hand-built `data/spiral_s1_anchor10` keeps all ten anchors on a single z-plane.** Of the 50
   in-ROI anchors, 48 already sit at z=15694 and the other two planes hold exactly one each, so
   "keep the first 10" drops **both** lone anchors. That cuts 80% of the count **and 100% of the
   longitudinal spread at once**, and no result could separate the two.

The arms therefore use **`data/spiral_s1_anchor10cov`**, built by
`scripts/build_anchor_subset.py --keep 10 --strategy coverage --z-roi 13056 18432`: 1 anchor at
z=14268, 8 at z=15694, 1 at z=15976. **Every populated z-plane is still represented**, so the
manipulation is count at matched coverage — which is the question villa asks.

That script also carries a `crowded` strategy that reproduces the hand-built set **exactly**
(positive-controlled in `tests/test_build_anchor_subset.py`), so the old artifact stays explainable
rather than merely discarded.

**The gate pilot ran on the OLD, z-collapsed dataset.** That is the more disruptive configuration, so
passing it is the conservative direction: if numbering survives losing all longitudinal spread, it
survives keeping it. This is disclosed rather than re-run, and it changes nothing about the
per-arm gate — **every ablated arm is still checked individually**, so a numbering failure in the
actual arms is caught regardless of what the pilot showed.

Current villa, 30,000 steps, `z` 13056-18432, identical in every other respect. The reduced dataset
is a symlink farm carrying a real reduced `abs_winding.json`.

**Verified in the fit logs that the manipulation is anchors-only**, by comparing the pilot against
`fit_curbase_s1.log`:

| collection | baseline | ablated |
|---|---:|---:|
| absolute winding (`abs_winding.json`) | 59 points | **10 points** |
| relative winding | 2,173 | 2,173 |
| same-winding | 5,413 | 5,413 |
| patches after filtering | 38,442 | 38,442 |

Only the anchors differ. Everything the fit otherwise consumes is identical.

**Anchor count is fixed at 10 and will not be swept.** Trying counts until one gives a publishable
answer is the failure mode this sentence exists to prevent.

## Endpoints

* **Primary: `total_fg_pixels`** on w120-w129, ABLATED vs BASELINE, Welch two-sided, alpha = 0.05.
* **Secondary: `satisfied_area_fraction`**, same test, **and here it is interpretable.**

That second point is a deliberate difference from the same-winding study, which had to make
satisfaction report-only because the manipulation removed 5,413 of the patches the metric scores, so
a rise could mean "less left to satisfy". **This manipulation touches `abs_winding.json` only and
leaves the patch set identical**, so satisfaction is like-for-like and is allowed to carry weight.

It still does not decide. A geometry move with a null ink result does **not** license "thinning
anchors is harmless for reading", and `verdict()` takes ink as the deciding input with a test pinning
that.

## Power, computed now

At the **current tier's** measured seed CV of **0.0125** (`reports/noise_floor_by_tier.md`, pooled
within-arm, df=4), 3 vs 3 reaches **2.9%** at 80% power. The four earlier studies inherited the
pinned tree's 0.0421 and would have quoted 9.6% here, overstating the floor by 3×.

A null must be reported as "no effect larger than about 3%", and **post-hoc the confidence interval
on the observed effect is quoted instead of this MDE**, which is the correction that came out of
`reports/decoupling_does_not_cleanly_reproduce.md`.

## Decision rule

| outcome (ABLATED vs BASELINE) | conclusion |
|---|---|
| ink **down**, p < 0.05 | **Anchors matter for reading.** The hand annotations villa asks for buy ink, and this quantifies how much 49 of them are worth. |
| ink **up**, p < 0.05 | **Fewer anchors read better.** Surprising; first check whether the retained 10 are better *placed*, not whether fewer is better in itself. |
| ink null | **No reading effect larger than ~3%.** If it holds, the annotation effort is buying geometry rather than reading — worth knowing before automating the production of more. |

Geometry is reported alongside in every branch and never upgrades the verdict.

## Arm-level gate, and what happens to a failure

**Every ablated arm is checked with `scripts/measure_winding_identity.py` against `curbase_s1`.** An
arm whose winding numbering shifted is comparing different papyrus; it is **EXCLUDED and reported as
excluded** via `--excluded`, which prints it. It is never silently dropped and never used to reselect
the anchor count. If exclusions leave fewer than 3 ablated arms the analysis **refuses to run** — a
partial sample is not reported.

## Prediction

**None, on either endpoint.** This is deliberate and is a change of practice.

My last two registered predictions of `satisfied_area`'s direction were both wrong, pointing opposite
ways — a rise predicted from a smoke fit that fell, then a fall predicted from that result which rose.
Two misses with opposite signs is not bad luck; it is evidence of no working model of this metric. On
ink I have no basis either: the relative-constraint ablation was null, which is weak evidence about a
different constraint class.

Registering "no prediction" costs the ability to score myself and buys not having to discount a guess
that would otherwise shape how the result is read.

## Cost

Three fits at ~2h, three renders at ~2.2h, three scorings at ~0.25h: **about 14 hours, sequential**,
reusing the six baseline arms already scored.
