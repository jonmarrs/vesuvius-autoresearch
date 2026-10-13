# Design and architecture review — repeatability execution and evidence

Date: 2026-10-13. Baseline: `97374b373cedc229a87220e0cf265061314d1e13`.
Villa pin: `9afddaf0fdc12efe088bab7b82534c4f9a79e536`.
Scope: the unreviewed identical-config probe, its execution isolation, lifecycle,
publication and statistical evidence boundary, plus research-lock integration.

PR integration base: `de96eabf89ab9df22415957ed64a04950ddbb269`. After the
initial review, main advanced through the depth-band and unwarped-incumbent
changes. The PR branch includes them and derives its expected protocol through
the trainer's shared `validation_protocol(config.depth_band)` helper. Base-v2
and matching band-specific results qualify; another depth range cannot qualify.
The original baseline reproductions and verification below remain historical;
the integration checks at the end of Verification describe the final PR tree.

## What changed

Make the probe import-safe and default to explicit read-only planning; execute
trials in private workspaces through the existing trainer and process supervisor,
and require complete finite evidence from all requested trials before reporting
F1 spread. Publish a new report directory and extend the existing controls to
recognize registered probe work.

## Why

The old probe launched four training processes when imported, deleted the shared
loop result, counted emitted scores from failed exits, and could publish NaN
JSON before crashing. It was presented as an isolated calibration instrument
although neither isolation nor valid statistical evidence was enforced.

## Findings and fixes

| Priority | Reproduced defect | Repair |
| --- | --- | --- |
| P1 | Module import created directories and read `config.json`, then launched training when that file existed. | Move work into CLI/functions; require `--execute` for training, with a read-only plan as default. A fresh interpreter forbidding Torch/CuPy/W&B imports verifies import safety outside the checkout. |
| P1 | Every trial deleted/replaced the checkout's `run_result.json`; a prior result was lost. | Private trial working directories and checkpoint copies isolate result/log/cache paths. A thin child wrapper redirects the trainer's file-anchored histogram path and delegates its existing logic. |
| P1 | Four exit-code-1 trials still entered the standard-deviation calculation. Missing or incomplete trials could silently yield a surviving-subset estimate. | Require exit zero, current protocol, complete sample counts, finite metric domains and a candidate artifact for every requested trial. Any failure stops remaining trials and leaves aggregate spread null. |
| P2 | Float NaNs passed the score filter and were written into JSON; the later statistics calculation crashed. | Strict finite summary fields and JSON serialization; keep raw reported-only legacy NaNs outside the summary. |
| P2 | Timeout/interruption used a plain subprocess call without worker-group cleanup. | Reuse `ProcessSupervisor`, test a real fake-trainer worker tree, and clean it before publishing a failure report. |
| P2 | Shared fixed checkpoint/config/report names and no input identity checks allowed repeated or changing runs to appear comparable. | Explicit new output, source separation, hashed config/checkpoint/entry/trainer identities and identical private starting copies; reject changed inputs. |

## Architecture and compatibility decisions

The workflow is **plan → reserve research lock → prepare private trial → strict
warm-start compatibility → supervised existing trainer → validate evidence →
publish descriptive report**. No model training or scientific experiment was
launched during this review; child processes in tests are executable fixtures.

The child validates recorded model/input settings and complete weights through
the shared checkpoint tool boundary before training. It does not duplicate
validation, selection or checkpoint logic. Trial `checkpoint_out` invokes the
existing isolated trainer branch; source scores, production config and model
weights remain unchanged. The unused default infinite skeleton bound is omitted
when serializing a config, then restored by the existing config loader.

The probe coordinates with the loop through the existing lock and controls.
The CLI anchors its working directory to the checkout for PID identity checks;
`stop.sh` can signal it, and the supervisor cleans its children. This reservation
does not coordinate another checkout or standalone fits/renders. It does not
clear `.loop_paused` or start the watchdog.

