# Source of the two files beside this one

Fetched 2026-10-04 from the public Hugging Face model repo `scrollprize/ink_3d_dino_guided` (MIT), revision
`73a79525466037432191284dfa237baf830c49ec` (lastModified 2026-08-05):

* `config.json` → `ink_3d_dino_guided_config.json`
* `README.md` (model card) → `ink_3d_dino_guided_README.md`

This checkpoint (step 78,000, W&B run `ps256_3d_bcedice_dinoguided_paris4_v3_fullsup`) is the model behind the
ink volume every label-based study here renders:
`PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr`.

What the config shows:
* `datasets[0].segments_path` = `/ephemeral/2d_ink_dataset/phercparis4`. villa's PHercParis4 ink dataset
  (`hf://buckets/scrollprize/datasets/ink/phercparis4`) is exactly the 8 segments that carry labels on the
  current frame.
* `force_full_supervision` = true.
* `dynamic_label.kind` = `self_distill`: targets come partly from the previous version's predictions.
* `full_3d.projection_half_thickness` = 3.0 voxels at 2.4 µm.

The model therefore trained on these segments. Agreement between its render and villa's labels there is
training-set agreement (finding 78).
