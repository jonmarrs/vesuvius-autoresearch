# DRAFT (NOT FILED) — villa issue: mesh scale metadata does not distinguish frames

**Status: drafted 2026-08-18, NOT filed.** Jon's call on whether and when.

Target: a **new issue** on `ScrollPrize/villa`, not a PR. Modelled on the contribution
pattern the accepted community listings share: `scroll-data-audit` reported a real catalog
defect (#1211) and `vesuvius-repro` landed #1253. This reports a defect and asks for nothing.

Constraints held deliberately:

- **No ask.** No listing request, no link to a prize submission, no mention of our closed PRs.
- **Numbers re-verified against the live bucket on 2026-08-18** before drafting, not taken
  from our own tool's README. 311 / 257 / 204 / 40.33x all reproduced. The README's "median
  7x" did NOT reproduce (8.29x across the 257 multi-frame segments), so the verified figure
  and its denominator are used here and the README needs its own correction.
- **Proposes a fix without demanding one**, and names the cheapest version first.
- **Credits the prior art.** `scroll-data-audit` and `tifxyz-repair` certified the corpus
  clean on metadata *validity*; every file here passes them, correctly. This is a different
  axis: each file is internally valid, and they are mutually incomparable.

---

## Title

`mesh meta.json "scale" does not distinguish frames: 204 segments ship meshes whose declared scale is identical while voxel sizes differ up to 40x`

## Body

**Summary.** For a segment with more than one `.tifxyz`, `meta.json` gives no way to tell
which scan frame a mesh's coordinates are in. Every mesh declares the same `"scale"`, which
is correct in each file taken alone, while the underlying voxel sizes differ by up to 40x.
The voxel size appears nowhere in `meta.json`; it is recoverable only from the directory name.

**Measured across the open bucket on 2026-08-18** (47 scroll prefixes, anonymous S3):

| | count |
|---|---|
| segments with a `mesh/` directory | 311 |
| of those, carrying more than one `.tifxyz` | 257 |
| of those, whose meshes all declare the same `scale` while voxel sizes differ | **204** |

Voxel-size spread across the 257 multi-frame segments: median 8.3x, maximum 40.33x.

**Example** (`PHercParis4/20230702185753`, 4 meshes):

```
mesh                                     um/voxel   declared scale
-on-20260608103018-1.129um.tifxyz           1.129    0.05
-on-20260411134726-2.4um.tifxyz             2.400    0.05
-on-20230205180739-7.91um.tifxyz            7.910    0.05
-on-20260310170716-45.532um.tifxyz         45.532    0.05
```

All four declare `0.05`, meaning "20 voxels of my own scan", true in each file. Across files
it is the same number for frames that differ by 40x.

**Why it bites.** A consumer that reads `meta.json` to decide whether two meshes' coordinates
are comparable gets "yes" in all 204 cases. Anything that bridges between meshes of one
segment (comparing surfaces, transferring labels or annotations, reusing a registration)
silently mixes frames. It cost us real time before we understood it, which is why we looked
at the whole catalog rather than only our own segments.

**Not a validity problem.** `scroll-data-audit` and `tifxyz-repair` both certify this corpus
clean, and they are right: every file here is internally valid and self-consistent. The gap is
between files, not within one.

**Reproducing.** The listing above is `mesh/*/meta.json` plus the directory names, nothing
else. A standalone checker is at <https://github.com/jonmarrs/scroll-frames> (MIT,
stdlib+numpy) if that is useful, but the survey is a few lines against the bucket and does not
need it.

**Possible fixes, cheapest first.** Recording the voxel size in `meta.json`, a value already
present in the directory name, would resolve it outright, since a consumer could then compare
frames without parsing filenames. A `scan` or `frame_id` field would do the same. Failing
either, documenting that `scale` is scan-relative and that mesh coordinates are not comparable
across meshes of one segment would at least make the trap findable.

Happy to send a PR for whichever of these you would want, or to leave it as a report.