Failures can publish an inspectable new directory, but cannot produce a spread
estimate or a successful exit. Complete trials need not beat the incumbent;
promotion success is a different decision. The mean, sample standard deviation
and range remain descriptive, with `tolerance_calibrated=false`. This addresses
the execution/evidence instrument, not the scientific metric choice recorded
in [finding 86](../reports/loop_v2_constant_control.md). Subsequent host/restart
decisions are recorded in [the resume note](RESUME_AFTER_RESTART.md); this review
does not claim those remain pending.

Publication reuses the existing new-directory helper. Callers must serialize
writers and keep data, dependencies and other imported code stable. The declared
file hashes do not provide a whole-data or whole-code snapshot. Recorded command
paths reflect the real staging directory; relative trial directories identify
published artifacts.

See [Repeatability probe](REPEATABILITY_PROBE.md) for commands, migration, failure
meaning and the scientific limits to interpreting a spread estimate.

## Verification

### Baseline reproductions

The one-off baseline script ran in temporary directories and replaced training
subprocess calls with a fake result writer. It never invoked model/data/GPU code.
Exact command, run before editing the baseline checkout:

```sh
set -o pipefail
.venv/bin/python - <<'PY' | tee /tmp/repeatability-review-baseline.log
import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

repo = Path.cwd()
source = repo / 'scripts/f1_noise_probe.py'
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    importing = root / 'importing'
    importing.mkdir()
    code = 'import sys; sys.path.insert(0, ' + repr(str(repo)) + '); import scripts.f1_noise_probe'
    result = subprocess.run([sys.executable, '-c', code], cwd=importing, capture_output=True, text=True, timeout=30)
    print('IMPORT_RETURN_CODE:', result.returncode)
    print('IMPORT_CREATED_DIRECTORIES:', sorted(str(p.relative_to(importing)) for p in importing.rglob('*')))
    for scenario in ('failed_exits', 'nonfinite'):
        cwd = root / scenario
        (cwd / 'reports/detector').mkdir(parents=True)
        (cwd / 'config.json').write_text('{"time_budget": 1}')
        (cwd / 'run_result.json').write_text('{"prior": "preserve"}')
        records = []
        real_run = subprocess.run
        def fake_training(*args, **kwargs):
            value = 0.9 - len(records) / 10 if scenario == 'failed_exits' else float('nan')
            records.append(value)
            (cwd / 'run_result.json').write_text(json.dumps({'val_f1': value, 'ap_prevalence_lift': 1.5, 'roc_auc': 0.8}))
            return SimpleNamespace(returncode=1 if scenario == 'failed_exits' else 0)
        os.chdir(cwd)
        subprocess.run = fake_training
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                namespace = runpy.run_path(str(source))
            error = None
        except Exception as exc:
            namespace = {}
            error = type(exc).__name__ + ': ' + str(exc)
        finally:
            subprocess.run = real_run
            os.chdir(repo)
        text = (cwd / 'reports/detector/f1_noise_probe.json').read_text()
        print(scenario.upper() + '_RUNS:', len(records))
        print(scenario.upper() + '_ERROR:', error)
        print(scenario.upper() + '_PRIOR_RESULT_PRESERVED:', (cwd / 'run_result.json').read_text() == '{"prior": "preserve"}')
        print(scenario.upper() + '_NONSTANDARD_JSON:', 'NaN' in text)
        if scenario == 'failed_exits':
            print('FAILED_RUNS_INCLUDED_IN_ESTIMATE:', len(namespace.get('vals', [])))
            print('FAILED_RUNS_REPORTED_STD:', any('std=' in line for line in output.getvalue().splitlines()))
PY
```

Captured output:

