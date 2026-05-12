import os
import torch
import numpy as np
import argparse
from tqdm import tqdm

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
                
                # Forward pass with Multi-task heads
                out_ink, qc = self.model(x, return_qc=True)
                probs = torch.sigmoid(out_ink)
                
                # Metric 1: Prediction Entropy (ambiguity)
                entropy = calculate_entropy(probs).mean(dim=(1, 2, 3))
                
                # Metric 2: QC Confidence (model's own estimate of quality)
                # Lower QC value = higher uncertainty
                qc_uncertainty = 1.0 - torch.sigmoid(qc).squeeze()
                
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--volume", type=str, required=True)
    parser.add_argument("--n_samples", type=int, default=10)
    args = parser.parse_args()

    # Setup would go here: Load model, setup dataset/dataloader
    print(f"Active Learning Sampler: Initialized for {args.volume}")
    print("Ready to identify regions for SAM2-assisted annotation.")

if __name__ == "__main__":
    main()
