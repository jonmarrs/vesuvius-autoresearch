"""The standard suite runs every test of the code the loop runs.

scripts/run_validation_tests.py lists its modules by hand, and 40 modules testing
code the loop, its training run, its benchmark or its evidence chain execute had
never been added (2026-10-16): the promotion criterion's, the promotion metric's
(val_f1, detector.metrics), the prize gates', the Frangi target's and the loader
workers' among them.

The loop's code is what its entry points import, followed through the repo. It
counts the module an import uses, not the packages that import only loads on the
way: train.py's `from vesuvius_autoresearch.detector.metrics import ...` runs
metrics.py, and only loads detector/__init__.py, so the detector's own tests are
not required. Importing names from a package's __init__ (the loader's
`from vesuvius_autoresearch.fibers import detect_ridges`) uses that __init__ and
what it re-exports.

Some of it is run by path rather than imported: the evidence chain launches
scripts/inference/launch_neural_tracing.py, and the noise probe its runner. They
are entry points too, and a test that loads a script by its file name, as
tests/test_villa_baselines_launchers.py does, tests it. That file had never been
listed (2026-10-22), because the guard saw only imports. Every other script the
loop's code names by path it only writes into a report, plan or worklist;
NAMED_NOT_RUN lists them, so a script the code starts to run cannot go unseen.
"""

import ast
import re
from pathlib import Path

from scripts import run_validation_tests

REPO = Path(__file__).resolve().parents[1]
# Where the loop's processes resolve imports: the checkout (the loop's working
# directory), the installed src/, train.py's own directory and scripts/.
ROOTS = (REPO, REPO / "src", REPO / "scripts" / "training", REPO / "scripts")

# What the loop and its operators run: the loop and its lock; the training run,
# its --smoke preflight and the benchmark; the scripts that share the loop's
# lock; and the post-sprint handoff with each script its steps run.
ENTRY_POINTS = (
    "run_autoresearch_loop.py",
    "scripts/loop_control.py",
    "scripts/training/train.py",
    "scripts/inference/predict.py",
    "scripts/smoke_test.py",
    "scripts/reevaluate_best_model.py",
    "scripts/f1_noise_probe.py",
    "scripts/ablate_scroll_augmentations.py",
    "scripts/train_with_new_augs.py",
    "scripts/run_post_sprint_villa_handoff.py",
    "scripts/archive/audit_villa_upstream.py",
    "scripts/plan_villa_prize_opportunities.py",
    "scripts/review_villa_pin.py",
    "scripts/build_villa_component_coverage.py",
    "scripts/build_volume_cartographer_readiness.py",
    "scripts/inference/run_ranked_inference.py",
    "scripts/rank_scroll23_candidates.py",
    "scripts/build_lasagna_fiber_worklist.py",
    "scripts/run_villa_prize_evidence_chain.py",
    "scripts/summarize_villa_evidence_preflight.py",
    "scripts/build_villa_prize_action_matrix.py",
    "scripts/build_villa_review_manifest.py",
    # Run by path, not imported: by the evidence chain and the noise probe.
    "scripts/inference/launch_neural_tracing.py",
    "scripts/training/run_noise_probe.py",
)

# Scripts the loop's code names by path but does not run: the villa coverage
# report, the opportunity plan, the review manifest, the Volume Cartographer
# readiness report and the action matrix describe them, and the lasagna worklist
# writes their commands for a person to run.
NAMED_NOT_RUN = {
    "scripts/autoresearch_thaumato_solver.py",
    "scripts/compute_structure_tensors.py",
    "scripts/crop_candidate_zarr.py",
    "scripts/labeling/generate_fiber_labels.py",
    "scripts/launch_crackle_viewer.py",
    "scripts/launch_thaumato.py",
    "scripts/launch_vc3d.py",
    "scripts/smoke_test_villa_optimized_inference.py",
    "scripts/training/launch_finetune_lejepa.py",
    "scripts/training/launch_gp_winner.py",
    "scripts/training/launch_mutex.py",
    "tests/test_import.py",
    "v3_training/trainer.py",
}
SCRIPT_NAME = re.compile(r"[\w./-]+\.py")


def _module_file(name, roots):
    """The repo file whose code `import name` runs, or None outside the repo."""
    for root in roots:
        path = root.joinpath(*name.split("."))
        for candidate in (path / "__init__.py", path.with_suffix(".py")):
            if candidate.is_file():
                return candidate
    return None


