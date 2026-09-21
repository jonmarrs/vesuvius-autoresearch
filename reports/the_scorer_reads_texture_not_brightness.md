# The inward loss is not a brightness loss: IN renders BRIGHTER than ZERO and scores 20% less ink

**2026-09-20.** Follow-up to `reports/displacing_the_surface_costs_ink_in_both_directions.md`, which
named two readings for the inward/outward asymmetry and distinguished neither. No new renders: the
renderer writes its five depth slices to disk before max-compositing, so the depth structure was
already on disk. `scripts/analyse_slice_profiles.py`,
`reports/flat_displacement_slice_profiles.json`.

## The question, and the frame that turned out to be wrong

Both readings — "asymmetric ink layer" and "off-centre scorer window" — assumed the scorer responds
to how much ink-intensity the surface samples. I set out to test which by looking at the per-slice
profiles. The profiles are informative, but the assumption behind both readings failed first.

## What the composite shows

The scorer sees a max-composite of five slices. Per arm:

| arm | composite pixels > 128 | scored `total_fg_pixels` |
|---|---:|---:|
| **IN** (−4 vx) | **1.783%** — the brightest | **1,363,076** — the lowest |
| ZERO | 1.751% | 1,698,914 |
| OUT (+4 vx) | 1.435% — the dimmest | 1,622,775 |

**IN has more bright pixels than ZERO and scores 20% less ink.** A brightness reading of the inward
loss is not merely incomplete; it has the wrong sign.

The nnU-Net scorer is reading **texture and shape**, not intensity. Whatever a 4 vx inward shift does
to the rendered strip, it makes the image *brighter* and *less letter-like* at the same time. Every
intensity summary — mean, bright fraction, per-slice profile — is the wrong probe for its behaviour,
and I built three of them before checking whether the probe tracked the target.

**OUT is different in kind.** Its composite is 18% dimmer and its ink loss (4.48%) is consistent with
that. So the asymmetry is not one mechanism with two magnitudes; it is two mechanisms.

## What the per-slice profiles do show

Slices sit at (k−2) × `--slice-step 1` along the normal, at render scale 0.25 — roughly ±2 render
voxels around the surface.

| arm | slice 0 | 1 | 2 | 3 | 4 | slope |
|---|---:|---:|---:|---:|---:|---:|
| IN | 8.151 | 8.207 | 8.262 | 8.314 | 8.362 | **+0.053** |
| ZERO | 8.385 | 8.336 | 8.280 | 8.218 | 8.154 | **−0.058** |
| OUT | 7.714 | 7.700 | 7.690 | 7.686 | 7.685 | −0.007 |

* **ZERO is a monotone gradient, not a peak.** The five slices do not bracket the ink layer; they
  sample one edge of it. The "window centred or not" question was ill-posed — there is no peak to
  be centred on.
* **IN reverses the gradient**, and IN's slice 4 (8.362) matches ZERO's slice 0 (8.385): a 4 vx
  inward shift puts the surface on the far side of the layer. That is a real geometric fact, and it
  is *consistent* with the brightness being equal — which is exactly why brightness cannot explain
  the 20%.
* **OUT is nearly flat and uniformly lower**: not a translation of ZERO's profile at all.

## What this changes

**The mechanism of the inward loss is now more specific and less explained.** It is not "the surface
left the ink". The surface sampled *at least as much* bright material. What changed is something the
scorer recognises as text and the intensity does not capture — plausibly the coherence of strokes
across the strip, which a depth shift would smear or double if the sheet is not locally parallel to
the flattened surface. That is a hypothesis, stated as one.

**For villa's objective**, the implication sharpens: `total_fg_pixels` is not a proxy for "how much
ink did the surface pass through". It is a proxy for "how much of what the surface passed through
looks like writing to this model", and those diverge by 20% under a quarter-winding shift with the
brightness going the *other way*.

## The error caught on the way

The first draft of this report was written around the per-slice profiles and would have concluded
that IN's loss is the window sliding off the layer. I checked whether composite brightness tracked
scored ink only because the per-slice means for IN and ZERO were within 3% while the ink differed
by 20%, and a max of near-equal layers cannot lose 20%. **The probe must be validated against the
target before its output is interpreted** — the same lesson as the column-metric line, learned again
on a different instrument.

## Limits

One arm per condition, one magnitude, one region, one scorer. "Texture and shape" is what is left
when intensity is excluded, not something measured here; a positive test would perturb texture at
constant brightness. The slice geometry rests on the renderer's defaults (`--slice-step 1`) as read
from its `--help`, not from a measurement of where the slices land.
