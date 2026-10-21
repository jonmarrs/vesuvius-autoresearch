# Finding 94: at a 4-voxel tolerance villa's neural tracer keeps its Scroll-3 lead, and its in-sample deficit narrows (2026-10-20)

The result of `docs/preregistration/2026-10-20_tolerance4_rescore.md`, registered at 04cb7e51 before our tracer or
connected components had been scored at tolerance 4. ScrollGT scores fibers at a tolerance of 2 voxels. Finding 91
found villa's neural fiber tracer ahead of our tracer on merge-penalized ERL on all 8 Scroll-3 cubes, and behind it on
all 11 in-sample cubes. The exploratory section of `neural_tracer_entrant.md` then found that most of the thin
entrants' Scroll-3 advantage lies within 2–4 voxels of the ground truth. This rescoring asks whether either comparison
holds at 4.

**Answer: the Scroll-3 lead holds, and widens; the in-sample deficit narrows, and reverses on the three 512³ cubes.**
P1 held and P2 failed. By the registered rule, the in-sample deficit is tolerance-dependent, and the rule recommends
a ScrollGT note where the deficit is claimed. That is the owner's call.

## The run

* **Registered and run at 04cb7e51:** `scripts/tolerance4_rescore.py`, scored 11:24–12:20 PDT at nice 19 with the
  loop running. CPU only.
* **Every labelling is the published one.** All 42 labellings (our tracer's and connected components' on 21 cubes)
  reproduce their published rows' instance counts, predicted and ground-truth lengths, and ground-truth fibers. The
  status is `OK` (`tolerance4_rescore.json`). Before registration, a smoke check at tolerance 2 on one in-sample and
  one held-out cube reproduced every published field of both labellings.
* **Villa's neural tracer** is finding 91's tolerance-4 rows, from the same run and the same ScrollGT version.

## Results

| prediction | registered | result |
|---|---|---|
| P1: the Scroll-3 lead holds | ahead of our tracer on ≥ 6 of 8 | **held:** 8 of 8 |
| P2: the in-sample deficit holds | behind our tracer on ≥ 9 of 11 | **failed:** 8 of 11 |

Medians of merge-penalized ERL, by group:

| group | n | neural tracer, tol 4 | our tracer, tol 4 | connected components, tol 4 | neural tracer, tol 2 | our tracer, tol 2 |
|---|---:|---:|---:|---:|---:|---:|
| in sample | 11 | 25.29 | 42.68 | 40.59 | 7.82 | 20.75 |
| Scroll 3 | 8 | 62.40 | 29.91 | 14.73 | 25.30 | 20.98 |
| held-out Scroll 5 | 2 | 10.77 | 12.47 | 4.66 | 4.25 | 7.44 |

* **The Scroll-3 lead widens.** The neural tracer's ERLpen over ours is a median 2.22 (1.87–2.79) at tolerance 4,
  against 1.26 at 2. It also leads connected components on all 8.
* **The in-sample deficit narrows, and reverses on the 512³ cubes.** Over ours it is a median 0.71 at tolerance 4,
  against 0.36 at 2. It still trails on all 8 in-sample 256³ cubes, but leads on all 3 in-sample 512³ ones (median
  49.50 against 43.69). Two of those three are among the five cubes where the ground truth sits about a voxel off
  the CT (#157). On the two held-out Scroll-5 cubes it still trails.
* **The thin tracer gains most from the wider tolerance.** Its ERLpen rises a median 4.30 times in sample and 2.53
  times on Scroll 3, against our tracer's 1.89 and 1.43 and connected components' 1.12 and 0.99.

## What it means

* **For ScrollGT's published Scroll-3 lead:** it holds at tolerance 4, and widens. No note is needed by the rule.
* **For its in-sample deficit:** on the 512³ in-sample cubes it is a tolerance-2 result. At 4 the neural tracer leads
  there. Per the registered rule, a note where the deficit is claimed is recommended. It could go with 0.8.2's
  placement note, since two of the three cubes are among its five.
* **For the reading of finding 91:** the thin tracer's in-sample weakness is largest where placement within 2–4 voxels
  counts most. That fits the placement and offset measurements (#151, #157), and does not separate their causes.
* **For the 256³ cubes:** finding 95 (`octant_crop_rescore.md`, pre-registered) cut the three 512³ cubes into 256³
  octants, and the lead held on 19 of 24 at tolerance 4. Cube size as scored is not why the 256³ cubes trail. Nor is
  the scroll alone: the three Scroll-5 256³ cubes trail too.

## What it does not say

* **Two tolerances, not a curve.**
* **The ground truth as published.** The offsets on five in-sample cubes stay in it.
* **ScrollGT's tolerance stays 2.0.** A wider tolerance also forgives mistakes, so a change to it would be a separate
  decision.
