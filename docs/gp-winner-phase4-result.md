# Memory: GP-Winner Phase 4 Result

**Type:** project

## Verdict
The scaled production TimeSformer (3 train segments + 1 holdout, 15 epochs) confirms the finding from Phase 4a Step A — the prize topology gate is **not detection-limited**.

Even an AUC 0.896 scaled TimeSformer model misses the topology gate (`skel_dist <= 2.0`) by ~7.5x, scoring `skel_dist = 15.0`. The bottleneck is definitively the topology / post-processing stage (thin-centerline extraction, connected-component cleanup) or the gate metric itself, which was invented for this repo and is not the actual Vesuvius prize criterion. The autoresearch loop has been gating on a metric that a Grand-Prize-quality model fails.

## Links
- [[gp-winner-phase3-result]]
- [[model-barely-discriminates-ink]]
