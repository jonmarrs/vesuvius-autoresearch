# Pre-registration: does refitting on the spiral's own well-satisfied patches help?

**Written 2026-09-03, before any filtered dataset is built or any fit is started.**

## The question, and whose it is

villa's open-problems page, under *Spiral fit: a global prior*, names this avenue directly:

> "An interesting avenue would be identifying methods to automatically crop 'good' regions of the
> spiral fit, and using these as surface patch inputs to a subsequent run."

and states the broader goal:

> "the fastest way to unroll scrolls at scale is to develop methods for creating winding constraints
> that are precise and fast enough to use widely"

A fit already scores every input patch: `satisfied_fitted.json` gives 38,439 patches each with a
`fraction` of its area the fit could satisfy. The proposal is to use that as a quality signal —
refit on only the patches the previous fit reconciled well, on the theory that poorly-satisfied
patches carry sheet switches and misregistrations that fight the global prior.

## The confound this design exists to handle

**Dropping low-satisfaction patches also drops evidence.** At threshold 0.90 the input falls from
38,439 patches to 26,728 (69.5%), and from 100% of patch area to 76.4%. A fit given less evidence
may change for that reason alone, in either direction. A two-arm design (baseline vs filtered) cannot
separate "better evidence" from "less evidence" and would be uninterpretable.

**So there is a random control**, and the comparison that carries the claim is
**BOOTSTRAP vs RANDOM**, not BOOTSTRAP vs BASELINE.

*Amendment, made before any fit was started: the control is matched on total patch AREA, not on
patch count.* A count-matched control was built first and left the arms at 76.4% vs 70.0% of area,
so part of any difference would have been quantity rather than quality — the exact confound the
control exists to remove. The losses integrate over surface area; patch count is an artefact of how
traces were split. Area-matched, RANDOM holds 30,071 patches to BOOTSTRAP's 26,728, both at 76.4% of
total area.

## Arms

| arm | patches | n seeds | status |
|---|---|---:|---|
| **BASELINE** | all 38,439 | 6 | **already fitted and scored** (baseline01, seed02-06) |
| **BOOTSTRAP** | `fraction >= 0.90` from `baseline01`, 26,728 | 3 | new |
| **RANDOM** | random patches drawn to the same total AREA (30,071 patches, 76.4% of area) | 3 | new |

Six new fits. Seeds 1, 2, 3 in each new arm. The selection is taken from **`baseline01` only** — one
fixed reference fit — so both new arms see an identical patch set across their seeds, and the
selection is not itself reseeded.

Threshold **0.90 fixed now**, chosen from the *input* distribution (median per-patch fraction is
0.9940; p25 is 0.7557) and not from any outcome. No other threshold will be tried; sweeping one is
how a null becomes a finding.

Dataset built as a symlink farm — `verified_patches/` containing only the selected directories,
every other dataset entry symlinked — so the 51 GB source is untouched and both arms differ from
BASELINE in exactly one respect.

## Primary and secondary, and why both are primary-ish

`reports/gap_fix_costs_ink_established.md` established that a change can raise `satisfied_area` by
7-10 sd while costing 10.35% of `total_fg_pixels`. **A bootstrap that selects patches by satisfaction
is at obvious risk of exactly that failure**: self-confirming geometry that reads less text. Scoring
only geometry would report a win.

* **Capability endpoint: `total_fg_pixels`** on w120-w129, Welch two-sided, alpha = 0.05,
  BOOTSTRAP vs RANDOM.
* **Geometry endpoint: `satisfied_area_fraction`**, same test.

**A geometry gain accompanied by an ink loss is recorded as a FAILURE of the method**, not a partial
success, and is reported as a second instance of the opposition.

## Power, computed now

At the measured outer CV of 0.0421 and 3 vs 3, SE on the relative ink difference is
`0.0421 * sqrt(1/3 + 1/3)` = **3.4%**, so 80% power at alpha 0.05 needs about **9.6%**. This arm sees
effects of roughly a tenth and no smaller; a null must be reported as "no effect larger than ~10%",
never "no effect". `satisfied_area` has CV 0.00167 and needs no such caveat.

## Decision rule

| outcome (BOOTSTRAP vs RANDOM) | conclusion |
|---|---|
| ink up, p < 0.05 | The method works. Selecting on the fit's own satisfaction produces better winding constraints — a direct answer to villa's named avenue. |
| ink down, p < 0.05 | The method actively harms recovery. Reported as such. |
| ink null, geometry up p < 0.05 | **FAILURE, not partial success.** The gap133 pattern repeats: geometry improves while text does not follow. |
| both null | No effect larger than ~10% on ink. The avenue is not promising at this threshold on this ROI, and the question closes at this budget. |

BOOTSTRAP vs BASELINE and RANDOM vs BASELINE are reported for context and **carry no claim**: they
confound quality with quantity, which is the whole reason RANDOM exists.

## Prediction, fixed now

**I predict ink is null and geometry rises** — i.e. the third row, a failure. Reasoning: satisfaction
is the fit's own residual, so refitting on what it already satisfied is close to circular, and the
gap133 result showed this metric pair coming apart under exactly that kind of pressure. Recorded so
it can be a miss; I have been wrong on three of five registered predictions.

## Cost

Six fits at ~1.75h, six renders at ~2.2h, six scorings at ~0.25h: **about 25 hours, sequential**.
Renders under `run_with_retry.sh`; fits pinned to villa-spiral working tree `6847063f` so the new
arms stay comparable with the existing six baselines (current villa defaults to 2 flow stages after
#1693 and would not be).
