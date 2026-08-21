# POSTED — `#robots`, 2026-07-29 (verbatim record)

**⚠ Two claims in the post below were retracted on 2026-08-07 and corrected publicly
in `#robots` on 2026-08-14** (verbatim reply: `DISCORD_POSTED_robots_2026-08-14_CORRECTION.md`).
The held-out "reads at chance" result was our own misregistration and reverses: the canon
teacher scores 0.753 and our clean students 0.731 and 0.746. **The body below is deliberately
left unedited**, because it is the verbatim record of what was posted; this header is the
pointer a later reader needs.

This is the exact text Jon posted to the ScrollPrize Discord `#robots` channel for the July
2026 Progress Prize. Recorded verbatim as the public artifact of record — do not edit this
file to "improve" it. Working drafts live in `DISCORD_ANNOUNCEMENT_DRAFT_2026-07.md`.

Thread title used: see the draft file (`ScrollGT: held-out ground-truth scoring for the SOTA
data + a renderer for mesh-only segments`).

Compliance against the `#robots` rules (rules obtained *after* posting):
- "name the model" — **SATISFIED** by the opening disclosure line.
- "include useful context" — satisfied.
- "prefer testable claims and reproducible work" — satisfied (every claim is a number
  reproducible from a published baseline row; links to repos + FINDINGS).
- "separate model output from human commentary" — **not explicitly marked**, but the post
  contains no human commentary to separate; it is model output end to end, so the rule's
  purpose (never pass model text off as human reasoning) is not violated. A short reply in
  Jon's own words would satisfy it explicitly.
- "treat every output as a proposal to verify, not an authority" — satisfied in substance
  (own negatives published, falsification invited) though not stated in those words.

For future months use the two-message template in the draft file, which marks the boundary
explicitly with a `──── MODEL OUTPUT ────` rule and leaves message 2 for Jon's own words.

---

*AI disclosure: primarily Claude Opus 4.7, with Claude Opus 5 on the most recent work.*

Two open-source tools for the open SOTA data (MIT):

**ScrollGT** — registered human ground-truth evaluation for the SOTA surface volumes. The bucket ships surface volumes and model predictions but no human labels aligned to the new geometry, so it's hard to answer "does my model read, or does it reproduce another model?" ScrollGT registers the 2023 GP-era hand labels onto the SOTA geometry (exact original.obj UV bridge, ~8-voxel median residual) and ships a one-command scorer (threshold-swept F1 + AP-prevalence-lift as an anti-gaming gate + ROC-AUC).

Fair warning that it has teeth: our own distilled models drop from 0.79+ on train-exposed regions to ~0.55 held-out, and every negative is a published baseline row. A PHerc-1667 target scores consistency with the published reading's 22 columns, since no pixel GT exists there; constant and papyrus-mask predictions both score exactly 0.5, and our models sit at that floor too.

Beating ROC-AUC 0.60 on the held-out target, honestly, would be news — CONTRIBUTING.md has the submit-a-row flow, and we'd like to add your scorecard.
<https://github.com/jonmarrs/scrollgt>

**Surface renderer for mesh-only segments** — some bucket segments ship geometry but no surface volume (both PHerc0332 segments; PHerc1667's merged full-reading segment). This CLI renders a detector-ready 26-layer surface volume from either original.obj or the released tifxyz grid, label-free. Validated against released volumes on two scrolls: Scroll 1 NCC 0.59 (miss vs our pre-registered 0.60 gate, resolution-limited comparison), PHerc1667 NCC 0.78 pass, all 26 layers matching at 0.84–0.89. It produced the first independent surface volumes of all three.
<https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/SURFACE_RENDERER.md>

Methodology and negative results behind both: <https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/FINDINGS.md>
