# Draft reply to @ge-al on villa issue #1655 — UNPOSTED, needs approval

**Why this exists.** On 2026-09-08 a contributor (`ge-al`) turned the four obstacles
I reported in #1655 into a README section on their own branch and offered it to us
directly: *"if you would rather fold it into a PR of your own like #1721, please take
it — it is your data."* They could not open the PR themselves ("GitHub is refusing PR
creation from my account on this repo at the moment").

Three days later I posted a self-correction in the same thread saying three of the
four items were already documented. That comment did not answer their offer, and it
has now been six days. Their branch `6ebe5b3a` is untouched since 09-08, so they may
still be waiting.

**Rate check.** This is a reply in an existing thread, not a new issue or PR — inside
the 1-per-day reply allowance. We are at villa's 3-open-PR cap (#1723, #1728, #1780),
so nothing here could become a PR anyway.

**Verification done before drafting**, against villa `983c20fef` (2026-09-14), read
through the API so the pinned local checkout the running study depends on was not
touched. All three citations are verbatim from the current file; the README was
touched three times today, so our notes were not trusted.

---

## Text to post

@ge-al — thank you, and sorry for the slow reply. Please don't spend any more time on
that branch: I checked it against current upstream today and the section it adds is
already there.

Verified against `983c20fef`, `spiral-fitting/README.md`:

- **`spiral-scroll.json` and its keys** — "Scroll specification (spiral-scroll.json)",
  added in #1628 on 2026-08-28.
- **the `winding_inference` path override** — "Neural winding-inference losses", which
  says to "override `paths.winding_inference` in `spiral-scroll.json`" and explains why
  the `winding_model` and `winding_inference` vocabularies deliberately coexist.
- **the default-on input switches** — the `input_use_*` example under "Spiral service
  host setup", using the same three keys I needed (`input_use_tracks`,
  `input_use_fibers`, `input_use_pcl_drawn_control_points`).

That is three of the four, and all three were documented before I filed this issue.
That was my error, which is what my comment above was correcting.

The fourth item does still stand — `lasagna_inputs/` is 47.5 GB on the published
PHercParis4 dataset while a default fit reads only the 11 GB normals sidecar — and it
is already open as #1723.

So there is nothing left here worth folding into a PR. I appreciate you doing the work
and offering it; that was a generous thing to do, and I am sorry it landed on a report
that was three-quarters wrong. I will close this issue once #1723 is resolved.
