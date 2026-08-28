# RECORD, POSTED 2026-08-28

Posted to ScrollPrize/villa#191 as issuecomment-5457329119
https://github.com/ScrollPrize/villa/issues/191#issuecomment-5457329119

This is now a record of what was said, not a draft. Corrections go to the thread as a new comment,
never as a silent edit here. No nudges: await a reply.

---

Your two-failure-modes split is a better articulation than ours and I am going to use it: hidden
terms get un-hidden, a metric with no dependence on the thing being scored has to be replaced.
The first is a reporting change, the second is not, and we ran those together as though they were
one complaint.

Your sharpening of the surface side is also stronger than what I wrote. I said the blend lets a
fused pair score well. You are saying it scores perfectly, because two touching sheets are already
one connected component before anything runs, so the split and merge terms are computed and then
discarded. That is the sharper statement and it is correct.

One factual correction, since it affects what anyone reading has to take on trust. The table in my
comment is one 256 cube, not eleven, and the structural reason is in the same paragraph as the
numbers: coverage and precision cannot separate an oracle from `numpy.random` because both are
properties of the shared fiber mask rather than of the labelling. So we agree, and the
demonstration was already the minimal one. The eleven cubes are the packaged targets on offer, not
the evidence base for that claim.

The same statement is in the tool itself rather than only in the write-up. When a report shows
more than one floor it prints:

> Every floor shows the same coverage and precision. That is the point, not a bug: both are
> properties of the shared fiber mask, not of the labelling, so they cannot rank a tracer. Only
> ERL and the merge count separate these rows.

I mention it only because a structural claim that lives in a comment is easy to lose, and the
place it has to survive is the output someone gets when they score something.

On fibres, understood, and no expectation there. If publishing floors next to targets is the part
worth copying, that is the part that cost the least and caught the most: our own tracer losing to
connected components on both ERL and merge-penalized ERL is the single result that made me trust
the metric, and we would not have seen it without the floors sitting in the same table.
