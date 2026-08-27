# An external check on the PHerc 1667 column registration

**Exploratory, not pre-registered.** I computed these numbers to see whether they were plausible,
found that they were, and am reporting them with that provenance attached. The strength here comes
from the size of the agreement, not from a threshold I set in advance — and the distinction matters
because I could have set a threshold afterwards to fit the answer.

## Why the existing evidence was not enough

`reports/detector/merged1667_column_registration.md` supports the registration with four checks:
all three figure strips independently recover the same scale (4.7 grid px per figure px) and the
same `dy` of 19; the strips tile left-to-right with the last edge landing within **3 px over
30,097**; match scores are 0.49 / 0.67 / 0.67; and bracket extraction yields exactly 22 columns.

Those are good, and they are all **internal**. Every one is a property of the same template-matching
procedure. If that procedure were systematically wrong — a mis-set scale, a shifted origin — three
strips fitted the same way could agree with each other and with the tiling closure while all being
wrong together. This project has already had one "everything reads at chance" headline reverse
because a registration was wrong in a way its own internal checks could not see.

The check that would have been natural — *"the traces columns sit on the fragmentary region and the
gutters land in the wrap-damage notches"* — is **circular**, and I nearly ran it before noticing.
The registration was fitted *by template matching onto the valid mask*, so correspondence with the
mask is a consequence of the fit, not evidence for it.

## The independent handle

The volume is `20251217075048-2.399um-...`, so **1 volume voxel = 2.399 µm**, and the grid is that
volume at `scale 0.05`, so **1 grid px = 20 × 2.399 = 47.98 µm**. That converts the registration
into physical units using only the scan's own voxel size — a quantity that never entered the fit.

| quantity | from the registration | plausible for a Herculaneum roll? |
|---|---|---|
| column width | median **52.8 mm** (40.6–60.0) | yes, typical columns run 4–7 cm |
| intercolumnium | median **9.7 mm** (6.8–15.8) | yes, typically ~1 cm |
| column + gap pitch | **62.5 mm** | consistent with the two above |
| line pitch | **5.76 mm** (120 grid px) | plausible for this hand |
| segment length | **1.44 m** | plausible for 22 columns |
| grid height | **98.9 mm** | consistent with *"preserves the lower parts of the final columns"* |

Plausible is not decisive. The decisive one is area.

## The area check

The published reading reports **twenty-two columns or column-equivalents over approximately
860 cm² of preserved writing surface**. That figure is external to everything we did: it comes from
the papyrological reading, not from the strips, and no part of our fit was tuned toward it.

Summing the target's own valid mask inside the 22 registered column boxes, at 47.98 µm per grid px:

```
valid mask, whole grid             1078 cm²
valid mask, inside the 22 columns    867 cm²      published: ~860 cm²   → 1.01x
```

**Within 1%.**

That is a tight constraint rather than a loose sanity check, because **area is quadratic in the
scale**:

| scale error | implied area | ratio to 860 |
|---|---|---|
| −20% | 555 cm² | 0.64× |
| −10% | 702 cm² | 0.82× |
| −5% | 782 cm² | 0.91× |
| **0%** | **867 cm²** | **1.01×** |
| +5% | 955 cm² | 1.11× |
| +10% | 1049 cm² | 1.22× |
| +20% | 1248 cm² | 1.45× |

The area can only land within 1% of the published figure if the scale is right to within about 5%.
And the area depends on the column *placement* as well as the scale — it is the valid mask summed
*inside the boxes* — so a registration that was correctly scaled but shifted would select a
different region and would not be expected to land here either.

## What this does and does not establish

**Establishes:** the registration's scale and gross placement are corroborated by a published
measurement that is independent of the fitting procedure, to within a few percent. The 22-column
count matches exactly. The physical dimensions it implies are ordinary for a Herculaneum roll.

**Does not establish:** per-column boundary accuracy. An area agreement to 1% is compatible with
individual column edges being off by tens of grid pixels in compensating directions, and the
registration report already flags cols 9 and 16 as spanning strip-crop gaps with bbox edges ±250
grid px. This audit is about the global transform, not the local boxes.

**Does not touch:** the metric's power, which is a separate question answered separately in
`reports/column_metric_power.txt` — the metric detects a column-concentrated signal at 0.25× the
background noise.

Taken together, those two say the column family's near-chance results are neither a broken scorer
nor a grossly broken registration. They are a statement about our detectors on this scroll.

## Sources

- [Complete virtual unwrapping and reading of a rolled Herculaneum papyrus](https://arxiv.org/abs/2606.29085)
  — the reading this target's ground truth derives from.
- [An entire Herculaneum scroll has been read for the first time, Vesuvius Challenge](https://scrollprize.org/firstscroll)
  — the announcement, which states the 22 columns and the ~860 cm² of preserved writing surface.
