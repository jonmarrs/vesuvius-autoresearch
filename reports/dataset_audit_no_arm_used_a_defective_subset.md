# Dataset audit: no scored arm used a defective subset

**2026-09-18.** A validity audit of past work, not a finding. Prompted by the config-override check,
which asked a general question — *could any study here have silently measured nothing?* — and answered
one axis of it. This answers another.

## What was checked

Every study dataset on disk, against the counts its pre-registration specified and against the known
failure mode in this project's history: a hand-built anchor subset that was wrong two ways at once.

**Patch counts match the registrations exactly:**

| dataset | patches | registration says |
|---|---:|---|
| `spiral_s1` (baseline) | 38,616 | full set |
| `spiral_s1_boot090` | **26,728** | "26,728 (69.5%)" ✓ |
| `spiral_s1_rand090` | **30,071** | "30,071 patches, 76.4% of area" ✓ |
| `spiral_s1_stripmatch` | 29,661 | area-matched to BOOTSTRAP's in-strip share |
| `spiral_s1_anchor*` | 38,616 | anchor studies vary anchors, not patches ✓ |

## The anchor subsets, where the known defect lives

Parsing the point collections (`abs_winding.json`):

| dataset | points | in z-ROI | **distinct z** | |
|---|---:|---:|---:|---|
| baseline | 59 | 50 | 5 | matches the documented "50 in-ROI anchors" |
| **`anchor10cov`** | 10 | 10 | **3** | the rebuilt one |
| `anchor10` | 10 | 10 | **1** | the known-broken one |
| `anchor20` | 20 | 20 | **1** | **same defect** |
| `anchor35` | 35 | 35 | **1** | **same defect** |

`anchor20` and `anchor35` carry the same single-z-plane collapse that got `anchor10` discarded — all
their anchors sit at z = 15694. That was not previously recorded.

## It does not matter, and here is why

**No scored arm used any of them.** The three published anchor arms —
`anchor10cov_pilot`, `_s2`, `_s3` — all point at `spiral_s1_anchor10cov`, the rebuilt subset with
anchors spread across three z-planes. `anchor10`, `anchor20` and `anchor35` appear only in
`fit_smoke_*` scripts, and no `outer_anchor10/20/35` directory exists, so none was ever rendered or
scored.

So `reports/anchor_ablation_verdict.md` rests on the correct dataset, and the fix that produced
`build_anchor_subset.py` did its job.

**`anchor10cov`'s three z-planes span 14268–15976**, inside a 13056–18432 ROI. That looks concentrated
until compared against the baseline, whose own in-ROI anchors reach only to 15976 — the subset samples
where anchors actually exist, which is what the coverage strategy is supposed to do.

## The live hazard this leaves

**Three defective datasets are still on disk with inviting names.** A future session reaching for
`spiral_s1_anchor20` would get 20 anchors stacked on one z-plane and a confounded study, with nothing
in the directory to warn it. They are smoke-test leftovers from before `build_anchor_subset.py`
existed.

They are small, and deleting other people's data is not mine to decide — but they should either be
removed or renamed to make their status obvious. Recorded here so the next reader finds this before
the datasets.
