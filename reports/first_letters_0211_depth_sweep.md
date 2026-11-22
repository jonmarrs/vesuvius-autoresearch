Studio reads our geometry best at the depth the band reads already use, where PHerc. 211's prize was won, and its read falls faster outward than inward (2026-11-22)

Finding 135. Every band read gives Studio layers 41 down to 26 of the 66-layer render frame. Here Studio's 16 planes
were taken D layers further out (D > 0) or further in (D < 0) instead, for D = −8, −6, −4, −2, −1, +1, +2, +4, +6
and +8. Two geometries of PHerc. 211's windings w033 to w036 (band z 7650 to 9150) were swept: finding 121's (arm
`e2e`) and finding 134's three-pass snap of the denser grid (arm `dense2s3`). Each arm was carried onto the winner's
surface once, by finding 110's transfer, and every shift's map was scored there by finding 124's statistic. The
recipe's PHerc. 343 surface was swept the same way and scored by finding 127's statistic, described only. Nothing
was fitted, snapped, flattened or rendered: every map comes from a render already on disk. Registered before any
map of a shifted set of planes existed: `docs/preregistration/2026-11-22_studio_depth_sweep.md` (commit
`fe6336af`). Record: `reports/first_letters_0211_depth_sweep.json`, from the run's `depth_sweep.json`,
`depth_sweep_343.json`, `repeat.json` and gates. Scripts as run: `repro/first_letters/pherc0211_control/`
(`run_depth_sweep.sh`, `depth_sweep.py`).

**Verdict `DEPTH_ZERO_BEST`**, as predicted, by the registered table. The best shift summed over the two arms is
D\* = 0, and it is also each arm's own best. Every step exited 0, and arm `e2e` at D = 0 gave finding 124's r 0.8247
on finding 124's own cells. No render samples against the winner's normals (median cosines −0.9962 to −0.9992), and
each arm reaches more than half of the winner's mask cells. **So the band reads keep layers 41 to 26**, as
registered, and findings 129 and 133 will read as they were registered.

## The registered numbers

Each arm is scored on the cells that every one of its shifts reaches: 457,405 of the winner's 550,482 mask cells
for `e2e` (share 0.8309) and 458,383 for `dense2s3` (share 0.8327). These are the cells its D = 0 maps reach, so no
shift loses a cell.

| D | `e2e` r | change from D = 0 | `dense2s3` r | change from D = 0 | sum |
|---|---|---|---|---|---|
| −8 | 0.4552 | −0.3695 | 0.4644 | −0.3491 | 0.9196 |
| −6 | 0.6603 | −0.1644 | 0.6645 | −0.149 | 1.3248 |
| −4 | 0.7572 | −0.0675 | 0.7612 | −0.0523 | 1.5184 |
| −2 | 0.8069 | −0.0178 | 0.7958 | −0.0177 | 1.6027 |
| −1 | 0.8208 | −0.0039 | 0.8057 | −0.0078 | 1.6265 |
| 0 | 0.8247 | | 0.8135 | | 1.6382 |
| +1 | 0.8144 | −0.0103 | 0.8073 | −0.0062 | 1.6217 |
| +2 | 0.784 | −0.0407 | 0.7876 | −0.0259 | 1.5716 |
| +4 | 0.6522 | −0.1725 | 0.6818 | −0.1317 | 1.334 |
| +6 | 0.3815 | −0.4432 | 0.3907 | −0.4228 | 0.7722 |
| +8 | 0.1207 | −0.704 | 0.1177 | −0.6958 | 0.2384 |

| | value | rule |
|---|---|---|
| D\*, the largest sum | 0 | ties to the smaller \|D\|, then to D > 0 |
| gain, r(D\*) − r(0) | 0.0 in both arms | a shift reads better at +0.02 or more in both |

**Predictions.**
1. `DEPTH_ZERO_BEST`, moderate confidence: held.
2. Shifts of ±1 and ±2 change r by less than 0.05 in both arms: held. The largest change is −0.0407, `e2e` at +2.
3. No prediction on the half-widths.
4. At PHerc. 343 the best shift is −1, 0 or +1, low confidence: held (+1).
5. The repeat is identical: held.

## Described

**Studio's depth tolerance on our geometry.** Over ±1 layer, r stays within 0.0103 of r(0) in both arms; over ±2,
within 0.0407. Four layers costs 0.0523 to 0.0675 inward and 0.1317 to 0.1725 outward.

**Half-widths.** On each side, the smallest |D| in the sweep at which r is at most half of r(0):

| | inward | outward | r(−8) / r(0) | r(+8) / r(0) |
|---|---|---|---|---|
| `e2e` | beyond 8 | 6 | 0.55 | 0.15 |
| `dense2s3` | beyond 8 | 6 | 0.57 | 0.14 |
| PHerc. 343 (described) | beyond 8 | 8 | 0.58 | 0.45 |

