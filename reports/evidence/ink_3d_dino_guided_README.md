---
license: mit
tags:
- arxiv:2606.29085
- vesuvius-challenge
- herculaneum
- papyrology
- computed-tomography
- ink-detection
- 3d-segmentation
- dino-guided
- self-distillation
- volumetric-imaging
pipeline_tag: image-segmentation
---

# PHerc. Paris 4 — volumetric 3D ink segmentation (DINO-guided, self-distilled)

Segments ink **directly in 3D** in micro-CT of **PHerc. Paris 4**, where ink is
volumetrically visible. This model provides the independent volumetric validation
of surface-conditioned ink recovery reported in *"Complete virtual unwrapping and
reading of a rolled Herculaneum papyrus"* (Angelotti et al., **arXiv:2606.29085**, 2026).

## Model details

| | |
|---|---|
| Architecture | `vesuvius` `NetworkFromConfig` nnU-Net-style **3D residual-encoder U-Net** (~142 M params), single sigmoid ink head |
| Input | 1-channel CT, **256³** patches, percentile min-max normalisation, full-3D mode (projection half-thickness 3 voxels) |
| Optimisation | SGD + Nesterov, cosine LR (base 1e-2, warmup 5000), bf16, Dice+BCE with 0.1 label smoothing, weight EMA |
| This checkpoint | step **78,000** · W&B run `4b07qv8p` (`ps256_3d_bcedice_dinoguided_paris4_v3_fullsup`) |
| Weights | `model` (raw) and `ema_model` (**EMA — recommended for inference**) |

## DINO-guided supervision + self-distillation

Trained in stages: **(1)** teacher on 8-scroll surface-conditioned ink labels
(PHerc. Paris 4, 0139, 0500P2, 0814, 0841, 1667, MAN5, 9B); **(2)** a DINO-guided
student using dense ink-likeness from the 3D DINOv2 representation model
[`scrollprize/dinovol_v2_ps8_with_paris4_352500`](https://huggingface.co/scrollprize/dinovol_v2_ps8_with_paris4_352500);
**(3)** + background masking; **(4)** self-distillation. DINO guidance compares each
864-D patch token to a **reference ink embedding** (`avg_ref_embedding.npy`, the
L2-normalised mean of 256 expert-clicked tokens stored in `recorded_embeddings*.npy`)
at threshold τ = 0.5. Full configuration is in **Supplementary Table 4** of the paper.

## Files

- `ckpt_78k_fullsup.pth` — checkpoint with `model` + `ema_model` (use `ema_model` for inference). Training/inference config embedded under `config` and mirrored in `config.json`.
- `config.json` — training/inference configuration.
- `avg_ref_embedding.npy` — `(864,)` reference ink embedding for DINO guidance.
- `recorded_embeddings.npy`, `recorded_embeddings_2.npy` — `(128, 864)` each; the expert-clicked DINO tokens (256 total) the reference embedding is averaged from.

## How to load

```python
import torch, numpy as np
ck    = torch.load("ckpt_78k_fullsup.pth", map_location="cpu", weights_only=False)
state = ck["ema_model"]                    # recommended
cfg   = ck["config"]                       # == config.json
ref   = np.load("avg_ref_embedding.npy")   # (864,) reference ink embedding
# Build the network with the vesuvius package (NetworkFromConfig(cfg)), then load_state_dict(state)
```
The `vesuvius` package and inference code are in <https://github.com/ScrollPrize/villa>.

## Related models

- **3D representation (guidance):** [`scrollprize/dinovol_v2_ps8_with_paris4_352500`](https://huggingface.co/scrollprize/dinovol_v2_ps8_with_paris4_352500)
- **2D ink detector + label ablations:** [`pherc1667-ink-detection-ablation`](https://huggingface.co/collections/scrollprize/pherc1667-ink-detection-ablation-6a39e45202e6e7f9c76e692f) collection

## Links

- **Paper:** Angelotti et al., *Complete virtual unwrapping and reading of a rolled Herculaneum papyrus.* arXiv:2606.29085 (2026). <https://arxiv.org/abs/2606.29085>
- **Code:** <https://github.com/ScrollPrize/villa>
- **Data:** <https://scrollprize.org/data_browser> · ESRF: <https://cultural-heritage.esrf.fr/tomo>
- **Vesuvius Challenge:** <https://scrollprize.org>

## Citation

```bibtex
@misc{angelotti2026unwrapping,
  title         = {Complete virtual unwrapping and reading of a rolled Herculaneum papyrus},
  author        = {Angelotti, Giorgio and others},
  year          = {2026},
  eprint        = {2606.29085},
  archivePrefix = {arXiv},
  primaryClass  = {eess.IV},
  doi           = {10.48550/arXiv.2606.29085}
}
```

## License

**MIT** — released by the Vesuvius Challenge. The underlying tomographic data are
distributed under **CC BY-NC 4.0** (see the data links above).
