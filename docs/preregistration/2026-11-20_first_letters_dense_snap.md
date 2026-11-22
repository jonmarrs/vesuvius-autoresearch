# Pre-registration: does snapping a twice-denser winding grid keep more of the rendered surface on the predicted sheet?

**Written 2026-11-20, before any winding has been densified, snapped or flattened this way.** Finding 130.

## The question

Studio reads 16 layers centred on the rendered surface, so it sees the papyrus only where that surface lies on the
sheet. The rendered surface is the flatten's output, and it lies on the snapped winding's triangles: on PHerc. 0826's
read, a median 97% of each final winding's nodes are within 2 voxels of them (`band_geometry.py`, after finding
125).

The snap moves each of the fit's nodes onto the predicted sheet. The fit's grid is even in angle, so at large radius
its nodes are far apart. On 0826's crushed band they are about 60 voxels apart at the tips, and there a flat triangle
between two nodes that are on the sheet can leave a curved sheet.

**If the grid is subdivided before the snap, so that the new nodes are snapped too, does more of the rendered surface
lie on the predicted sheet?** If so, later band reads should snap a denser grid.

## Reachability, checked before this was written

Medians over 0826's 70 read windings, against the surface prediction's signed distance field:

| | within 2 voxels of the predicted sheet |
|---|---|
| the snapped nodes | 0.774 |
| the rendered surface | 0.668 |
| the rendered surface, inner third of radii | 0.787 |
| the rendered surface, middle third of radii | 0.661 |
| the rendered surface, outer third of radii | 0.541 |
| PHerc. 211's read windings w033 and w035, rendered | 0.90 and 0.91 |

So the rendered surface loses about 0.11 against the snapped nodes, and the loss grows with radius.

- **The tools take any grid.** The recipe's `snap_meshes.py` snaps every node of a tifxyz grid, and the band's
  `run_snap.sh` and `run_flatten.sh` run on any arm whose raw windings sit under `R/work/fit_ARM/*/meshes/<folder>`.
- **The cost does not change downstream.** The flatten writes its output at a fixed 20 voxels a node, so the render
  costs the same; only the snap and the flatten see four times the nodes.

## Arms

| arm | work dirs | what varies | held fixed |
|---|---|---|---|
| `outer80` | finding 125's `snap_outer80`, `final_outer80` (already made) | — | the fit, the snap and flatten tools and their settings |
| `dense2` | `fit_dense2`, `snap_dense2`, `flatten_dense2`, `final_dense2`, `gate_dense2` under PHerc. 0826's run directory | each raw winding subdivided twice in rows and columns (bilinear midpoints, original nodes kept; tifxyz scale 0.05 → 0.1) before the snap | the same |

The windings, chosen now: **w020, w030, w040, w050, w060 and w070**, every tenth from w020, covering the band's
radii. The innermost ten, w010 to w019, are stacked (finding 126's check), so they are left out.

## Procedure

`repro/first_letters/eligible_band/run_dense_snap.sh`, once. Each step runs only if the one before exited 0:

1. **densify:** `densify_winding.py`, on the six raw windings, into `fit_dense2`.
2. **snap:** `run_snap.sh dense2`, the recipe's snap at its defaults.
3. **flatten:** `run_flatten.sh dense2` on each winding.
4. **compare:** `dense_snap.py compare`. For each winding of both arms, with `band_geometry.py`'s measures:
   - the final winding's share within 2 voxels of the predicted sheet, overall and by radius tercile;
   - the snapped nodes' share within 2 voxels;
   - the final winding's share within 2 voxels of its snapped triangles.

No render and no ink: nothing here reads an image.

## Decision rule, fixed now

| verdict | rule | consequence |
|---|---|---|
| `DENSE_SNAP_HELPS` | the median over the six windings of (`dense2` minus `outer80`) in the final's share within 2 voxels of the predicted sheet is at least +0.05, and `dense2`'s median share on its snapped triangles is at least 0.95 | band reads registered after this snap a twice-denser grid |
| `DENSE_SNAP_NO_GAIN` | otherwise | they keep the fit's grid |
| `DOES_NOT_RUN` | a step failed | as `DENSE_SNAP_NO_GAIN` |

## Predictions, fixed now

1. `DENSE_SNAP_HELPS`, moderate confidence, with a median gain of about +0.05 to +0.10, largest on the outer windings
   and in the outer third of radii. The ceiling is roughly the snapped nodes' own share (0.774); denser nodes do not
   make the snap itself better.
2. The snapped nodes' own share stays within ±0.03 of `outer80`'s.

## What the result cannot do

- **It is geometry.** A surface on the predicted sheet is not shown to be on the papyrus that carries ink. The
  surface prediction is the reference, and it was also the snap's target.
- **It is one band.** It is six windings of one crushed band of one scroll.
- **Disclosure.** It reads no image. The numbers come from an eligible scroll's geometry and stay as numbers.

## Cost

Snap about 5 minutes on 3 processes. Flatten about 2 to 10 minutes a winding with four times the nodes, at about 3 GB
of GPU memory, beside finding 125's Studio stage, which uses 14.5 GB of the card's 24 GB. Comparison a few minutes.
Nothing is uploaded.
