# villa PR candidate — OPENED 2026-09-15 as #1805

**Opened as https://github.com/ScrollPrize/villa/pull/1805** when #1780 merged and freed a slot.
Re-verified against upstream `d8feb9724` immediately before opening: the anchor was unchanged and
`model_dir` still in scope in the same function. The branch differs from upstream by exactly
**+1/−0** in one file.

Pushed through the GitHub API rather than a local checkout, because the only villa checkout here is
pinned to `be09a8503` for the running study and must not be fetched or branched.

---

## Title

`get_ink_metrics: record which model snapshot produced a score`

## The patch (1 line)

```diff
     summary = {
         'ink_dir': ink_dir,
         'model': args.model,
+        'model_dir': model_dir,
         'checkpoint': args.checkpoint,
```

Applies cleanly to `b82895bf1`; the file parses after applying. `model_dir` is already in scope,
assigned at the top of the same function.

## Body

`get_ink_metrics.py` resolves its model with `snapshot_download(repo_id=model)` and **no
`revision=`**, so it follows the repo's `main`. That is reasonable as a default, but it means the
weights behind a score can change between runs without anything in the run saying so.

The script already resolves and prints the exact snapshot:

```python
model_dir = resolve_model(args.model)
...
print(f'model   : {args.model}' + (f' ({model_dir})' if model_dir != args.model else ''))
```

which on a HF-backed run expands to a path ending in the revision, e.g.
`.../models--scrollprize--ink-coverage-32um/snapshots/d79c5860.../`.

But `metrics.json` keeps only the repo id:

```python
'model': args.model,          # 'scrollprize/ink-coverage-32um'
```

So the revision survives only in console scrollback. Given a `metrics.json` on its own — which is
what any comparison, dashboard or later re-analysis actually consumes — **there is no way to tell
which weights produced the number.** Two runs either side of an upstream model update are
indistinguishable in their outputs while not being comparable.

This adds the resolved path the script already computed and already prints, so nothing new is
exposed and no behaviour changes. For a local-directory model it simply repeats the given path.

If you would rather store just the revision than the full cache path, the basename of the snapshot
directory is that revision, and I am happy to send it that way instead.

**Found by:** running `spiral-fitting` here across a nine-arm study, where "are all these arms scored
with the same weights?" had to be answered from the HF cache rather than from the outputs.

## Notes for the opener

* No AI-authorship markers anywhere in the PR (villa rejected #922/#923 over exactly that).
* Keep it to the one line. The tempting scope creep is adding `--revision`, which is a feature and
  belongs in a separate discussion; the two PRs of ours that merged were both minimal.
