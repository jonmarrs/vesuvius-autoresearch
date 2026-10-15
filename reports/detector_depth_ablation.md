# The detector reads ink mostly from its deepest slices, which the loop's shallower windows leave out (finding 89)

**2026-10-13.** A read-only measurement, **pre-registered**: its reading rule was committed (`f9d892b0`) before it
ran. CPU, one thread, lowest priority, beside the running loop. Script `scripts/detector_depth_ablation.py`, run at
`f9d892b0`; output `reports/detector_depth_ablation.json`.

**Question.** Finding 87 left one depth difference untested: the TimeSformer detector
(`models/detector/detector_epoch=7.ckpt`) reads 26 slices, zarr 1–26 (layers 17–42), and the loop's model reads
16. With `depth_band` [1, 27], `num_layers` 16 and a 4-slice margin, the loop reads 24 slices starting at zarr 0–7
and keeps the middle 16. In the detector's channel numbering (channel c is zarr slice c+1), that window starts at
channel **3** at the lowest and **10** at the highest. Does the detector use slices outside such a window?

**Method.** Control B's **400** random windows of Fr143 (seed 0; the draw and the full-depth scores reproduce B, or
the script aborts), **1,638,400** pixels, ink prevalence **0.1545**. The detector is scored with all 26 channels,
then with only 16 kept, at the loop's offsets 3, 7 and 10. The other 10 channels are filled from the kept 16:
mirrored about its ends (reflect, the primary fill) or its end slices repeated (edge, a sensitivity check).

## Result

| channels kept | zarr slices | AUC, reflect fill | AUC drop | AUC drop, edge fill | AP lift, reflect fill |
|---|---|---:|---:|---:|---:|
| all 26 | 1–26 | 0.7034 | 0 | 0 | 1.8831 |
| 3–18 (the loop's lowest window) | 4–19 | 0.6278 | **0.0756** | 0.0959 | 1.5176 |
| 7–22 (a middle window) | 8–23 | 0.6653 | **0.0381** | 0.0295 | 1.5797 |
| 10–25 (the loop's highest window) | 11–26 | 0.6826 | **0.0208** | 0.0129 | 1.6895 |

The rule: every reflect drop ≤ 0.02 would mean the detector does not need the slices outside the loop's window;
every drop ≥ 0.05 would make the 26-vs-16 difference a candidate cause at every offset. The drops are 0.0756,
0.0381 and 0.0208, so by the pre-registered rule **it depends on the window's position.**

The position effect is not an artefact of how much was removed. The window at 10 replaces ten channels (0–9) and
loses 0.0208. The window at 3 replaces ten as well (0–2 and 19–25) and loses 0.0756, 3.6 times as much. The
difference is channels 19–25 (zarr 20–26, layers 36–42). Both fills give the same ordering.

## What this means

* **For this detector, the 26-vs-16 difference matters through which 16 slices are kept.** A 16-slice window at
  the deep end keeps nearly all of its AUC; one at the shallow end loses 0.0756 of its 0.2034 above chance. The
  slices it leans on are zarr 20–26. A loop read that starts at zarr z0 keeps z0 of those seven: none at the
  shallowest start, all seven at the deepest.
* **The loop's windows span exactly this range.** The loader draws each patch's read start uniformly from zarr 0–7
  (`RandomState.randint`; fixed per patch by seed 42 in validation, by each cycle's sampling seed in training), so
  its windows run from the shallow end to the deep end.
* **A lever this suggests, untested:** pin the loop's window to the deep end. `depth_band` [11, 27] leaves the 24-slice
  read one start (zarr 7), so every window would be zarr 11–26. The band is part of the validation protocol, so this
  is the owner's decision, and it is a separate change from adopting the ink-free patches (finding 88). It would need
  a re-score and a loop test.

## Caveats

* A fill is input the detector never saw in training, so every drop overstates the information lost. The strong
  result is the asymmetry between equal-sized removals, not the size of any one drop.
* This shows what this detector uses, not what a model trained on 16 slices can learn. The loop's model might draw
  ink from shallower slices that the detector ignores.
* One fragment (Fr143), one detector checkpoint, one draw of 400 windows. Pixels within a window are not
  independent; no significance is claimed.
* The detector's epoch was chosen by AUC on Fr143, so its full-depth numbers lean optimistic (as in finding 88).
* The run (20:53–21:16) overlapped one loop cycle, which ended at 21:17 at 0.51 Mvps against 0.28–0.30 for the rest
  of the night. That cycle's tweak changed its speed, so this job's cost to the loop can't be read from it.
