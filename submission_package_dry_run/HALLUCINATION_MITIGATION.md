# Hallucination Mitigation Note

## Overview
To ensure the text signals detected by our model are real carbonized ink and not machine learning hallucinations, we have implemented the following mitigations:

1. **Window Size Constraint**: Our models strictly adhere to a maximum window size of 64x64 pixels at 8 µm resolution (0.5x0.5 mm). This forces the model to make highly local geometric predictions, preventing it from memorizing long-range structural features or letter shapes from the training set.
2. **Zero Overlap Guarantee**: As shown in `train_predict_mask.png`, the region used for prediction has zero overlap with any annotated training data.
3. **Topological Evaluation Metrics**: Our model was selected via the `bountyhunter` autonomous loop using the official `centerline_dice` and `skeleton_distance_length` metrics (from the `villa` suite). These metrics prioritize contiguous, topologically sound structures over scattered noise.
4. **Ensemble Voting (Sprint 012)**: The final output image is generated through a "Voter Swarm" consensus of multiple architectures (Gated UNet and ResEnc UNet), eliminating artifact-based hallucinations that are specific to a single model's inductive biases.
5. **Auxiliary Task Supervision (Sprint 023)**: The network was co-trained to predict the local 3D Structure Tensor, ensuring the features it extracts are deeply anchored to the actual physical geometry of the papyrus surface rather than visual noise.
