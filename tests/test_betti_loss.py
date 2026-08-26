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

from scripts.betti_loss_module import RETIRED_MESSAGE, BettiLoss


class TestBettiLoss(unittest.TestCase):
    def test_construction_refuses_with_an_explanation(self):
        with self.assertRaises(NotImplementedError) as ctx:
            BettiLoss(weight=1.0)
        self.assertIn("cldice", str(ctx.exception).lower())

    def test_the_message_names_both_defects(self):
        """The retirement is only useful if it says why, so a future reader does
        not 'fix' the visible TypeError and re-enable a zero-gradient term."""
        msg = RETIRED_MESSAGE.lower()
        self.assertIn("gradient", msg)
        self.assertIn("argument types", msg)


if __name__ == "__main__":
    unittest.main()
