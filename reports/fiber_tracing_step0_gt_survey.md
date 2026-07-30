# Fiber tracing, Step 0: ground-truth feasibility survey

**Date:** 2026-07-29
**Question:** does publicly available **instance-labelled** fiber ground truth exist? The August
plan's evaluation (expected run length, split/merge) needs per-fiber identity and connectivity,
not just semantic fiber-vs-background.

**Verdict: YES. Gate passed.** Better than the plan assumed: the original WebKnossos skeleton
traces are published, not only their voxelized semantic projections.

## Where it is

`https://dl.ash2txt.org/datasets/fiber-skeletons/` (public, no credentials)

| Dataset | Contents |
| --- | --- |
| `Dataset001_sk-fibers-20250124/` | `imagesTr/` + `labelsTr/` + **`nml/`** + `dataset.json`, 11 cubes |
| `Dataset002_sk-fibers-hzvt-20250228/` | same layout, horizontal/vertical classes |
| `Dataset003_sk-fibers-hzvt-20250404/` | same layout (matches our local nnUNet baseline name) |
| `Dataset004_sk-fibers-binary-20250728/` | binary variant |

Per the dataset README: cubes of 256³ or 512³ were selected from within the scroll and *"inside
each cube, every papyrus fiber was traced and labeled"*, using WEBKNOSSOS. Conversion script
lives in villa at `foundation/datasets/fibers-dataset`.

## What the labels actually are

- `labelsTr/*.tif` is **semantic only**. `Dataset001/dataset.json` declares
  `labels: {background: 0, fiber: 1}`. This confirms the plan's concern: the voxelized labels
  cannot support connectivity metrics on their own.
- **`nml/*.nml` is the instance ground truth.** WebKnossos NML format: one `<thing>` per fiber
  (a tree), with `<node>` and `<edge>` elements giving an explicit polyline with connectivity.

Sampled `Dataset003_.../nml/fibers_s1a_00497z_01497y_03997x_256_v00.nml` (693 KB):

- **89 fibers** (`<thing>` trees), **3161 nodes**, **3072 edges**
- ~34.5 nodes per fiber on average (per-tree counts in the first twelve: 34, 41, 21, 18, 44, 52,
  36, 16, 27, 43, 47, 30)
- Node records carry integer voxel coordinates in absolute scroll space, e.g.
  `<node id="3315" radius="1.0" x="4144" y="1737" z="720" .../>`, consistent with the cube
  origin encoded in the filename (`03997x_01497y_00497z`, size 256)
- `<parameters>` gives `experiment name="scroll1a"` and `<scale x="7.91" y="7.91" z="7.91"
  unit="micrometer"/>`

## Consequences for the plan

1. **No fallback needed.** The plan's contingency (derive instance GT by hand, or weaken the
   metric) is unnecessary. ERL and split/merge are directly computable from the NML trees.
2. **Frame is 7.91 µm, the older Diamond/EduceLab-era protocol**, not the newer ESRF scans. The
   paired `imagesTr/*.tif` cubes are in that same frame, so evaluating a tracer against these
   labels needs **no cross-frame transform**. Villa's `CrossFrameZarrDataset` /
   `transform.json` bridge is only required if we later want to run on new-protocol scans, and
   is explicitly out of scope for the first deliverable.
3. **Scale is small and honest.** 11 cubes in Dataset001 at 256³/512³. That is the right size for
   the ask, which says careful small-scale work matters more than scale here, but the report must
   state n plainly and avoid over-generalizing from ~11 cubes across two scrolls (s1a, s5).
4. **Semantic priors are available off the shelf**, so we do not need to train a segmentation
   model: HF hosts `scrollprize/fiber_hz_vt` plus `fiber_selftrain_teacher_epoch30`,
   `fiber_dinoguided_2class_step010000`, and `fiber_ink_4class_selfdistill`.

## Negative findings worth recording

- The **open S3 bucket has no fiber labels or predictions at all**. Under
  `s3://vesuvius-challenge-open-data/<scroll>/representations/predictions/` only `ink-3d/` and
  `surfaces/` exist (checked PHercParis4, PHercMAN5). Fibers are absent from the modern data
  release.
- The **Hugging Face `fibers` branch of `buckets/scrollprize/datasets` is empty** (`[]`), while
  `ink`, `surfaces`, and `spiral` all carry data. So fibers are also absent from the curated HF
  datasets.
- There are **no HF datasets under the `scrollprize` author at all**; the curated data lives in
  the `buckets/` namespace instead.

The practical implication: fiber ground truth exists only on the legacy server, in an older scan
frame, and is not surfaced through either of the two channels a newcomer would look in. That is
itself part of why this lane is uncontested.
