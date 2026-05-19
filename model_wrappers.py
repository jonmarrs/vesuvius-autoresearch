"""Shared model wrappers.

Previously `GenericMultiTaskWrapper` was duplicated in train.py and
predict.py with slight signature drift (the train.py version accepted an
optional `projector` arg). This module is the single canonical source so
train.py and predict.py can never get out of sync.

TODO(multi-task-heads): fiber/qc/st outputs from this wrapper are dummies
(re-use of the ink output or torch.zeros). With dummy outputs the
corresponding losses become zero-gradient constants — they inflate
reported total_loss without contributing supervision. resenc_unet's
good topology (May-5 skel_dist=1.0) came from ink BCE+Dice alone, so
the dummies are not actively harmful, but real heads would unlock
multi-task gains.
"""
import torch
import torch.nn as nn


class GenericMultiTaskWrapper(nn.Module):
    """Adapter that gives a single-headed backbone (e.g. ResEnc UNet)
    the multi-head forward signature train.py expects.

    Returns an ink_2d output for every call, plus optionally:
      - fiber: same 5D output as ink (dummy — re-uses ink tensor)
      - qc:    torch.zeros((B, 1))
      - proj:  Linear projection of pooled scalar (real, used for DINO-Lite)
      - st:    torch.zeros((B, 6, Z, H, W))
    """

    def __init__(self, model, projector=None):
        super().__init__()
        self.model = model
        if projector is not None:
            self.projector = projector
        else:
            self.projector = nn.Sequential(
                nn.AdaptiveAvgPool3d(1),
                nn.Flatten(),
                nn.Linear(1, 128),
            )

    def forward(self, x, return_fiber=False, return_qc=False, return_proj=False, return_st=False, **kwargs):
        out = self.model(x)
        if isinstance(out, (list, tuple)):
            out = out[0]
        if out.dim() == 5:
            ink_2d = torch.mean(out, dim=2)
        elif out.dim() == 2:
            ink_2d = out.view(out.shape[0], out.shape[1], 1, 1).expand(-1, -1, x.shape[3], x.shape[4])
        else:
            ink_2d = out

        results = [ink_2d]
        if return_fiber:
            results.append(out if out.dim() == 5 else out.unsqueeze(2))
        if return_qc:
            results.append(torch.zeros((x.shape[0], 1), device=x.device, dtype=ink_2d.dtype))
        if return_proj:
            proj_in = out if out.dim() == 5 else out.unsqueeze(2).unsqueeze(-1).unsqueeze(-1)
            results.append(self.projector(proj_in))
        if return_st:
            results.append(torch.zeros((x.shape[0], 6, *x.shape[2:]), device=x.device, dtype=ink_2d.dtype))
        return tuple(results) if len(results) > 1 else results[0]
