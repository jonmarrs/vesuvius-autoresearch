# PHerc. 343 kill test

The scripts that rebuilt the published PHerc. 343 First Letters image on this machine on 2026-11-10. Result:
`reports/first_letters_343_reproduction.md`. The recipe is
[Nieuwlaar/pherc343-first-letters](https://github.com/Nieuwlaar/pherc343-first-letters) at commit `e8370f1f`; none
of its code is copied here. These scripts call it from a clone.

They are the files that ran, reformatted afterwards, with one `strict=True` added to a `zip` in
`compare_image.py`. Both comparison files and the record were regenerated from the committed versions and are
byte-identical to the ones from the run.

Paths are this host's. `B` in each shell script is the run directory. It holds the clone (`src/repo`), the
environment (`venv`), the checkpoints (`ckpt`), the renderer's home (`vchome`) and the outputs (`work`).

| Order | Script | What it does |
|---|---|---|
| 1 | `setup_env.sh` | builds the ink environment from villa `0fb38c45` and downloads the four checkpoints with the recipe's sha256-checking script |
| 2 | `check_ckpt_safe.py` | loads each checkpoint with `weights_only=True` |
| 3 | the recipe's `build_concat.py`, then `sha256sum -c` | joins the two published windings; not wrapped here |
| 4 | `render_66.sh` | renders 66 layers from CT streamed off the public bucket, in the `vc-render:sampler-75c79ac5f` image |
| 5 | `check_render.py` | compares the render with the hashes in the published sidecar |
| 6 | the recipe's `pad_render.py` | writes the zero-padded copy; not wrapped here |
| 7 | `stage_a_ink.sh` | runs the four models at depth +1 on both renders. Stop the training loop first |
| 8 | `stage_a_image.sh` | merges the maps and builds the image twice: with the published statistics (`stats_from_sidecar.py`) and without |
| 9 | `compare_image.py` | compares each image with the published one |
| 10 | `make_record.py` | assembles the JSON record from the run's logs and comparison files |

The recipe's code is MIT. Its meshes and images are CC BY-NC 4.0, and none is committed here.
