# Research roadmap

**Updated November 5, 2026 UTC.** The current decision record is
[Research strategy: useful progress on one RTX 4090](RESEARCH_STRATEGY.md).
It replaces the July roadmap and reconciles the current official prize rules,
our actual measurements, upstream work already in progress and our compute
budget. Historical reports and preregistrations retain their original scope.

1. **Pursue useful November engineering on current Villa.** The official
   [November rollover](https://github.com/ScrollPrize/villa/pull/2301) merged
   on November 5; its [pinned rules](https://github.com/ScrollPrize/villa/blob/9c343a16494cf61d72727cbc85dc5e12e8773677/scrollprize.org/docs/34_prizes.md)
   give November 30 at 11:59 p.m. Pacific as the monthly deadline. The best
   monthly submission receives $20,000; other amounts, including $250, are
   discretionary. A merged PR is not an automatic award. Prioritize bugs
   encountered on real scroll workflows, release useful fixes early and
   bundle small contributions. The newer rules discourage standalone auditing
   tools. The latest [PHerc306B announcement](https://scrollprize.substack.com/p/writing-seen-in-pherc-306b-for-the)
   describes a result developed on an RTX 4090, supporting bounded exploration
   with released models rather than requiring large rented accelerators.
2. **Finish integrations people can use.** All three previously queued owner
   Villa PRs merged: [#2141](https://github.com/ScrollPrize/villa/pull/2141)
   and [#2259](https://github.com/ScrollPrize/villa/pull/2259) on October 30,
   [#2258](https://github.com/ScrollPrize/villa/pull/2258) on November 1. Verify
   the prepared seed-heading fix through the
   [current object-store workflow](VILLA_OBJECT_STORE_EXPORT_CHECK.md) on a
   configured host. Keep existing fixture checks separate from native
   real-data proof. Respect the upstream PR cap.
3. **Use the current issue queue before inventing another tool.** At Villa
   `9c343a1`, [#2371](https://github.com/ScrollPrize/villa/issues/2371)
   (downloader pyramid coordinates) already has
   [#2379](https://github.com/ScrollPrize/villa/pull/2379);
   [#2246](https://github.com/ScrollPrize/villa/issues/2246)
   (offset-layer normals) has [#2449](https://github.com/ScrollPrize/villa/pull/2449);
   [#2391](https://github.com/ScrollPrize/villa/issues/2391)
   (offset configs) has [#2418](https://github.com/ScrollPrize/villa/pull/2418).
   Do not duplicate them. [#2437](https://github.com/ScrollPrize/villa/issues/2437)
   requests reopening the existing inpainting fix, which needs a native build
   and real-surface replay. [#2444](https://github.com/ScrollPrize/villa/issues/2444)
   needs authoritative sheet-tracer training bands before a same-scroll
   evaluation can be called held out. Historical metadata cannot reconstruct
   those bands reliably. Recheck status before starting work.
4. **Choose one bounded research pilot after its prerequisites are met.**
   Conservative fiber connectivity and independently reviewed label correction
   address the official [open problems](https://scrollprize.org/2026_open_problems).
   Findings 101–104 in the strategy close the existing refit retry as a useful
   continuation rule: coverage rose while wrong connections also rose. A new
   continuation needs a discriminating rule and a fixed comparison protocol;
   neither relaxed stops nor a presence-only gate is supported by that result.
   Keep independent human-click reach, precision and wrong connections beside
   coverage. Do not tune on a confirmation set.
5. **Keep ink research controlled.** After the registered
   [unchanged-training comparison](preregistration/2026-10-27_loop_unchanged_control.md)
   closes, consider one matched-update cross-scroll intervention. Use
   untouched test regions and fixed selection rules. Defer foundation-model
   pretraining and broad parameter sweeps on this single GPU.

The selected cloud environment currently has no CUDA device, no connected GPU
host credentials, and no native `vc_reader` bindings. No GPU experiment or
current-native Villa workflow was run for this update. CPU work improves the
existing [fragment linker](FIBER_RELINKING.md), with exact-geometry replay;
that measurement is not evidence of independent reading or upstream adoption.
Reassess the available host before scheduling a GPU pilot; the hardware budget
remains one RTX 4090 with 24 GB VRAM, with no rented compute assumed.

## October filing record

The completed October
[filed engineering record](PRIZE_FILING_2026-10_SUBMITTED.md) preserves the
three Villa merges and verified receipt; the
[second response](PRIZE_FILING_2026-10_SECOND_SUBMITTED.md) adds #2141 and
#2259, merged on October 30. The optional ScrollGT research
answer remains unsubmitted in this workflow. The
[final-week plan](PRIZE_PLAN_2026-10_FINAL_WEEK.md) is historical; the October
deadline has passed. This work submits no contest entry.

The official rules allow larger model windows when supported by evidence
against hallucination. The repository's historic 64-pixel / 0.5-mm checks are
local conservative contracts, not a statement of current prize eligibility.
Do not change frozen studies or disable validation to explore a new window.
The strategy links the pinned official wording and distinguishes detection,
teacher imitation and independently verified reading.

Run development in a separate checkout. While the registered study is open,
a pull into its live checkout ends the window; use counts-only status and
avoid competing GPU work. This roadmap starts no experiment and makes no
claim that a contribution will win an award.
