# RECORD, POSTED 2026-08-29

Posted to ScrollPrize/villa#1621 as issuecomment-5460105766
https://github.com/ScrollPrize/villa/issues/1621#issuecomment-5460105766

The issue was ALREADY CLOSED by @pmh47 when they commented; our `gh issue close` was a no-op and
reported it as already closed. The maintainer closed it, not us.

This is a record of what was said, not a draft. Corrections go to the thread as a new comment, never
as a silent edit here. The thread is closed and was criticised as "excessively verbose": do not post
to it again.

---

Agreed, and thank you for the correction. If a patch has no attached absolute pcl there is no true winding to compare against, so periodicity is the right invariance for a metric measuring spacing self-consistency rather than absolute placement. I conflated "the statistic is invariant", which is what I measured, with "the statistic should not be invariant", which I did not establish.

One piece of corroboration from our side rather than more argument. A converged 30,000 step fit on PHercParis4 here drives `abs_winding` from 888.1 at initialisation to 2.3, at 65.4% satisfied patches. The fit already agrees with the absolute anchors because the loss puts it there, so the satisfaction metric does not need to re-check what the objective enforces.

Closing this. @Bullo27 and @TAUIL-Abd-Elilah, thank you both, and apologies for the length.
