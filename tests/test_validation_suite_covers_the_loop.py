"""The standard suite runs every test of the code the loop runs.

scripts/run_validation_tests.py lists its modules by hand, and tests added since
were left out of it: on 2026-10-16, 28 modules importing train.py, the loop, the
inference scripts, the core library or the evidence chain (the promotion
criterion's, the prize gates', the Frangi target's, the loader workers') were
outside the list that reviews validate against.
"""

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import run_validation_tests  # noqa: E402

# Modules the loop, its training run, its inference and its evidence chain run.
LOOP_CODE = (
    "train",
    "run_autoresearch_loop",
    "loop_control",
    "scripts.training",
    "scripts.loop_control",
    "scripts.inference",
    "scripts.production_predict",
    "vesuvius_autoresearch.core",
    "scripts.validate_prize_artifact",
    "scripts.run_villa_prize_evidence_chain",
    "scripts.rank_scroll23_candidates",
    "scripts.run_post_sprint_villa_handoff",
    "scripts.summarize_villa_evidence_preflight",
    "scripts.plan_villa_prize_opportunities",
    "scripts.review_villa_pin",
    "scripts.build_villa_prize_action_matrix",
    "scripts.build_villa_review_manifest",
    "scripts.build_villa_component_coverage",
    "scripts.build_volume_cartographer_readiness",
)


def _imported_modules(path):
    names = set()
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def _runs_loop_code(path):
    return any(
        name == code or name.startswith(code + ".")
        for name in _imported_modules(path)
        for code in LOOP_CODE
    )


def test_every_test_of_the_loops_code_is_in_the_standard_suite():
    listed = set(run_validation_tests.VALIDATION_TESTS)
    missing = sorted(
        str(path.relative_to(REPO))
        for path in (REPO / "tests").glob("test_*.py")
        if _runs_loop_code(path) and str(path.relative_to(REPO)) not in listed
    )
    assert not missing, (
        "add these to scripts/run_validation_tests.py VALIDATION_TESTS: "
        + ", ".join(missing)
    )


def test_the_standard_suite_names_only_existing_modules():
    absent = [
        name
        for name in run_validation_tests.VALIDATION_TESTS
        if not (REPO / name).is_file()
    ]
    assert not absent
    assert len(set(run_validation_tests.VALIDATION_TESTS)) == len(
        run_validation_tests.VALIDATION_TESTS
    )


def test_the_guard_sees_the_ways_tests_import_the_loops_code(tmp_path):
    cases = {
        "import train\n": True,
        "from train import ExperimentConfig\n": True,
        "from scripts.training.train import train\n": True,
        "from scripts.inference import predict\n": True,
        "from vesuvius_autoresearch.core.inference_constants import X\n": True,
        "import run_autoresearch_loop as loop\n": True,
        "from scripts import loop_control\n": True,
        "import trainer\n": False,
        "from vesuvius_autoresearch.fibers import trace\n": False,
        "from scripts.analyse_outer_floor import main\n": False,
    }
    for source, expected in cases.items():
        path = tmp_path / "test_case.py"
        path.write_text(source)
        assert _runs_loop_code(path) is expected, source
