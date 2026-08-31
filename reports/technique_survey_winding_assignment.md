# Technique survey: how absolute windings get assigned, and where the literature helps

**A spike, and a negative one. I was about to build something villa already has, in a weaker form.**
Written 2026-08-27, after issue #1621 went out, to answer: what techniques are other contributors
using on the winding problem, and does the literature offer anything we are not doing?

## What I expected to find, and why it was wrong

The plan was a technique transfer. Assigning integer windings to patches from noisy pairwise
relative measurements is a textbook problem — **group synchronization over ℤ**, the integer case of
angular synchronization — with a mature literature: least-squares on the graph Laplacian, spectral
relaxation, SDP relaxation with exact MLE recovery under Gaussian noise, and robust variants for
outliers.

My hypothesis was that villa propagates windings along a **BFS spanning tree**, which has no
redundancy: a single wrong edge propagates silently to every patch downstream of it, and the answer
depends on which tree the traversal happens to pick. Replacing that with a cycle-consistent global
solve looked like an obvious, well-grounded improvement.

The hypothesis was half right and the conclusion was wrong.

## What villa actually does

`villa/spiral-fitting/find_inconsistent_windings.py` (1,400 lines, at
our pin `ced62390e`; upstream moved it to `spiral-fitting/` in PR #1548):

1. **BFS spanning tree** for the initial assignment — as expected.
2. **Non-tree edges are not discarded.** Each closes a cycle, and the script measures its *winding
   holonomy*: the difference between the winding that edge implies and the winding the tree already
   assigned. Nonzero holonomy is a genuine inconsistency in the annotation graph, detectable without
   any absolute anchor. Reported under `"loops"`, with the full cycle reconstructed under
   `"loop_cycles"` for `plot_winding_graph.py` to render.
3. **A global integer program repairs it.** Node potentials `u_p` (integer winding, gauge-fixed at
   the seed), edge constraints `u_R − u_P == D_e`, and:

   ```
   minimise  sum_e z_e
   s.t.      −M z_e <= (u_R − u_P) − D_e <= M z_e,   u integer, z ∈ {0,1}
   ```

   solved as a MILP through HiGHS, restricted to edges lying on inconsistent fundamental cycles.
   Each violated edge comes back with a suggested corrected delta.

That is robust synchronization over ℤ under an **L0 loss** — minimise the *number* of violated
edges. It is a stronger robustness criterion than the L1/IRLS I was going to propose, and the right
one for this noise model: winding errors are sparse and large (a whole wrap), not Gaussian, so a
least-squares fit would smear one bad edge across its neighbourhood instead of isolating it.

**So the technique transfer had nothing to transfer.** villa is at or ahead of the textbook
treatment for this sub-problem.

## Where the actual gap is, and it is not algorithmic

Two facts, both checked rather than assumed:

- `find_inconsistent_windings.py` is imported by exactly one other file, `plot_winding_graph.py`,
  which draws its output. It is a **standalone CLI**, invoked one `--patch-id` at a time
  (`@click.option('--patch-id', required=True, ...)`), and nothing in the fit loop calls it.
- `satisfaction_metrics.py` contains **zero occurrences** of `winding_is_absolute` or
  `winding_annotation`, while `losses.py:935` still selects point collections on the former. The
  annotations drive the fit and never score it.

The gap is **integration, not algorithm**. villa can already detect a broken winding graph and
compute the minimal set of edges to blame. That machinery is not wired into the thing that decides
whether a patch is satisfied — which is exactly what
[issue #1621](https://github.com/ScrollPrize/villa/issues/1621) reports, and why the fix it proposes
is a comparison rather than a solver.

**This survey therefore strengthens #1621's framing and kills its natural follow-up.** Good: the
follow-up would have been a redundant reimplementation.

## What the villa community is doing on adjacent problems

From the #191 thread (89 comments) and recent issues, the working style is worth recording because
it sets the bar for anything we send:

- **Pinned-revision reproduction.** `aviad12g` re-runs claims against a named commit and reports
  where they diverge; `Jinhojeong` reads the C++ source to confirm or retire an explanation.
- **Public retraction inside hours.** A thickness map was withdrawn the day after delivery when its
  script turned out to be misreading a blosc-compressed label store. A 68° tracer failure was chased
  to a stale binary rather than an algorithm, by `flummoxjr` with `Bullo27`'s finding on #1588.
- **Harnesses over assertions.** `flummoxjr` shipped the facing-pairs harness so others could re-run
  the numbers in their own environment, rather than asking to be believed.

That is the same discipline this project has been converging on, arrived at independently.

## What the literature could still offer, honestly scoped

One open question I cannot answer from public data: **scalability**. Minimising violated-edge count
is NP-hard, and villa restricts the MILP to inconsistent fundamental cycles precisely to keep it
tractable. Whether that holds at full-scroll scale is unknown to me — I have no fitted checkpoint and
no winding graph to measure. If it does not, the literature has the standard ladder: spectral
initialisation, then IRLS on an L1 relaxation, then cycle-basis methods that solve on the cycle space
rather than the node space.

I am recording that as a **question, not a proposal**. Suggesting a scalability fix to people who
have the data and I do not, without a measurement, is exactly the kind of contribution that gets
closed on sight — and this project has ten closed PRs teaching that lesson.

## Sources

- [In-depth: Winding Constraints, Vesuvius Challenge](https://scrollprize.org/open_problems/winding_annotations)
  — defines same-winding, relative-winding and absolute-winding constraints; describes local
  constraint creation and leaves global interpretation to "the spiral fit". Makes no mention of
  cycle consistency, holonomy, or conflict resolution.
- [ThaumatoAnakalyptor](https://github.com/schillij95/ThaumatoAnakalyptor) — the prior automatic
  segmentation pipeline, now in villa under `deprecated/`. Assigns windings by random walks over a
  patch graph weighted by overlap, selecting covers that maximise overlap. A sampling approach to
  the same problem, without an explicit consistency objective.
- [Segmentation: a different approach](https://scrollprize.org/tutorial4) — the challenge's own
  description of graph-based sheet stitching.
- [The Noise-Sensitivity Phase Transition in Spectral Group Synchronization](https://arxiv.org/pdf/1803.03287)
  — spectral synchronization over compact groups and where it breaks down with noise.
- [Uncertainty Quantification of Spectral Estimator and MLE for Orthogonal Group Synchronization](https://arxiv.org/html/2408.05944)
  — SDP relaxation recovering the MLE exactly under additive Gaussian noise, and its limits.
