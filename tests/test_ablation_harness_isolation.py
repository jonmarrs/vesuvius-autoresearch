"""scripts/ablate_scroll_augmentations.py runs its cells as experiment runs.

It used to train each cell as a loop cycle in the main checkout: a run could
promote into best_model.pt and append to the loop's logs, and the harness
copied a backup of best_model.pt back afterwards, over any promotion the loop
had made meanwhile. See docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-15_OPERATOR_SCRIPTS.md.
"""

import json
import sys
from pathlib import Path

import scripts.ablate_scroll_augmentations as ablation
from scripts.training.config import ExperimentConfig


def _project(tmp_path, monkeypatch, loop_pid=None):
    # main() chdirs to PROJECT_ROOT; monkeypatch puts the cwd back afterwards.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ablation, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ablation, "running_pid", lambda repo: loop_pid)
    ExperimentConfig().save(tmp_path / "config.json")
    (tmp_path / "best_model.pt").write_bytes(b"incumbent")
    (tmp_path / "run_result.json").write_text(json.dumps({"val_bpb": 9.0}))
    argv = ["ablate", "--seeds", "1", "--conditions", "baseline", "squeeze"]
    monkeypatch.setattr(sys, "argv", argv)


def test_the_ablation_leaves_the_loops_files_alone(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    seen = []

    def run(cfg_path, seed, budget, log_path):
        cfg = ExperimentConfig.load(cfg_path)
        seen.append((cfg.checkpoint_out, (tmp_path / "run_result.json").exists()))
        Path(cfg.checkpoint_out).write_bytes(b"candidate")  # train.py's write
        return {"status": "OK", "elapsed_s": 1.0, "val_bpb": 0.5}

    monkeypatch.setattr(ablation, "_run_one", run)
    assert ablation.main() == 0
    assert len(seen) == 2
    # Each run is an experiment run, and starts without the previous result.
    assert all(out and out.endswith(".pt") and not stale for out, stale in seen)
    assert (tmp_path / "best_model.pt").read_bytes() == b"incumbent"
    assert not list(tmp_path.glob("best_model.pt.*"))
    assert not list((tmp_path / "reports" / "ablation_logs").glob("*.pt"))


def test_the_ablation_will_not_run_beside_the_loop(tmp_path, monkeypatch, capsys):
    _project(tmp_path, monkeypatch, loop_pid=4321)
    monkeypatch.setattr(
        ablation, "_run_one", lambda *a: (_ for _ in ()).throw(AssertionError("ran"))
    )
    assert ablation.main() == 1
    assert "loop (PID 4321) runs in this checkout" in capsys.readouterr().err
