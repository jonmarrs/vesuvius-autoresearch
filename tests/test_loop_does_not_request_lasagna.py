"""The loop must not request the lasagna warp while it cannot run.

villa's uint8 kernel takes CUDA tensors and the loader reads patches on the CPU,
so strict validation reads refuse the warp and a cycle that requests it fails
before training (finding 86's correction). It never ran in any logged run.
"""

import json
from pathlib import Path

import run_autoresearch_loop as loop

REPO = Path(__file__).resolve().parents[1]


def test_config_does_not_request_the_warp():
    assert json.loads((REPO / "config.json").read_text())["use_lasagna"] is False


def test_the_loop_never_samples_the_warp():
    values = [t["vals"] for t in loop.tweak_templates if t["attr"] == "use_lasagna"]
    assert values == [[False]]
