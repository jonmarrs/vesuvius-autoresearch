"""BettiLoss is retired; this pins the retirement rather than the old contract.

The previous test asserted `loss.item() == 0.0` and `loss.requires_grad`, with
the comment "Currently mocked to 0.0". Nothing was mocked -- the module called
the real C++ extension, which raised TypeError on every invocation, so the test
could not pass. Worse, the two properties it asserted were the bug: the loss
was zero because it was disconnected from `pred`, and `requires_grad` was True
only because the code fabricated a fresh leaf tensor. A test that had passed
would have been certifying a loss that trains nothing.
"""

import unittest

from scripts.betti_loss_module import BettiLoss


class TestBettiLoss(unittest.TestCase):
    def test_construction_refuses_with_an_explanation(self):
        with self.assertRaises(NotImplementedError) as ctx:
            BettiLoss(weight=1.0)
        self.assertIn("cldice", str(ctx.exception).lower())

    def test_train_py_refuses_before_the_epoch_loop(self):
        """The property that matters to a caller: a config with
        use_betti_loss=True fails at setup, not part-way through training. The
        earlier version of this test asserted the wording of a string constant
        against itself, which no production change could break."""
        import inspect

        import scripts.training.train as train

        src = inspect.getsource(train)
        construction = src.index("BettiLoss(weight=config.betti_loss_weight)")
        training_loop = src.index("    while True:")
        self.assertLess(construction, training_loop)


if __name__ == "__main__":
    unittest.main()