```text
IMPORT_RETURN_CODE: 1
IMPORT_CREATED_DIRECTORIES: ['local_data', 'local_data/noise_probe']
FAILED_EXITS_RUNS: 4
FAILED_EXITS_ERROR: None
FAILED_EXITS_PRIOR_RESULT_PRESERVED: False
FAILED_EXITS_NONSTANDARD_JSON: False
FAILED_RUNS_INCLUDED_IN_ESTIMATE: 4
FAILED_RUNS_REPORTED_STD: True
NONFINITE_RUNS: 4
NONFINITE_ERROR: ValueError: cannot convert NaN to integer ratio
NONFINITE_PRIOR_RESULT_PRESERVED: False
NONFINITE_NONSTANDARD_JSON: True
```

Interpretation: import has side effects, failed exits enter statistics, the old
loop result is overwritten, and nonfinite JSON is published before failure.

### Focused execution and lifecycle contracts

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_noise_probe_contracts.py tests/test_loop_lifecycle.py -q --no-header --tb=short | tee /tmp/repeatability-review-focused.log
```

```text
46 passed in 14.15s
```

Interpretation: import/default planning, private execution, finite evidence,
input stability, complete sample accounting, shared lock refusal, worker cleanup,
interruption, wrapper context restoration and registered-probe stopping pass.
Fake trainers and a fake checkpoint loader exercise orchestration, not numerical
model parity or production training.

### Standard validation suite

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py | tee /tmp/repeatability-review-standard.log
```

```text
1982 passed, 11 skipped, 1 xfailed, 2 warnings in 238.01s (0:03:58)
```

Interpretation: the standard suite passes, including the new probe contracts.
The expected failure is the existing Mutex runtime blocker; skips require
external data/GPU facilities, and both warnings concern CPU pin memory. After
this run, output separation was tightened to reject the scripts, src and Villa
trees; the final targeted checks below cover that change and its three new tests.

### Smoke check

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py | tee /tmp/repeatability-review-smoke.log
```

```text
Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
SKIP: dataloader_3tuple_sobel — training URI / inklabels not present
SKIP: dataloader_frangi_target — training URI / inklabels not present
SKIP: augmentations_bg2 — create_training_transforms not available
--- 8/11 passed, 3 skipped, 0 failed in 9.0s ---
```

Interpretation: imports, model construction, complete production weights,
available augmentations and bandit templates pass. Missing local data and the
optional augmentation factory prevent three checks; this is not a training run.

### Final documentation and execution guards

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_noise_probe_contracts.py tests/test_loop_lifecycle.py -q --no-header --tb=short | tee /tmp/repeatability-review-doc-guards.log
```

```text
142 passed, 1 skipped in 29.64s
```

Interpretation: all nine required documentation guards and the final probe and
lifecycle contracts pass, including code-tree output rejection and same-sample
count/prevalence checks. The skip is an existing external-data requirement.

After completing this report, the documentation-only check was repeated:

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py -q --no-header --tb=short | tee /tmp/repeatability-review-final-docs.log
```

```text
92 passed, 1 skipped in 17.50s
```

Interpretation: the completed report and guide pass all available documentation
guards; the spiral output is absent on this machine, so its existing guard skips.

### Static checks and protected artifacts

```sh
/workspace/.cache/uv/archive-v0/ZbEljn70GB_GHxGK/ruff-0.9.10.data/scripts/ruff check scripts/f1_noise_probe.py scripts/training/run_noise_probe.py scripts/run_validation_tests.py scripts/loop_control.py tests/test_noise_probe_contracts.py
/workspace/.cache/uv/archive-v0/ZbEljn70GB_GHxGK/ruff-0.9.10.data/scripts/ruff format --check scripts/f1_noise_probe.py scripts/training/run_noise_probe.py scripts/run_validation_tests.py scripts/loop_control.py tests/test_noise_probe_contracts.py
git diff --check
git diff --exit-code -- config.json best_model.pt reports/loop_v2_constant_control.json reports/loop_v2_constant_control.md scripts/training/train.py docs/preregistration villa
```

```text
All checks passed!
5 files already formatted
```

Interpretation: changed Python files pass Ruff and formatting; whitespace and
protected-artifact diffs exit zero without output. The trainer, model, production
config, scientific finding, preregistrations and recorded Villa checkout are
unchanged.

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /workspace/.cache/uv/archive-v0/iIym1u6_padgNlQe/bin/mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python | tee /tmp/repeatability-review-mypy.log
.venv/bin/python - <<'PY'
from pathlib import Path
old = Path('/tmp/preprocessing-review-final-mypy.log')
new = Path('/tmp/repeatability-review-mypy.log')
errors = lambda p: sorted(x for x in p.read_text().splitlines() if ': error:' in x)
print('Baseline typing errors:', len(errors(old)))
print('Final typing errors:', len(errors(new)))
print('Error sets identical:', errors(old) == errors(new))
PY
```

