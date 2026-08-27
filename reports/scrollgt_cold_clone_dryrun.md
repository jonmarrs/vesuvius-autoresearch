# Cold-clone dry run of ScrollGT, 2026-08-27

Ran the adoption path we advertised the same day, from a stranger's starting position: no local
checkout, no environment, nothing but the URL in the villa #191 comment.

**It works.** Cold clone to a scored fiber cube in about a minute, most of it `pip install`.

| step | result |
|---|---|
| `git clone` | 26 MB, no LFS, no submodules |
| `python3 -m venv .venv && pip install -e .` | clean, no pins fought, CLI on PATH |
| `scrollgt score-fibers` on a trivial prediction | **8.5 s**, full floor table printed |

The scored output reproduces the floor table exactly as quoted in the #191 comment: one-instance
199.18 / 0.00, connected components 197.11 / 37.13, per-voxel 0.94 / 0.94, 50-random 0.98 / 0.00,
with coverage 0.9177 and precision 0.2194 identical across every floor. That was the load-bearing
claim in the comment and it survives a cold clone, which is the only test that matters now that
other people can run it.

## What was wrong, and it was navigation rather than function

Three things, all aimed at the audience the #191 comment sends here, all now fixed.

**The CLI described itself as ink-only.** `scrollgt --help` opened with *"Score ink predictions
against registered human ground truth"* — while offering `score-columns` and `score-fibers`. A
fiber user running `--help` first was told, in the tool's own words, that they were in the wrong
place. Now: *"ink targets, column-level reading targets, and fiber connectivity targets."*

**The README buried the fiber path.** 105 lines before the first runnable command, and the fiber
section began at line 283 of 383. Someone arriving from a fiber thread had to scroll past the
entire ink family to find what they came for.

**The first thing a newcomer read was a retraction about a different target family.** The
2026-08-07 misregistration notice is honest and belongs in the README, but it opened the document,
so the first impression of the tool was a reversed headline in the ink family — for a reader who
came for fibers and is unaffected by it.

**Shipped as `jonmarrs/scrollgt@44e9311`, verified live from a second cold clone.** The fix is a jump table directly under the summary: three rows, one per target family, each with
its command, its section link and what it needs. Under it, the three-line cold-clone recipe, and
one sentence stating that the retraction below concerns the ink family only. All three anchors
verified to resolve against the actual headings.

## What was deliberately not done

**No PyPI publish.** That decision stands: it is a name grab and an ongoing maintenance promise,
worth making when someone actually uses this, not before. The cold-clone path is now fast enough
that source install is not the friction it would have been.

**No change to any number, floor, or claim.** This was a packaging pass. If the tool's substance
needed changing, that would be its own work with its own evidence.
