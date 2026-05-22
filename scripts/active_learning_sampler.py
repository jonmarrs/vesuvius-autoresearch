import os
import torch
import numpy as np
import argparse
from tqdm import tqdm
import json
from datetime import datetime

# Local imports
from model_wrappers import build_inference_model
from vesuvius_loader import VesuviusLabeledDataset
from torch.utils.data import DataLoader

def calculate_entropy(probs):
    """Calculate pixel-wise entropy: -p*log(p) - (1-p)*log(1-p)"""
    eps = 1e-8
    entropy = -probs * torch.log(probs + eps) - (1 - probs) * torch.log(1 - probs + eps)
    return entropy

class ActiveLearningSampler:
    """
    Identifies high-uncertainty regions for SAM2-assisted human-in-the-loop cleaning.
    """
    def __init__(self, model, device='cuda'):
        self.model = model
        self.device = device
        self.model.to(device)
        self.model.eval()

    def sample_uncertain_regions(self, dataloader, n_samples=10):
        uncertainties = []
        all_coords = []
        
        print(f"Sampling {n_samples} high-uncertainty regions...")
        
        with torch.no_grad():
            for i, (x, _, coords) in enumerate(tqdm(dataloader)):
                x = x.to(self.device)
                
                # Forward pass - support multi-output
                outputs = self.model(x, return_qc=True)
                if isinstance(outputs, tuple):
                    out_ink, qc = outputs[0], outputs[1]
                else:
                    out_ink = outputs
                    # Dummy QC if model doesn't have it
                    qc = torch.ones((x.shape[0], 1), device=self.device)

                probs = torch.sigmoid(out_ink)
                
                # Metric 1: Prediction Entropy (ambiguity)
                # out_ink might be 4D [B, 1, H, W] or 5D [B, 1, Z, H, W]
                # dataset returns [B, 1, Z, H, W] usually
                entropy = calculate_entropy(probs).mean(dim=tuple(range(1, probs.ndim)))
                
                # Metric 2: QC Confidence (model's own estimate of quality)
                # Lower QC value = higher uncertainty
                qc_uncertainty = 1.0 - torch.sigmoid(qc).squeeze()
                if qc_uncertainty.ndim == 0:
                    qc_uncertainty = qc_uncertainty.unsqueeze(0)
                
                # Combined Uncertainty Score
                score = 0.7 * entropy + 0.3 * qc_uncertainty
                
                uncertainties.append(score.cpu().numpy())
                all_coords.append(coords.cpu().numpy())
                
                if i * dataloader.batch_size > 1000: # Limit search for speed
                    break
        
        uncertainties = np.concatenate(uncertainties)
        all_coords = np.concatenate(all_coords)
        
        # Get indices of top N uncertain regions
        top_indices = np.argsort(uncertainties)[-n_samples:][::-1]
        
        return all_coords[top_indices], uncertainties[top_indices]

def identify_uncertain_patches(probs, threshold=0.2):
    """
    Identifies high-entropy (uncertain) regions in a probability map.
    probs: (H, W) or (C, H, W) tensor
    """
    if isinstance(probs, np.ndarray):
        probs = torch.from_numpy(probs)
    
    entropy = calculate_entropy(probs)
    if entropy.dim() == 3:
        entropy = entropy.mean(dim=0)
    
    # Normalize entropy to [0, 1]
    max_entropy = -0.5 * np.log(0.5) - (1 - 0.5) * np.log(1 - 0.5)
    entropy /= max_entropy
    
    return (entropy > threshold).float()

def export_for_proofreader(mask, output_path):
    """
    Exports a binary mask to a Zarr volume for the proofreader tool.
    """
    import zarr
    if isinstance(mask, torch.Tensor):
        mask = mask.cpu().numpy()
    
    # Ensure 3D [Z, H, W]
    if mask.ndim == 2:
        mask = mask[np.newaxis, ...]
    
    # If 4D [C, Z, H, W], take first channel
    if mask.ndim == 4:
        mask = mask[0]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    z = zarr.open(output_path, mode='w', shape=mask.shape, chunks=(1, 64, 64), dtype='f4')
    z[:] = mask
    print(f"Exported uncertainty mask for proofreading: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Active Learning Sampler for Vesuvius Autoresearch")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to best_model.pt")
    parser.add_argument("--volume", type=str, required=True, help="URI to the Zarr volume")
    parser.add_argument("--labels", type=str, default=None, help="Optional path to labels (if not in volume dir)")
    parser.add_argument("--n_samples", type=int, default=20, help="Number of uncertain patches to sample")
    parser.add_argument("--output", type=str, default="reports/active_learning_queue.json", help="Path to export review queue")
    args = parser.parse_args()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Active Learning Sampler: Running on {device}")

    # 1. Load Checkpoint Metadata
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    config_dict = checkpoint.get("config", {})
    
    # Architecture defining fields
    arch_kwargs = {
        "architecture": config_dict.get("architecture", "gated_unet"),
        "patch_size": config_dict.get("patch_size", 64),
        "num_layers": config_dict.get("num_layers", 16),
        "base_feat": config_dict.get("base_feat", 64),
        "num_blocks": config_dict.get("num_blocks", 16),
        "num_heads": config_dict.get("num_heads", 8),
        "dropout": config_dict.get("dropout", 0.0),
        "use_ridges": config_dict.get("use_ridges", False),
        "multi_task_heads": config_dict.get("multi_task_heads", False),
    }
    
    print(f"Instantiating model: {arch_kwargs['architecture']}...")
    model = build_inference_model(**arch_kwargs)
    model.load_state_dict(checkpoint["model_state_dict"])
    
    sampler = ActiveLearningSampler(model, device=device)

    # 2. Setup Dataset
    labels_path = args.labels
    if labels_path is None:
        # Standard location for Fragments
        labels_path = os.path.join(os.path.dirname(args.volume), "inklabels.png")
        if not os.path.exists(labels_path):
            # Fallback to local_data structure
            frag_name = os.path.basename(os.path.dirname(args.volume))
            labels_path = f"local_data/{frag_name}/inklabels.png"

    print(f"Using labels from: {labels_path}")
    
    dataset = VesuviusLabeledDataset(
        args.volume,
        labels_path,
        patch_size=arch_kwargs["patch_size"],
        num_layers=arch_kwargs["num_layers"],
        require_ink=False
    )
    
    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)

    # 3. Sample Uncertain Regions
    coords, scores = sampler.sample_uncertain_regions(dataloader, n_samples=args.n_samples)

    # 4. Export Review Queue
    queue = []
    for i in range(len(coords)):
        queue.append({
            "rank": i + 1,
            "z_y_x": coords[i].tolist(),
            "uncertainty_score": float(scores[i]),
            "status": "pending_manual_review"
        })

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "checkpoint": args.checkpoint,
            "volume": args.volume,
            "queue": queue
        }, f, indent=4)

    print(f"\nSuccess: Exported {len(queue)} patches to review queue: {args.output}")
    print("These regions are ready for interactive cleaning via vc_proofreader.")

if __name__ == "__main__":
    main()
