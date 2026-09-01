# villa's default spiral config asks for 3 more windings than it provides

**2026-09-01.** A self-reported inconsistency in the shipped defaults, found while investigating
something else. It holds independently of that investigation and of its outcome.

## The finding

Every fit we have run prints this, six for six:

```
WARNING: shell_outer_winding_idx 130 requires model_gap_expander_num_windings >= 133,
         got model_gap_expander_num_windings 130; increase model_gap_expander_num_windings
         or lower shell_outer_winding_idx
```

It is emitted by `spiral_helpers.py:1071-1078`, and both values are **shipped defaults**:

| setting | file | default |
|---|---|---:|
| `shell_outer_winding_idx` | `config.py:489` | **130** |
| `model_gap_expander_num_windings` | `config.py:287` | **130** |
| required minimum | `spiral_helpers.py:1071` | `idx + 3` = **133** |

## Why it fires on every default run, not just ours

The obvious reading, that this is specific to our configuration, does not hold:

* **No shipped config overrides either value.** All 40 JSON files under `spiral-fitting/configs/`
  were checked, including `default_config.json` and the sweep defaults. None mentions either key.
* **The inference path cannot rescue it.** `resolve_outer_winding_idx_and_notes` infers the index
  only when `shell_active AND idx is None`. `_resolve_shell_outer_winding_idx` returns the configured
  value whenever it is not None, and the default is 130, not None. So inference never runs under
  defaults and `idx` is always 130.
* **The check is outside the shell branch.** `if idx is not None:` gates it, not `if shell_active:`,
  so it applies whether or not outer-shell losses are active.

Our own runs take the `no outer-shell losses` branch, but that changes only which note is printed,
not the arithmetic.

## What the consequence is: NOT established

The code comment says the index bounds "every sampler that integrates over the spiral cylinder: the
dense lasagna losses, the symmetric Dirichlet regulariser and the phase bundle (incl. min_spacing)".
The warning itself states the requirement and the remedy, but **not the effect of ignoring it**. I
have not established what the three-winding shortfall does, and this report does not claim it does
anything. It may be harmless.

A separate arm (`docs/preregistration/2026-09-01_gap_expander_capacity.md`) tests one specific
possible consequence, whether it contributes to the duplicate coverage concentrated in the outermost
windings. That is pre-registered, its outcome is unknown as this is written, and **this finding does
not depend on it**. Raising `model_gap_expander_num_windings` to 133 makes the warning disappear,
verified on a 100-step fit.

## Why it is worth reporting regardless

A default configuration that warns about itself on every run trains readers to ignore warnings. If
the shortfall is harmless the default should be consistent so the warning stops; if it is not, every
default run is affected. Either way the current state is a defect.

## Limits

One dataset and one dataset json, though the values in question are read from villa's own config
rather than ours.

**The call-path limit is now closed.** Every mention of either key anywhere in the villa tree, across
`*.py`, `*.json`, `*.sh`, `*.md` and `*.toml`, was checked. Outside `config.py`, which holds the
defaults, and the two files that read them (`spiral_helpers.py`, `flatten_spiral_checkpoint.py`),
every occurrence is a **consumer**: `phase_tuning.py` reads the index, `fit_spiral.py` passes it to
`get_progressive_dt_max_winding` and warns separately at line 2219 when a weight is positive but the
index leaves it inactive. **Nothing assigns either key** in any runner, script or config, so
`run_single.py` and the autoresearch loop take the defaults unchanged.

What remains untested is the consequence, not the reach: I still have not run villa's pipeline end to
end under its own runner and observed what the shortfall does.
