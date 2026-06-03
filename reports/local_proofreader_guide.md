# Active Learning: Local Proofreader Guidance

To complete the Active Learning cycle initiated during the Night Shift, you need to review the patches identified by the model as high-uncertainty or high-value. Since this requires an interactive GUI (Napari), please follow these steps on your local machine:

### 1. Prerequisites
Ensure your local machine is set up with the same environment as the Vesuvius Autoresearch repo.
```bash
# Ensure submodule and dependencies are synced
git submodule update --init --recursive
uv pip install -e .
# Ensure villa submodule dependencies are ready
cd villa
uv pip install -e .
```

### 2. Launch the Proofreader
Run the following command, pointing to the volume and the predictions you generated during the Night Shift:
```bash
uv run scripts/inference/launch_proofreader.py \
    --volume local_data/PHercParis2Fr143/surface_volume.zarr \
    --predictions predictions/pred_10_1000_1000_64x64_ink.zarr
```

### 3. Review Process
1.  **Napari Interface:** The tool will open a Napari window showing the CT data and predicted ink mask.
2.  **Interaction:**
    *   **Press 'a'**: Approve the patch (adds it to `local_data/Proofread_Patches/`).
    *   **Press 'spacebar'**: Skip this patch.
3.  **Completion:** Once reviewed, the approved patches in `local_data/Proofread_Patches/` will be automatically integrated into the dataset by the next iteration of the training loop if placed in the designated training paths.

Please let me know if you encounter any environment issues when launching the proofreader locally.
