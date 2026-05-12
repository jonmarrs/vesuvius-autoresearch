import os
import sys
import numpy as np
import tifffile
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from scipy.ndimage import distance_transform_edt
from math import sqrt

# Add villa paths to imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
FIBER_TOOLS_PATH = os.path.join(PROJECT_ROOT, "villa/foundation/datasets/fibers-dataset")
sys.path.append(FIBER_TOOLS_PATH)

from tools import detect_vesselness

try:
    import webknossos as wk
    from webknossos import Annotation
except ImportError:
    print("webknossos not installed. Please install it to use this script.")
    sys.exit(1)

def classify_fiber_pca_on_voxels(voxel_coords, z_threshold=1./sqrt(2)):
    if voxel_coords.shape[0] < 2:
        return "horizontal"
    coords = voxel_coords.astype(np.float32)
    centroid = coords.mean(axis=0)
    coords_centered = coords - centroid
    cov = np.cov(coords_centered.T)
    if np.isnan(cov).any() or np.isinf(cov).any():
        return "horizontal"
    eigvals, eigvecs = np.linalg.eig(cov)
    idx = np.argsort(eigvals)[::-1]
    eigvecs = eigvecs[:, idx]
    principal_axis = eigvecs[:, 0]
    principal_axis /= (np.linalg.norm(principal_axis) + 1e-8)
    z_axis = np.array([1, 0, 0], dtype=float)
    cos_angle = abs(np.dot(principal_axis, z_axis))
    return "vertical" if cos_angle > z_threshold else "horizontal"

def interpolate_adaptive(start_pos, end_pos, curvature_threshold=0.1, max_recursion=100):
    segment_vector = end_pos - start_pos
    segment_length = np.linalg.norm(segment_vector)
    if max_recursion == 0 or segment_length < curvature_threshold:
        return [start_pos, end_pos]
    mid_pos = (start_pos + end_pos) / 2.0
    left_segment = interpolate_adaptive(start_pos, mid_pos, curvature_threshold, max_recursion - 1)
    right_segment = interpolate_adaptive(mid_pos, end_pos, curvature_threshold, max_recursion - 1)
    return left_segment[:-1] + right_segment

def fill_volume_for_tree(tree, output_shape, origins=(0, 0, 0)):
    temp_fiber = np.zeros(output_shape, dtype=np.uint8)
    origins = np.array(origins)
    for node1, node2 in tree.edges:
        node1_pos = np.array([node1.position.x, node1.position.y, node1.position.z])
        node2_pos = np.array([node2.position.x, node2.position.y, node2.position.z])
        interpolated_points = interpolate_adaptive(node1_pos, node2_pos)
        for p in interpolated_points:
            voxel_coords = (p - origins).astype(int)
            if np.all((0 <= voxel_coords) & (voxel_coords < output_shape)):
                temp_fiber[voxel_coords[2], voxel_coords[1], voxel_coords[0]] = 1
    return temp_fiber

def expand_and_vesselness(binary_volume, radius=3):
    binary_inverted = 1 - binary_volume
    edt = distance_transform_edt(binary_inverted)
    expanded_structure = (edt <= radius).astype(np.uint8)
    vessel = detect_vesselness(expanded_structure.astype(np.float32))
    combined = np.maximum(binary_volume, vessel)
    binned_data = (combined > 0.5).astype(np.uint8)
    return binned_data

def process_tree_worker(tree, output_shape, origins, radius):
    temp_fiber = fill_volume_for_tree(tree, output_shape, origins)
    processed_temp = expand_and_vesselness(temp_fiber, radius)
    fiber_voxels = np.argwhere(processed_temp > 0)
    orientation = classify_fiber_pca_on_voxels(fiber_voxels)
    accum_h = np.zeros(output_shape, dtype=np.uint16)
    accum_v = np.zeros(output_shape, dtype=np.uint16)
    if orientation == "vertical":
        accum_v += processed_temp.astype(np.uint16)
    else:
        accum_h += processed_temp.astype(np.uint16)
    return accum_h, accum_v

def voxelize_skeleton(annotation, output_shape, origins, radius=3, n_workers=None):
    all_trees = []
    for group in annotation.skeleton.groups:
        all_trees.extend(group.trees)
    all_trees.extend(annotation.skeleton.trees)
    accum_horizontal = np.zeros(output_shape, dtype=np.uint8)
    accum_vertical = np.zeros(output_shape, dtype=np.uint8)
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(process_tree_worker, tree, output_shape, origins, radius): tree for tree in all_trees}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing trees"):
            h, v = future.result()
            accum_horizontal = np.maximum(accum_horizontal, h)
            accum_vertical = np.maximum(accum_vertical, v)
    final_volume = np.zeros(output_shape, dtype=np.uint8)
    mask_mixed = (accum_horizontal > 0) & (accum_vertical > 0)
    final_volume[mask_mixed] = 3
    final_volume[(accum_horizontal > 0) & (accum_vertical == 0)] = 1
    final_volume[(accum_vertical > 0) & (accum_horizontal == 0)] = 2
    return final_volume

def main():
    nml_path = "villa/foundation/datasets/fibers-dataset/fibers_s5_06500z_02000y_04000x_500_v03.nml"
    output_dir = "local_data/fibers_dataset"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading annotation from {nml_path}...")
    annotation = Annotation.load(nml_path)
    
    # Coordinates from filename
    parts = os.path.basename(nml_path).split('_')
    z_start = int(parts[2][:-1])
    y_start = int(parts[3][:-1])
    x_start = int(parts[4][:-1])
    size = int(parts[5])
    
    print(f"Generating labels for Scroll 5 at ({z_start}, {y_start}, {x_start}) size {size}...")
    labels = voxelize_skeleton(
        annotation, 
        output_shape=(size, size, size), 
        origins=(x_start, y_start, z_start),
        radius=2,
        n_workers=4
    )
    
    label_path = os.path.join(output_dir, "labels.tif")
    tifffile.imwrite(label_path, labels)
    print(f"Labels saved to {label_path}")

if __name__ == "__main__":
    main()
