#!/usr/bin/env python3
import os
import subprocess
import time
import json
import random
import glob
import numpy as np
import shlex

def run_command(cmd, log_file):
    cmd_args = shlex.split(cmd) if isinstance(cmd, str) else cmd
    cmd_display = " ".join(shlex.quote(str(part)) for part in cmd_args)
    print(f"Running: {cmd_display}")
    with open(log_file, "a") as f:
        f.write(f"\n--- Running: {cmd_display} ---\n")
    
    result = subprocess.run(cmd_args, capture_output=True, text=True)
    
    with open(log_file, "a") as f:
        f.write(result.stdout)
        f.write(result.stderr)
        
    if result.returncode != 0:
        print(f"Error running command. Check {log_file}")
        return False
    return True

def score_texture(texture_dir):
    """
    Evaluates the flatness of the unroll by running a proxy metric on the generated surface texture.
    In a full run, we would use our `best_model.pt` to predict ink and measure the signal-to-noise ratio.
    For this wrapper, we measure image variance as a proxy for structural clarity.
    """
    import cv2
    tifs = glob.glob(os.path.join(texture_dir, "*.tif"))
    if not tifs:
        return 0.0
    
    scores = []
    for tif in tifs:
        img = cv2.imread(tif, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            # High variance indicates crisp structural details (not blurred/crushed)
            scores.append(np.var(img))
            
    return float(np.mean(scores)) if scores else 0.0

def main():
    print("--- Vesuvius Autoresearch: ThaumatoAnakalyptor Solver Evolution ---")
    print("Optimizing graph solver parameters for First Title hunt...")
    
    # These paths assume execution inside the Thaumato Docker container
    base_scroll_path = "/scroll.volpkg"
    surface_points_dir = f"{base_scroll_path}/scroll3_surface_points"
    graph_bin_input = f"{surface_points_dir}/1352_3600_5002/graph.bin"
    output_bin = f"{surface_points_dir}/1352_3600_5002/output_graph.bin"
    pointcloud_blocks_dir = f"{surface_points_dir}/point_cloud_colorized_verso_subvolume_blocks"
    
    if not os.path.exists(graph_bin_input):
        print(f"Waiting for prerequisite graph.bin at {graph_bin_input}")
        print("Ensure 'instances_to_graph' has been run first.")
        return

    log_file = "thaumato_autoresearch.log"
    history_file = "thaumato_history.json"
    
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)

    for cycle in range(1, 101):
        print(f"\n--- Cycle {cycle} ---")
        
        # 1. Sample Hyperparameters
        solver_type = random.choice(["cpp", "python_viterbi", "python_random_walk"])
        spring_constant = round(random.uniform(0.5, 2.5), 2)
        steps = random.choice([2, 3, 4, 5])
        estimated_windings = random.randint(40, 80)
        
        print(f"Testing Config: solver={solver_type}, spring_constant={spring_constant}, steps={steps}, windings={estimated_windings}")
        
        # 2. Run Graph Solver
        if solver_type == "cpp":
            solver_cmd = (
                f"./ThaumatoAnakalyptor/graph_problem/build/graph_problem_gpu "
                f"--input_graph {graph_bin_input} --output_graph {output_bin} "
                f"--auto --auto_num_iterations 2000 --z_min 5000 --z_max 6000 "
                f"--num_iterations 2000 --estimated_windings {estimated_windings} "
                f"--steps {steps} --spring_constant {spring_constant}"
            )
            if not run_command(solver_cmd, log_file):
                continue
            
            # 3. Translate bin back to pkl for C++ output
            translate_cmd = f"python3 -m ThaumatoAnakalyptor.instances_to_graph --path {pointcloud_blocks_dir} --create_graph"
            if not run_command(translate_cmd, log_file):
                continue
        else:
            # Our custom Python graph solver using Viterbi or Random Walk directly against the .pkl format
            algo = "viterbi" if solver_type == "python_viterbi" else "random_walk"
            pkl_input = f"{pointcloud_blocks_dir}/1352_3600_5002/scroll_graph_angular.pkl"
            pkl_output = f"{pointcloud_blocks_dir}/1352_3600_5002/point_cloud_colorized_verso_subvolume_graph_BP_solved.pkl"
            
            python_solver_cmd = (
                f"python3 scripts/sheet_stitcher.py "
                f"--input_graph {pkl_input} --output {pkl_output} --algorithm {algo}"
            )
            if not run_command(python_solver_cmd, log_file):
                continue

        # 4. Generate Mesh
        # We append a unique ID to the output so we can evaluate it independently
        run_id = f"opt_{cycle}_{int(time.time())}"
        mesh_cmd = (
            f"python3 -m ThaumatoAnakalyptor.graph_to_mesh --path {pointcloud_blocks_dir} "
            f"--graph 1352_3600_5002/point_cloud_colorized_verso_subvolume_graph_BP_solved.pkl 1352 3600 5002 "
            f"--z_range 5000 6000 --angle_step 2.0 --unfix_factor 5.0 --continue_from 0 --scale_factor 1.0 "
        )
        if not run_command(mesh_cmd, log_file):
            continue
            
        # The mesh is dumped to a specific timestamped folder. We grab the newest one.
        mesh_folders = glob.glob(f"{pointcloud_blocks_dir}/1352_3600_5002/point_cloud_colorized_verso_subvolume_blocks/windowed_mesh_*")
        if not mesh_folders:
            continue
        latest_mesh = max(mesh_folders, key=os.path.getmtime)
        
        # 5. Generate Surface Texture
        texture_cmd = (
            f"python3 -m ThaumatoAnakalyptor.large_mesh_to_surface --input_mesh {latest_mesh} "
            f"--scroll {base_scroll_path}/volumes/20231027191953 --nr_workers 4 --gpus 1"
        )
        if not run_command(texture_cmd, log_file):
            continue
            
        # 6. Score the Texture
        # Texture outputs are typically alongside the mesh
        score = score_texture(latest_mesh)
        print(f"Cycle {cycle} Score: {score:.4f}")
        
        # 7. Record
        record = {
            "cycle": cycle,
            "spring_constant": spring_constant,
            "steps": steps,
            "estimated_windings": estimated_windings,
            "score": score,
            "mesh_path": latest_mesh
        }
        history.append(record)
        
        with open(history_file, "w") as f:
            json.dump(history, f, indent=4)
            
        print("Best score so far:", max([r["score"] for r in history]))

if __name__ == "__main__":
    main()
