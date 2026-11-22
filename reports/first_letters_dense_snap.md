Snapping a twice-denser winding grid keeps more of the rendered surface on the predicted sheet: +0.070 at the median, on every winding tried (2026-11-20)

Finding 130. Six of PHerc. 0826's read windings (finding 125's arm `outer80`) had their raw grid subdivided twice,
then went through the recipe's snap and the band's flatten unchanged. Their final surface was compared with finding
125's against the surface prediction's signed distance field. Geometry only: nothing was rendered or read. Registered
before any winding was densified: `docs/preregistration/2026-11-20_first_letters_dense_snap.md` (commit `bed84d08`).
Record: `reports/first_letters_dense_snap.json`. Scripts as run: `repro/first_letters/eligible_band/`
(`run_dense_snap.sh`, `densify_winding.py`, `dense_snap.py`). The numbers come from an eligible scroll's geometry; no
image was made.

**Verdict `DENSE_SNAP_HELPS`**, as predicted, by the registered table. Every step exited 0. The median gain in the
final surface's share within 2 voxels of the predicted sheet is +0.0697 (rule: at least +0.05), and the dense arm's
median share on its snapped triangles is 0.9877 (rule: at least 0.95).

## The registered numbers

Share of the final (flattened) winding's nodes within 2 voxels of the predicted sheet:

| winding | fit's grid (`outer80`) | twice denser (`dense2`) | gain |
|---|---|---|---|
| w020 | 0.7756 | 0.8425 | +0.0669 |
| w030 | 0.6739 | 0.7485 | +0.0746 |
| w040 | 0.6926 | 0.765 | +0.0724 |
| w050 | 0.6433 | 0.7248 | +0.0815 |
| w060 | 0.6559 | 0.7176 | +0.0617 |
| w070 | 0.5114 | 0.5651 | +0.0537 |
| **median** | **0.6649** | **0.7367** | **+0.0697** |

## Described

| median over the six | `outer80` | `dense2` |
|---|---|---|
| snapped nodes within 2 voxels of the predicted sheet | 0.7722 | 0.8303 |
| final nodes within 2 voxels of the snapped triangles | 0.9706 | 0.9877 |
| final within 2 voxels, inner third of radii | 0.7624 | 0.8331 |
| final within 2 voxels, middle third of radii | 0.6783 | 0.7669 |
| final within 2 voxels, outer third of radii | 0.5444 | 0.6174 |

- **The gain is even across radii,** +0.07 to +0.09 in each third. It is not concentrated at the crushed tips, as I
  expected.
- **The second prediction was wrong.** I predicted that the snapped nodes' own share would stay within ±0.03. It rose
  by +0.058, so denser nodes also made the snap itself better. A likely reason, not tested, is that the snap's
  smoothing (`sigma` 1) and jump limit act per node: on a denser grid they span half the distance.
- **The outermost winding gains least,** and w070 stays the furthest off the sheet at 0.5651. Most of what is lost
  there is already lost in the snap (0.5771 to 0.6241 at the snapped nodes).

## What it cost

| step | wall time |
|---|---|
| densify, six windings | 1 s |
| snap, about four times the nodes | 50 s |
| flatten, per winding | 134 to 254 s (finding 125: 71 to 177 s on the fit's grid) |
| comparison | 69 s |

The flatten ran beside finding 125's Studio stage. The card's memory peaked at 15,428 MiB for both, so the flatten
used about 1 GB more than Studio alone. The flatten writes its output at 20 voxels a node whatever its input, so the
render and Studio cost the same.

## What this does to the campaign

The registered consequence: band reads registered after this snap a twice-denser grid. Finding 129's PHerc. 0813 read
will be the first. On 0826's read, finding 125's 70 windings were read on the fit's grid and stay as registered.

## What this does not show

1. **That the denser surface is on the papyrus that carries ink.** The reference is the surface prediction, which is
   also what the snap moves nodes toward. A surface nearer the predicted sheet is a better bet, not a demonstrated
   gain in what Studio reads.
2. **Anything beyond six windings of one crushed band of one scroll.**
3. **Whether a factor of 3 or more would gain further.** Only 2 was tried.
