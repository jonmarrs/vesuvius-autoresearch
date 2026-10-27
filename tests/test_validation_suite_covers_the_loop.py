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
scripts/inference/launch_neural_tracing.py (with --neural-tracing), and the noise
probe its runner. They are entry points too, and a test that loads a script by its
file name, as tests/test_villa_baselines_launchers.py does, tests it. That file
had never been listed (2026-10-22), because the guard saw only imports. Every
other script the loop's code names by path, it only describes or writes into a
command for a person; NAMED_NOT_RUN lists each with the file that names it, so a
file that starts to run one is seen. The names are read from string literals: a
launch through `-m`, or a path split inside a directory name, is not seen. None
of the loop's launches is built that way (2026-10-22).
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

# Scripts the loop's code names by path but does not run, by the file naming
# them: reports that describe viewers and tools, the action matrix's launchers,
# and the commands the lasagna worklist writes for a person to run.
NAMED_NOT_RUN = {
    # Recognized as a lock owner; the controller does not launch promotions.
    "scripts/loop_control.py": {"scripts/promote_loop_candidate.py"},
    "scripts/build_lasagna_fiber_worklist.py": {
        "scripts/compute_structure_tensors.py",
        "scripts/crop_candidate_zarr.py",
    },
    "scripts/build_villa_component_coverage.py": {
        "scripts/autoresearch_thaumato_solver.py",
        "scripts/labeling/generate_fiber_labels.py",
        "scripts/launch_crackle_viewer.py",
        "scripts/launch_thaumato.py",
        "scripts/launch_vc3d.py",
        "scripts/smoke_test_villa_optimized_inference.py",
        "tests/test_import.py",
        "v3_training/trainer.py",
    },
    "scripts/build_villa_prize_action_matrix.py": {
        "scripts/smoke_test_villa_optimized_inference.py",
        "scripts/training/launch_finetune_lejepa.py",
        "scripts/training/launch_gp_winner.py",
        "scripts/training/launch_mutex.py",
    },
    "scripts/build_villa_review_manifest.py": {
        "scripts/launch_crackle_viewer.py",
        "scripts/launch_vc3d.py",
    },
    "scripts/build_volume_cartographer_readiness.py": {"scripts/launch_vc3d.py"},
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
        try:  # a name too long to be a file raises
            if "/" in name:
                candidates = [(REPO / name).resolve()]
            else:
                candidates = [c.resolve() for c in (REPO / "scripts").rglob(name)]
            candidates = [c for c in candidates if c.is_file()]
        except OSError:
            continue
        for candidate in candidates:
            if candidate.is_relative_to(REPO):
                if candidate.relative_to(REPO).parts[0] != "villa":
                    found.add(candidate)
    return found


def loop_tests(loop, tests):
    """The tests that import the loop's code or name one of its files."""
    return {
        test for test in tests if (imported_files(test) | named_scripts(test)) & loop
    }


def names_outside(loop):
    """{loop file: the scripts outside the loop's code that it names by path}."""
    named = {}
    for path in loop:
        scripts = named_scripts(path) - loop
        if scripts:
            named[str(path.relative_to(REPO))] = {
                str(script.relative_to(REPO)) for script in scripts
            }
    return named


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
        for path in loop_tests(loop, (REPO / "tests").rglob("test_*.py"))
        if str(path.relative_to(REPO)) not in listed
    )
    assert not missing, (
        "add these to scripts/run_validation_tests.py VALIDATION_TESTS: "
        + ", ".join(missing)
    )


def test_every_script_the_loops_code_names_is_an_entry_point_or_named_only():
    named = names_outside(loop_files())
    assert named == NAMED_NOT_RUN, (
        "a script the loop's code names by path is neither an entry point nor in "
        "NAMED_NOT_RUN (add it to ENTRY_POINTS if the file runs it), or an entry "
        f"there is no longer named. Named now: {named}"
    )


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


def _repo(tmp_path, monkeypatch, *files):
    """A repository of empty files in tmp_path/repo, which the guard reads as REPO."""
    repo = (tmp_path / "repo").resolve()
    for name in files:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("")
    monkeypatch.setitem(globals(), "REPO", repo)
    return repo


def _source(tmp_path, text):
    path = tmp_path / f"case_{abs(hash(text))}.py"
    path.write_text(text)
    return path


def test_the_guard_reads_the_scripts_a_file_names(tmp_path, monkeypatch):
    runner, launcher, theirs = (
        "scripts/training/runner.py",
        "scripts/inference/x.py",
        "villa/v.py",
    )
    repo = _repo(tmp_path, monkeypatch, runner, launcher, theirs)
    (tmp_path / "outside.py").write_text("")
    cases = {
        f'RUNNER = REPO / "{runner}"\n': {repo / runner},
        'path = ROOT / "scripts" / "inference" / "x.py"\n': {repo / launcher},
        'glob("*.py"); "no_such_script.py"\n': set(),
        f'"{theirs}"\n': set(),
        '"../outside.py"; "scripts/../../outside.py"\n': set(),
        f'"{tmp_path / "outside.py"}"\n': set(),
        f'"{"a" * 300}.py"\n': set(),
    }
    for text, expected in cases.items():
        assert named_scripts(_source(tmp_path, text)) == expected, text


def test_the_guard_selects_by_imports_and_by_names(tmp_path, monkeypatch):
    repo = _repo(
        tmp_path, monkeypatch, "scripts/chain.py", "scripts/x.py", "scripts/report.py"
    )
    (repo / "scripts/chain.py").write_text('RUN = "scripts/x.py"; SEE = "report.py"\n')
    loop = {repo / "scripts/chain.py", repo / "scripts/x.py"}
    naming = _source(tmp_path, 'LAUNCHER = "x.py"\n')
    unrelated = _source(tmp_path, "import numpy\n")
    assert loop_tests(loop, [naming, unrelated]) == {naming}
    assert names_outside(loop) == {"scripts/chain.py": {"scripts/report.py"}}
