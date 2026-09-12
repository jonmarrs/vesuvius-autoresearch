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
| **BASELINE** | all 59 anchors | 3 | already fitted and scored (`curbase_s1..s3`) |
| **ABLATED** | 10 anchors | 3 | new (`anchor10_s1..s3`, seeds 1-3) |

Current villa, 30,000 steps, `z` 13056-18432, identical in every other respect. The reduced dataset
is a symlink farm (`data/spiral_s1_anchor10`) carrying a real reduced `abs_winding.json`; the patch
set is unchanged at **38,442 in both arms**, verified in the fit logs, so this manipulation is
anchors-only.

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