```text
Found 15 errors in 13 files (checked 665 source files)
Baseline typing errors: 15
Final typing errors: 15
Error sets identical: True
```

Interpretation: canonical typing exits one with the exact same diagnostics as
the preceding baseline review. Missing YAML/requests stubs, OpenCV overloads,
augmentation slice types, the loader's optional tensor and trainer list-tensor
reductions remain pre-existing failures. None refers to a file changed here.
No dependencies were installed to mask these failures.

### PR integration checks on current main

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_noise_probe_contracts.py tests/test_loop_lifecycle.py tests/test_checkpoint_tool_contracts.py tests/test_config_depth_band_fits_fragments.py -q --no-header --tb=short | tee /tmp/repeatability-pr-focused.log
```

```text
110 passed, 2 skipped in 28.79s
```

Interpretation: the probe and shared checkpoint/lifecycle boundaries pass on
current main. Matching base/depth-band protocols succeed and another band's
results fail closed. The two config checks need local fragment data and skip.

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py | tee /tmp/repeatability-pr-standard.log
```

```text
2090 passed, 12 skipped, 1 xfailed, 2 warnings in 233.74s (0:03:53)
```

Interpretation: the entire standard suite passes on the integrated PR tree,
including main's labeled-dataset and training/inference changes. The expected
failure remains the Mutex runtime blocker; skips require external data/backend
facilities, and warnings concern CPU pin memory. This supersedes the earlier
standard-suite result for the final PR.

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py | tee /tmp/repeatability-pr-smoke.log
```

```text
Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
SKIP: dataloader_3tuple_sobel — training URI / inklabels not present
SKIP: dataloader_frangi_target — training URI / inklabels not present
SKIP: augmentations_bg2 — create_training_transforms not available
--- 8/11 passed, 3 skipped, 0 failed in 13.4s ---
```

Interpretation: smoke checks pass against the current main checkpoint; the
same local-data and optional-augmentation gaps remain. No training was launched.

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /workspace/.cache/uv/archive-v0/iIym1u6_padgNlQe/bin/mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python | tee /tmp/repeatability-pr-mypy.log
.venv/bin/python - <<'PY'
import subprocess
from pathlib import Path
log = Path('/tmp/repeatability-pr-mypy.log')
errors = [line for line in log.read_text().splitlines() if ': error:' in line]
if not errors:
    print('Typing check has not emitted diagnostics yet')
else:
    paths = sorted({line.split(':', 1)[0] for line in errors})
    changed = subprocess.check_output(['git', 'diff', '--name-only', 'origin/main'], text=True).splitlines()
    overlap = sorted(set(paths) & set(changed))
    print('Typing diagnostics:', len(errors))
    print('Diagnostics in PR files:', overlap)
    assert not overlap
    tracked = []
    untracked = []
    for path in paths:
        target = tracked if subprocess.run(['git', 'ls-files', '--error-unmatch', path], capture_output=True).returncode == 0 else untracked
        target.append(path)
    if tracked:
        subprocess.run(['git', 'diff', '--exit-code', 'origin/main', '--', *tracked], check=True)
    print('All tracked diagnostic files match origin/main:', len(tracked))
    print('Existing ignored diagnostic files:', untracked)
PY
```

