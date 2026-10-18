# Spawned loader workers cost 21 s a pass, outside the training budget (2026-10-17)

**Question:** why did the 2026-10-16 night cycle `use_uamt_False` die at its 3900 s timeout, with 89 s of its budget
left?

**Answer:** every pass over the training catalogue cost about 21 s that the training budget does not count. That
cycle made 15 passes; the timeout's margin allows about 10.

## Mechanism

* **The budget counts only the time inside each training step** (`train.py`, `total_training_time += dt`). The
  step that reaches the end of a pass catches `StopIteration`, makes a new iterator and `continue`s, so its time is
  never added.
* **Making that iterator respawned the loader's workers.** Since 10-16 the main checkout includes #74, so the
  labeled training loader runs 3 spawned workers. They were not persistent, so each new iterator spawned them
  again.
* **Spawning blocked `iter()`.** Spawning pickles the dataset into each worker, here 176,495 B for a stand-in for
  Fr47's 7,345 patch origins. A pickle larger than a pipe's 64 KB blocks until that worker has re-imported
  `train.py`, so `iter()` waited for the three workers in turn.
* **Measured** (`scripts/loader_pass_cost.py`, `loader_pass_cost_2026-10-17.json`; CPU, at nice 19 beside the
  loop):
  * respawned: 20.6–21.9 s in iter() on every pass;
  * persistent: 20.9 s on the first pass, 0.00 s on each after.

## In the loop

`scripts/epoch_boundary_overhead.py` measures each cycle's overhead: its sprint-log interval minus its budget.
It matches each cycle to its `run.log` run by val_f1, which gives its step count and so its passes. Then it fits
overhead against epoch boundaries crossed (`epoch_boundary_overhead_workers.json`, the 10-16/17 shifts):
**overhead = 84 s + 21.3 s per boundary over 72 cycles (residual SD 16 s).**

| budget (s) | boundaries | cycles | median overhead (s) | range (s) |
|---:|---:|---:|---:|---:|
| 900 | 0 | 9 | 63 | 57–102 |
| 900 | 1 | 49 | 108 | 53–140 |
| 900 | 4 | 3 | 177 | 164–209 |
| 3600 | 5 | 11 | 185 | 177–199 |

* **Control: the shifts before the workers.** The 10-13 to 10-15 shifts ran the loader in-process
  (`epoch_boundary_overhead_inline.json`). The same fit gives -4.1 s per boundary over 141 cycles (intercept 67 s).
  A five-pass night cycle took 55 s with the loader in-process, 185 s with spawned workers.
* **The killed cycle.** `use_uamt_False` trains without the UA-MT teacher, so its steps are faster. It made 28,970
  steps, 15 passes, before the kill, against a median of 10,360 for the other 60-minute cycles at batch 4. The fit predicts 404 s of overhead against the 300 s
  margin (`budget + 300`). It was killed at 3900 s with 89 s of its budget left.
  * The config did not crash. Every 60-minute `use_uamt_False` cycle would meet the same timeout.
* **The cost to every cycle.** Each boundary leaves the GPU idle for those seconds. That is about 106 s of each
  60-minute cycle (5 boundaries), and about 21 s of most 15-minute ones (1 boundary).

## The fix

* **Workers persist across passes** (`persistent_workers=True` in `shuffled_loader`). A new pass reuses them
  (`test_a_new_pass_reuses_the_workers`).
* **The sampler draws its permutations from its own generator.**
  * The reason: a new iterator draws a worker seed from the loader's generator, and a persistent one's reset does
    not. With one shared generator, persistence alone made the second pass a different order from an in-process
    loader's. The test failed before the generator split.
  * The test now compares the two over three passes.
  * Worker seeds keep a seeded generator of their own, so the global RNG is untouched, as before.
* **Training is unchanged:** the same budget, and per seed the same batches as an in-process loader's.
  * The order for a given seed differs from the old code's, whose permutation draws alternated with worker-seed
    draws. Each run draws a fresh seed (#79).

## What it does not say

* **The effect on the loop is predicted, not yet measured.** Overhead should stop rising with boundaries.
  Re-running `scripts/epoch_boundary_overhead.py` on the first shifts after a pull checks that.
* **Startup still spawns the workers one after another**, once per cycle; it is inside the 84 s intercept.
* **A pass's end is still not counted in the budget.** After this fix it costs 0.00 s.
* **The overhead includes the loop's own seconds between cycles**, not only the training run's.
* **The pass costs come from a stand-in dataset on the CPU.** The import that dominates them is the real
  `train.py`'s, and the 21 s they show matches the loop's fit.
