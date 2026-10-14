# Repeatability probe — PR review fixes

Date: 2026-10-14. Reviewed PR: #57, head
`22ea79441038e302a7c8af93b7afa9c61b1c20c3`. Integration base:
`de96eabf89ab9df22415957ed64a04950ddbb269`.
This follow-up addresses both comments from the PR review. The
[original report](DESIGN_ARCHITECTURE_REVIEW_2026-10-13_REPEATABILITY.md)
records the earlier architecture review and historical checks.

## What changed

Require the trainer to load complete starting weights for repeatability trials,
and bind the planned configuration hash to the same captured bytes that are
parsed into its settings.

## Why

The wrapper could accept checkpoint defaults that made the trainer start fresh,
and a config rewrite between loading and hashing could identify different
settings than the ones executed.

## Findings and fixes

| Comment | Reproduced behavior | Repair |
| --- | --- | --- |
| P1: actual warm start | A complete CPU checkpoint without `use_ridges`, `num_blocks` or `num_heads` passed reconstruction, but the trainer's raw-field comparison selected fresh weights. | Share the trainer's recorded-field set, reject absent/mismatched fields during child preflight, and explicitly request `strict_warm_start=True`. The trainer loads every tensor with `strict=True` and propagates errors before optimizer creation. |
| P2: config identity | Planned `lr=0.001` could carry the hash of a rewritten `lr=0.002` config, and input stability accepted it. | Capture config bytes once, parse through the shared `ExperimentConfig.from_json` decoder, hash those exact bytes and check declared inputs again before returning the plan. A changed source makes planning fail without output or a lock. |

The required starting checkpoint is deserialized on CPU and loaded into the
trainer's actual constructed model. Preflight reconstruction alone is not proof
of that load. The existing `train(config)` call retains its optional warm-start
behavior; only the probe opts into the required path. No new scoring or promotion
formula is introduced. File-based config loading uses the same decoder and still
reconstructs nested auxiliary settings.

## Verification

### Focused checkpoint, planning and training contracts

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_noise_probe_contracts.py tests/test_training_step_contracts.py tests/test_checkpoint_tool_contracts.py tests/test_loop_lifecycle.py -q --no-header --tb=short | tee /tmp/pr57-review-fixes-focused.log
```

```text
143 passed in 24.54s
```

Interpretation: checkpoint, execution, training and lifecycle contracts pass.
The added CPU regression goes through the real child wrapper and trainer,
compares every starting tensor before optimizer creation, then deliberately
halts. Three checkpoint-field omissions fail before delegation. Missing,
misshaped, extra and unreadable weights cannot be swallowed by the required
loader. The config rewrite fails planning, and captured hashes retain the parsed
learning rate and nested auxiliary settings.

The full suite below also covers the final tightened exception assertions and
the assertion that omitted fields never reach validation setup.

### Standard validation suite

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py | tee /tmp/pr57-review-fixes-standard.log
```

```text
2100 passed, 12 skipped, 1 xfailed, 2 warnings in 321.47s (0:05:21)
```

Interpretation: the final regression changes and standard suite pass. The
expected failure remains the Mutex runtime blocker; skips require external
data/backend facilities, and warnings concern CPU pin memory. No optimizer
or real training steps ran in the added wrapper regression.

### Smoke check

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py | tee /tmp/pr57-review-fixes-smoke.log
```

```text
Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
SKIP: dataloader_3tuple_sobel — training URI / inklabels not present
SKIP: dataloader_frangi_target — training URI / inklabels not present
SKIP: augmentations_bg2 — create_training_transforms not available
--- 8/11 passed, 3 skipped, 0 failed in 30.8s ---
```

Interpretation: imports, construction, complete current checkpoint weights and
available augmentation/template checks pass. Missing local data/labels and the
optional augmentation factory prevent three checks; no training run was launched.

### Typing and static checks

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /workspace/.cache/uv/archive-v0/iIym1u6_padgNlQe/bin/mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python | tee /tmp/pr57-review-fixes-mypy.log
.venv/bin/python - <<'PY'
import re
from pathlib import Path
before = Path('/tmp/repeatability-pr-mypy.log')
after = Path('/tmp/pr57-review-fixes-mypy.log')
def diagnostics(path):
    return sorted(re.sub(r'^([^:]+):\d+(?::\d+)?: error:', r'\1: error:', line) for line in path.read_text().splitlines() if ': error:' in line)
if 'Found ' in after.read_text():
    old, new = diagnostics(before), diagnostics(after)
    print('Baseline typing diagnostics:', len(old))
    print('Final typing diagnostics:', len(new))
    print('Identical diagnostics ignoring shifted line numbers:', old == new)
    assert old == new
else:
    print('Typing check is still running')
PY
```

```text
Found 14 errors in 12 files (checked 671 source files)
Baseline typing diagnostics: 14
Final typing diagnostics: 14
Identical diagnostics ignoring shifted line numbers: True
```

Interpretation: canonical typing exits one with the same fourteen diagnostics
as the reviewed PR head. New helper lines shift the trainer's existing teacher
mean/variance diagnostics; their messages are unchanged. No dependency installs
or unrelated typing fixes were used to conceal the baseline failures.

```sh
/workspace/.cache/uv/archive-v0/ZbEljn70GB_GHxGK/ruff-0.9.10.data/scripts/ruff check scripts/f1_noise_probe.py scripts/training/config.py scripts/training/train.py scripts/training/run_noise_probe.py scripts/loop_control.py scripts/run_validation_tests.py tests/test_noise_probe_contracts.py
/workspace/.cache/uv/archive-v0/ZbEljn70GB_GHxGK/ruff-0.9.10.data/scripts/ruff format --check scripts/f1_noise_probe.py scripts/training/config.py scripts/training/train.py scripts/training/run_noise_probe.py scripts/loop_control.py scripts/run_validation_tests.py tests/test_noise_probe_contracts.py
git diff --check
git diff origin/main --exit-code -- config.json best_model.pt reports/loop_v2_constant_control.json reports/loop_v2_constant_control.md docs/preregistration villa
```

```text
All checks passed!
7 files already formatted
```

Interpretation: lint/format checks pass on all PR Python files. Whitespace and
protected-artifact checks exit zero without output. The trainer and shared config
decoder are intentionally changed to enforce the fixes; the production config,
model, scientific evidence, preregistrations and Villa pin remain unchanged.

### Required documentation guards

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py -q --no-header --tb=short | tee /tmp/pr57-review-fixes-doc-guards.log
```

```text
92 passed, 1 skipped in 20.71s
```

Interpretation: all available required reference/claim guards pass with the
updated guide and follow-up report. The existing spiral-output guard skips
because that external output is absent on this machine.

## Edge cases considered

- Helper-supplied defaults versus fields actually recorded in the checkpoint.
- Missing, wrong-shaped, extra or unreadable tensors and runtime loading errors.
- Complete starting weights reaching the actual model before an optimizer exists.
- Config rewrites during construction, strict JSON serialization and nested
  auxiliary dataclasses.
- Caller working-directory and histogram context restoration after load errors.

## What was NOT tested

- CUDA execution, native compilation, optimizer steps or real training.
- Numerical GPU/CPU parity, performance, scientific noise or tolerance calibration.
- Whole-data/dependency snapshots, concurrent publication or power-loss durability.
- Scientific resolution of the promotion metric or the all-ink ceiling.

## Reviewer focus

Confirm that the required loader is used by the actual trainer, errors cannot
fall through to fresh/partial weights, and the config hash identifies the exact
snapshot used to construct the plan.
