# Every published result rests on fresh, non-empty renders (inkdelta corpus audit)

**2026-09-27.** The first use of [inkdelta](https://github.com/jonmarrs/inkdelta) beyond its
validation: `inkdelta check` was run on every scored run in `spiral_out`, and every log was swept for
the same signatures. Script: `scripts/audit_corpus_integrity.py`. Per-run results:
`reports/corpus_integrity_audit.json`.

## Result

| | count |
|---|---:|
| scored runs (`*/ink_metric/metrics.json`) | 102 |
| `STALE_SLICES`: the render re-used old per-slice TIFFs | **2** |
| `ZERO_STRIP` or `FG_ZERO` | **0** |
| unreadable or ambiguous metrics | 0 |
| `SCORER_SNAPSHOT_UNRECORDED` (warning) | 100 |
| `LOG_NOT_FOUND` (warning; no per-run log) | 52 |

**The two stale runs are both known:**

* `smp_pub`: the published-sampler arm whose "~35× slower" comparison was withdrawn (finding 65
  correction).
* `tif_score_pr1905`: re-used slices deliberately, to score another build's TIFFs through the pinned
  path. `inkdelta` cannot know intent, and flags it as its validation required.

**The 52 runs without a per-run log** rendered inside chain scripts that log several arms together.
To cover them, all **207 logs** under `spiral_out` were swept for both signatures:

* the stale-slice line appears **only** in the two logs above;
* an all-zero strip (`p95=0.0` / "rendered strip is entirely zero") appears in **none**.

The 100 snapshot warnings are expected: every run except the two upstream-scorer renders predates
villa #1805.

## What it means

No published number in this repository rests on a skipped or empty render, apart from the one already
withdrawn. The run that produced the only bad claim is exactly the one the new tool flags. Since
2026-09-27, `repro/spiral_render/run_render.sh` also refuses such a work dir at source.

## Limits

* The chain-log sweep attributes a signature to a log, not to an arm within it. It can prove absence,
  as here, but would not say which arm skipped.
* Pinned-tier and current-tier runs alike were checked for integrity only, not for comparability.
  Tiers remain non-comparable (`scripts/arm_tiers.py`).