```text
Found 14 errors in 12 files (checked 671 source files)
Typing diagnostics: 14
Diagnostics in PR files: []
All tracked diagnostic files match origin/main: 11
Existing ignored diagnostic files: ['scripts/_finetune_lejepa_runner.py']
```

Interpretation: canonical typing still exits one, with no diagnostic in a PR
file. Main fixed the earlier loader diagnostic; all eleven tracked files still
producing diagnostics exactly match main. The remaining ignored runner's missing
YAML stubs were also reported before this PR. No dependencies were installed.

The final Ruff commands in Static checks were repeated and still reported
`All checks passed!` and `5 files already formatted`. The protected-artifact
check used the integration base rather than the original baseline:

```sh
git diff origin/main --exit-code -- config.json best_model.pt reports/loop_v2_constant_control.json reports/loop_v2_constant_control.md scripts/training/train.py scripts/training/config.py scripts/training/promotion.py docs/preregistration villa
```

Interpretation: exit zero without output; the PR does not change main's new
production config/checkpoint, training harness, scientific evidence or Villa pin.

The actual current config was also planned from outside the checkout:

```sh
.venv/bin/python - <<'PY'
import json
import subprocess
import sys
import tempfile
from pathlib import Path
repo = Path.cwd()
with tempfile.TemporaryDirectory(prefix='vesuvius-probe-pr-', dir='/tmp') as temporary:
    root = Path(temporary)
    output = root / 'report'
    completed = subprocess.run([sys.executable, str(repo / 'scripts/f1_noise_probe.py'), '--config', str(repo / 'config.json'), '--checkpoint', str(repo / 'best_model.pt'), '--out', str(output), '--runs', '2'], cwd=root, capture_output=True, text=True, check=True, timeout=30)
    report = json.loads(completed.stdout, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    assert report['status'] == 'DRY_RUN' and report['training_executed'] is False
    assert report['protocol'] == 'seeded-sample-400-v2+z1-27'
    assert list(root.iterdir()) == []
    print('Current config dry-run outside checkout:', report['status'])
    print('Planned protocol:', report['protocol'])
    print('Created files or directories:', len(list(root.iterdir())))
PY
```

```text
Current config dry-run outside checkout: DRY_RUN
Planned protocol: seeded-sample-400-v2+z1-27
Created files or directories: 0
```

Interpretation: the current production config plans with its band-specific
protocol outside the repository, without creating artifacts or launching work.

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py -q --no-header --tb=short | tee /tmp/repeatability-pr-doc-guards.log
```

```text
92 passed, 1 skipped in 20.34s
```

Interpretation: all available required documentation guards pass on current
main with the completed PR report; the absent spiral output still skips.

## Edge cases considered

- Failed trainer exits despite emitted results; partial/no sample coverage,
  inconsistent counts, different protocols, missing candidate files and invalid
  scores, seeds or prevalence.
- Existing/source-overlapping destinations, input changes during copying or
  execution, source checkpoint mutation and normal non-promoting trials.
- Worker processes surviving their leader, timeout, interruption, an active
  research owner and return of the caller's working/histogram context.
- Strict JSON with the existing unused infinite default and raw reported-only
  NaNs, plus fresh imports without config, data or GPU packages.

## What was NOT tested

- Actual training, CT/model re-evaluation, CUDA execution or native compilation.
- Production speed/memory, scientific noise estimates or tolerance calibration.
- Atomic CT/label/dependency snapshots, changing native source, parallel writers,
  power-loss durability or interruption exactly during final publication.
- Host migration or scientific resolution of the all-ink-ceiling problem and
  metric choice in finding 86; later host decisions belong to main's resume note.

## Reviewer focus

Check complete-trial eligibility, isolation of the shared result and starting
checkpoint, worker cleanup, and the research lock/control integration. Confirm
that descriptive spread never becomes an automatic tolerance or scientific
readiness claim.
