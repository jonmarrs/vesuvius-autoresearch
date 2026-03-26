import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

def generate_atlas():
    print("Generating Training Data Atlas (Low-Res Overview)...")
    
    labeled_dirs = []
    for d in sorted(os.listdir('local_data')):
        labels_path = os.path.join('local_data', d, 'inklabels.png')
        if os.path.exists(labels_path):
            # Check if it's a valid image and not an HTML error
            try:
                with Image.open(labels_path) as img:
                    img.verify()
                labeled_dirs.append((d, labels_path))
            except:
                print(f"Skipping invalid image: {labels_path}")
            
    if not labeled_dirs:
        print("No valid labeled data found to atlas.")
        return

    num_frags = len(labeled_dirs)
    cols = 3
    rows = (num_frags + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
    if num_frags == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for i, (name, path) in enumerate(labeled_dirs):
        img = Image.open(path)
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Downsample significantly for high-level overview
        img.thumbnail((1024, 1024))
        
        axes[i].imshow(np.array(img))
        
        # Check for mask
        mask_path = os.path.join('local_data', name, 'mask.png')
        has_mask = "✓ Mask" if os.path.exists(mask_path) else "No Mask"
        
        axes[i].set_title(f"Fragment: {name}\n{has_mask}", fontsize=12, fontweight='bold')
        axes[i].axis('off')
        
    # Hide unused axes
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')
        
    plt.suptitle("Vesuvius Training Data Atlas: Labeled Segments Overview", fontsize=20, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    os.makedirs('reports/figures', exist_ok=True)
    plt.savefig('reports/figures/training_data_atlas.png', dpi=150)
    plt.savefig('reports/figures/training_data_atlas.svg')
    print("Atlas saved to reports/figures/training_data_atlas.png and .svg")
    plt.close()

if __name__ == "__main__":
    Image.MAX_IMAGE_PIXELS = None
    generate_atlas()