**The read falls faster outward than inward, at both places.** At +6, r is 0.46 and 0.48 of r(0) at PHerc. 211 and
0.75 at PHerc. 343; at −6 it is 0.80, 0.82 and 0.86. Part of this is the window itself. The renderer puts layer i
of the 66-layer frame at i − 32.5 voxels along the render's normal, so layers 26 to 41 run from 6.5 voxels inside
the mesh to 8.5 outside it. Only at +8 does the window leave the mesh altogether. At ±6 it still holds the layers
either side of the mesh, and the asymmetry is already there. This study cannot say how much of it is where the ink
lies and how much is how Studio weighs its planes. The window centred on the mesh, D = −1, reads 0.0039 (`e2e`) and
0.0078 (`dense2s3`) below D = 0.

**Each winding:** its best shift, and its gain there over D = 0.

| winding | cells (`e2e`) | `e2e` | `dense2s3` |
|---|---|---|---|
| w033 | 164,315 | 0 | 0 |
| w034 | 95,215 | 0 | 0 |
| w035 | 133,557 | 0 | 0 |
| w036 | 64,318 | −1 (+0.0096) | −1 (+0.0027) |

Only w036, the winding with fewest cells, reads best a layer further in, by less than 0.01 in both geometries.

**At PHerc. 343** (the recipe's surface, finding 110's render, on its 551,720 cells), D = 0 gives finding 127's r
0.6238 again:

| D | −8 | −6 | −4 | −2 | −1 | 0 | +1 | +2 | +4 | +6 | +8 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r | 0.363 | 0.5392 | 0.609 | 0.6185 | 0.6237 | 0.6238 | 0.6274 | 0.623 | 0.5885 | 0.4677 | 0.2832 |

Its best shift is +1, by +0.0036, so neither place asks for a shift. At ±4 the read there keeps 0.98 and 0.94 of
r(0), against 0.79 to 0.94 at PHerc. 211. The two places differ in scroll, papyrus and surface (someone else's at
PHerc. 343, ours at PHerc. 211), so this study cannot say why.

**The floor.** Studio run again on finding 124's own w035 planes gave a map identical to finding 124's (largest
difference 0.0). As in finding 132, Studio is deterministic on this machine, so the curve's small steps are not
Studio's run-to-run noise. Whether a step of 0.004 would hold at another place is not known. The registered line is
0.02.

**Controls.** At every shift each arm's r stays above its slid control: the largest r with our map moved against
the winner's. The smallest gap is 0.1009 (`dense2s3`). In `e2e` that control lies between 0.0976 and 0.1165 from
−8 to +2 and falls to 0.0172 at +8, as r does. The reversed-plane control is the D = 0 map's: −0.0471 (`e2e`) and −0.0521
(`dense2s3`). Each shift's controls, ink overlap and r with the background in are in the record. The transfer
distances are 1.94 and 3.45 voxels (`e2e`) and 1.9 and 3.44 (`dense2s3`) at the median and 95th percentile.

## What it cost

1 h 59 min 1 s in all (registered: about 2.5 hours). GPU memory peaked at 14,487 MiB in use by all processes
(registered: up to about 15 GB). The maps take 4.1 GB on disk (registered: about 4.3 GB).

| step | wall time |
|---|---|
| check | 2 s |
| PHerc. 211, 80 maps with their planes | 5896 s |
| PHerc. 343, 10 maps with their planes | 1087 s |
| repeat | 73 s |
| compare, both places | 83 s |

A map at PHerc. 211 took about 74 s with its planes, and one at PHerc. 343 about 109 s.

## What this does to the campaign

The registered consequence: **the band reads keep layers 41 to 26.** Findings 129 (PHerc. 0813) and 133 (PHerc.
0800) are unchanged and stay held for disk. PHerc. 0826 and 0358 are not read again.

At the one place with a known text, no uniform shift of a layer or more brings our map closer to the winner's. So a
depth offset of Studio's window is not what keeps r at 0.82 there. Whether such an offset hid letters in a blank
band is a different question, and this study answers it only in part. Moving the window 2 layers, as a surface off
the ink by a uniform 2 voxels would, lost at most 0.0407 in r at PHerc. 211, about 5%. Four layers outward lost
0.13 to 0.17, and four inward 0.05 to 0.07.

## What this does not show

1. **Anything about legibility to an eye.** "Reads" means Studio's map agrees with the winner's Studio map.
2. **A sheet switch.** The neighbouring sheets are about 14 voxels away, and ±8 stays on this sheet's side of them.
3. **The eligible bands' tolerance.** Their distances are to a predicted sheet, not to a known surface, and their
   papyrus and ink differ from PHerc. 211's. The half-widths may stand beside a band's share of nodes within 2
   voxels; they do not give a probability that letters would have shown.
4. **An uneven depth error.** Every node moved by the same D. A surface off by different amounts in different
   places was not measured.
5. **Where the ink lies in depth.** The asymmetry mixes the ink's depth with how Studio weighs its 16 planes.