def imported_files(path):
    """The repo files whose code path's import statements use: a submodule for
    `from package import submodule`, the package's __init__ for
    `from package import name`. Imports inside functions count too."""
    files = set()
    for node in ast.walk(ast.parse(path.read_bytes(), str(path))):
        if isinstance(node, ast.Import):
            files.update(_module_file(alias.name, ROOTS) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots = ROOTS
            if node.level:
                base = path.parent
                for _ in range(node.level - 1):
                    base = base.parent
                roots = (base,)
            module = node.module or ""
            for alias in node.names:
                name = f"{module}.{alias.name}" if module else alias.name
                files.add(
                    _module_file(name, roots)
                    or (_module_file(module, roots) if module else None)
                )
    files.discard(None)
    return files


def named_scripts(path):
    """The repo's .py files that path's strings name: a repo-relative path, or a
    bare file name under scripts/ (the evidence chain builds its launcher's path
    from parts). villa/ is not this repository's code."""
    found = set()
    for node in ast.walk(ast.parse(path.read_bytes(), str(path))):
        if not (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and SCRIPT_NAME.fullmatch(node.value)
        ):
            continue
        name = node.value
        candidates = [REPO / name] if "/" in name else (REPO / "scripts").rglob(name)
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate.is_file() and candidate.is_relative_to(REPO):
                if candidate.relative_to(REPO).parts[0] != "villa":
                    found.add(candidate)
    return found


def _runs_code(path):
    """False for a package marker: an __init__ with nothing but a docstring."""
    body = ast.parse(path.read_bytes(), str(path)).body
    if body and isinstance(body[0], ast.Expr):
        body = body[1:]
    return bool(body)


def loop_files():
    seen, todo = set(), [REPO / entry for entry in ENTRY_POINTS]
    while todo:
        path = todo.pop()
        if path not in seen:
            seen.add(path)
            todo.extend(imported_files(path) - seen)
    return {path for path in seen if _runs_code(path)}


def test_every_test_of_the_loops_code_is_in_the_standard_suite():
    loop = loop_files()
    listed = set(run_validation_tests.VALIDATION_TESTS)
    missing = sorted(
        str(path.relative_to(REPO))
        for path in (REPO / "tests").rglob("test_*.py")
        if (imported_files(path) | named_scripts(path)) & loop
        and str(path.relative_to(REPO)) not in listed
    )
    assert not missing, (
        "add these to scripts/run_validation_tests.py VALIDATION_TESTS: "
        + ", ".join(missing)
    )


def test_every_script_the_loops_code_names_is_an_entry_point_or_named_only():
    loop = loop_files()
    named = {
        str(path.relative_to(REPO))
        for path in set().union(*(named_scripts(path) for path in loop)) - loop
    }
    assert not named - NAMED_NOT_RUN, (
        "the loop's code names these by path: add each to ENTRY_POINTS if it runs "
        "it, else to NAMED_NOT_RUN: " + ", ".join(sorted(named - NAMED_NOT_RUN))
    )
    assert not NAMED_NOT_RUN - named, sorted(NAMED_NOT_RUN - named)


def test_the_entry_points_exist_and_reach_the_loops_modules():
    for entry in ENTRY_POINTS:
        assert (REPO / entry).is_file(), entry
    loop = {str(path.relative_to(REPO)) for path in loop_files()}
    for module in (
        "scripts/training/promotion.py",
        "scripts/process_supervisor.py",
        "src/vesuvius_autoresearch/core/vesuvius_loader.py",
        "src/vesuvius_autoresearch/core/frangi_torch.py",
        "src/vesuvius_autoresearch/detector/metrics.py",
        "src/vesuvius_autoresearch/fibers/detection.py",
        "vesuvius_model.py",
        "scripts/validate_prize_artifact.py",
    ):
        assert module in loop, module
    # Loaded on the way to detector.metrics, not run.
    assert "src/vesuvius_autoresearch/detector/infer.py" not in loop


def test_the_standard_suite_names_only_existing_modules():
    names = run_validation_tests.VALIDATION_TESTS
    assert not [name for name in names if not (REPO / name).is_file()]
    assert len(set(names)) == len(names)


def test_the_guard_reads_the_ways_tests_import(tmp_path):
    src = REPO / "src" / "vesuvius_autoresearch"
    cases = {
        "import train\n": REPO / "scripts/training/train.py",
        "from train import ExperimentConfig\n": REPO / "scripts/training/train.py",
        "from scripts.training.train import train\n": REPO
        / "scripts/training/train.py",
        "from scripts.inference import predict\n": REPO
        / "scripts/inference/predict.py",
        "from scripts import loop_control\n": REPO / "scripts/loop_control.py",
        "import run_autoresearch_loop as loop\n": REPO / "run_autoresearch_loop.py",
        "def f():\n    from vesuvius_autoresearch.core import frangi_torch\n": src
        / "core/frangi_torch.py",
        "from vesuvius_autoresearch.fibers import detect_ridges\n": src
        / "fibers/__init__.py",
        "from vesuvius_autoresearch.fibers import trace\n": src / "fibers/trace.py",
    }
    for source, expected in cases.items():
        path = tmp_path / "test_case.py"
        path.write_text(source)
        assert imported_files(path) == {expected}, source
    path.write_text("import numpy\nimport trainer\n")
    assert imported_files(path) == set()


def test_the_guard_reads_the_scripts_a_file_names(tmp_path):
    cases = {
        'RUNNER = REPO / "scripts/training/run_noise_probe.py"\n': {
            REPO / "scripts/training/run_noise_probe.py"
        },
        'path = ROOT / "scripts" / "inference" / "launch_neural_tracing.py"\n': {
            REPO / "scripts/inference/launch_neural_tracing.py"
        },
        'glob("*.py"); "no_such_script.py"\n': set(),
        # Named by src/vesuvius_autoresearch/core/patch_catalog.py; not ours.
        'VILLA = "villa/vesuvius/src/vesuvius/models/datasets/find_valid_patches.py"\n': set(),
    }
    for source, expected in cases.items():
        path = tmp_path / "test_case.py"
        path.write_text(source)
        assert named_scripts(path) == expected, source
    outside = tmp_path / "outside.py"
    outside.write_text("")
    path.write_text(f'"{outside}"\n')
    assert named_scripts(path) == set()
