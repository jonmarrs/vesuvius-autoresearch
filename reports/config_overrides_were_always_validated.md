# Every config-override arm we ran was validated — checked, not assumed

**2026-09-18.** A validity property, not a finding. Recorded because it underwrites a lot of past work
and because the question only surfaced by accident.

## Why it came up

Reviewing villa's recent commits for a contributable defect, `b82895bf1` ("ignore keys which are not
known in advanced config") turned a hard failure into a warning:

```python
-        unknown = sorted(set(self.run_config.config) - set(config))
-        if unknown:
-            raise ValueError(f"Unknown advanced config keys: {unknown}")
+        advanced_config = filter_known_config_keys(
+            self.run_config.config, config, label="advanced config", warn=warn)
```

**If our path behaved that way, a misspelled key would be silently dropped and the arm would run with
defaults** — producing a "treatment" arm identical to baseline, and a study measuring nothing while
looking perfectly healthy. Most arms in this project set `FIT_SPIRAL_CONFIG_OVERRIDES`:
`gap133`, `boot090`, `rand090`, `nosame*`, `anchor10cov*`, `densespace0`, and the `curbase` seeds.

## What is actually true

`fit_spiral.py`, the path every arm here uses, **raises**:

```python
overrides = json.loads(overrides_json)
unknown_keys = sorted(set(overrides) - set(Config().as_dict()))
if unknown_keys:
    raise KeyError(f'unknown FIT_SPIRAL_CONFIG_OVERRIDES keys: {unknown_keys}')
```

Verified at **both** our pin `be09a8503` and current upstream `b1ef996e3`. `b82895bf1` touched
`config.py`, `spiral_runtime.py` and `spiral_service.py` — **not `fit_spiral.py`**.

So a typo would have aborted the fit loudly. **No arm in this project can have silently run with
defaults through a mistyped override**, and every registered comparison that relied on an override
changing behaviour is sound on that axis.

The warn-versus-raise split is deliberate rather than an inconsistency: a saved workspace may carry
keys retired since it was written, while an explicit CLI override is a direct instruction that should
fail if it cannot be honoured.

## No villa contribution here

The slot remains free and this is not a defect. Recording the negative so the same commit is not
re-examined later as a suspected hazard.

**What would have made it one:** if `fit_spiral.py` shared the filtering path, every override-based
study in this repository would need its arms re-verified. That is why a five-minute check was worth
running on a commit that merely looked adjacent.
