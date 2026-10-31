"""The loop must not sample a learning rate too small to change the incumbent in one cycle.

Each cycle warm-starts from best_model.pt and trains for 15 minutes. At lr 1e-5 that leaves the model almost as it
was: against the 10-27 incumbent its six cycles' val_f1 spread was 0.00004, against 0.0019 for all 161 cycles. The
replicate rule (scripts/training/replicate_rule.py) takes Student's t of a tweak's cycles minus the other tweaks' mean,
so only the tweak's own spread enters it, and a steady offset with no spread scores high: lr 1e-5 was promoted on
2026-10-29 on +0.0002 F1, which set every later cycle's lr to 1e-5. Against the next incumbent it was set to fire
again. Until the rule's test counts the comparison's spread too, the loop does not sample it.
"""

import run_autoresearch_loop as loop


def test_the_loop_never_samples_a_no_op_learning_rate():
    (lrs,) = [t["vals"] for t in loop.tweak_templates if t["attr"] == "lr"]
    assert min(lrs) >= 5e-5
