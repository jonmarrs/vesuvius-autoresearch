# RECORD, POSTED 2026-08-30

Posted as ScrollPrize/villa#1658: https://github.com/ScrollPrize/villa/issues/1658

A record of what was said, not a draft. Corrections go to the thread as a new comment, never as a
silent edit here. No nudges: await a reply.

---

`spiral-fitting/autoresearch.md` describes the loop's pipeline and its objective. Two things in it do not match the code. Both are quick to check against `5479453a`.

### 1. `get_ink_coverage.py` does not exist

The doc names it four times, including in the pipeline description:

> 3. `get_ink_coverage.py <meshes_dir>/ink` scores ink coverage into `<meshes_dir>/ink_metric`.

There is no `get_ink_coverage.py` in the repo. The scorer is `spiral-fitting/get_ink_metrics.py`, which is what `runners/run_single.py` invokes.

```
$ git ls-tree -r --name-only origin/main | grep -c get_ink_coverage.py
0
```

### 2. The scorer writes two structure metrics the doc never mentions

`get_ink_metrics.py` computes and persists into `metrics.json`:

```python
'overall_line_score':   row['line_score'],   # text-line pitch periodicity, expected band 80-120 strip px
'overall_column_score': row['col_score'],    # column width, expected ~850 px
```

`autoresearch.md` mentions neither. It points the loop at `total_fg_pixels` as the objective, `overall_fg_fraction` as the guard against inflating the surface with garbage geometry, and the `fit_spiral.py` satisfaction metrics as diagnostics.

Both structure scores are already computed on every run at no extra cost, and unlike `overall_fg_fraction` they respond to whether the recovered ink is laid out like text. It may be worth stating explicitly whether the loop is meant to read them or ignore them, since right now a run that improved `total_fg_pixels` while degrading line and column structure would look like a clean win in the documented reading.

I have not run the loop, so this is a read of the code and the doc rather than a claim about how the metric behaves in practice. The render path needs `vc_render_tifxyz`, `flatboi`, `vc_tifxyz2obj`, `vc_obj2tifxyz` and `vc_obj_uv_lift`, which I do not have built.
