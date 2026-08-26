"""Betti-Matching topology loss -- RETIRED, and it never worked.

This module wrapped villa's Betti-Matching-3D C++ extension as a training
loss. It was wired into ``scripts/training/train.py`` behind
``config.use_betti_loss`` (default False) and, as far as the config history
shows, never enabled. Two independent defects mean it could not have helped
if it had been:

1. **The extension call was wrong.** It passed the output of
   ``compute_barcode`` into ``compute_matching``, which takes raw ndarrays,
   not ``BarcodeResult`` objects. Every forward pass raised ``TypeError``.
   The original code carried the comment "the extension likely expects a
   specific function signature", which is where the guess is recorded.

2. **It had no gradient, and fixing (1) would not give it one.** The loss was
   rebuilt from a numpy scalar as ``torch.tensor(..., requires_grad=True)``.
   That fabricates a fresh leaf tensor; it does not connect to ``pred``. The
   backward pass would have reached this term and found nothing upstream, so
   it would have contributed exactly zero to the model while appearing in the
   loss printout as a topology term that was doing work. Defect 1 is loud;
   defect 2 is the dangerous one, and it would have survived a naive fix.

``scripts/cldice_loss.py`` is the replacement and predates this note: soft
clDice targets centerline overlap -- the same notion villa's centerline_dice
gate measures -- through a differentiable soft-skeletonization, so gradients
actually reach the model. Use ``config.use_cldice``.

The class is kept, raising, so that old configs and imports fail with an
explanation instead of a ``TypeError`` from a C++ binding.
"""

import torch.nn as nn

RETIRED_MESSAGE = (
    "BettiLoss is retired and never functioned: it called the Betti-Matching "
    "extension with the wrong argument types, and its output carried no "
    "gradient to the model, so enabling it would have added a term worth "
    "exactly zero. Use config.use_cldice (scripts/cldice_loss.py) instead, "
    "which is differentiable. See the module docstring for details."
)


class BettiLoss(nn.Module):
    def __init__(self, weight=1.0):
        raise NotImplementedError(RETIRED_MESSAGE)
