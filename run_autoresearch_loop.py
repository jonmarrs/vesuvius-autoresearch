import os
import subprocess
import time
import random
import sys
import json
import re
from collections import defaultdict
from dataclasses import asdict
from train import ExperimentConfig

# Define templates for architectural and hyperparameter tweaks
# These now map directly to ExperimentConfig attributes
tweak_templates = [
    {"family": "lr", "attr": "lr", "vals": [1e-3, 5e-4, 1e-4, 5e-5, 1e-5]},
    {"family": "wd", "attr": "weight_decay", "vals": [0.1, 0.01, 0.001, 0.0]},
    {"family": "capacity", "attr": "num_blocks", "vals": [8, 10, 12, 16, 20]}, 
    {"family": "attention", "attr": "num_heads", "vals": [4, 8, 12]},
    {"family": "regularization", "attr": "dropout", "vals": [0.1, 0.2, 0.0]},
    {"family": "batch", "attr": "batch_size", "vals": [8, 16, 24]}, 
    {"family": "spatial", "attr": "patch_size", "vals": [64, 96]},
    {"family": "temporal", "attr": "num_layers", "vals": [16, 24, 32]}, 
    {"family": "width", "attr": "base_feat", "vals": [32, 64, 128]}
]

HISTORY_FILE = "autoresearch_history.json"
CONFIG_FILE = "config.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                counts = defaultdict(lambda: 1)
                counts.update(data)
                return counts
        except: pass
    return defaultdict(lambda: 1)

def save_history(counts):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(dict(counts), f)
    except: pass

success_counts = load_history()

# Detect Shift
current_hour = time.localtime().tm_hour
if 7 <= current_hour < 19:
    shift_name = "DAY SHIFT"
    end_hour = 19
else:
    shift_name = "NIGHT SHIFT"
    end_hour = 7

os.makedirs("sprint_logs", exist_ok=True)
log_filename = f"sprint_logs/sprint_log_{time.strftime('%Y-%m-%d_%H-%M-%S')}_{shift_name.lower().replace(' ', '_')}.md"

print(f"--- {shift_name} STARTING AT {time.strftime('%H:%M:%S')} ---")
print(f"Logging to: {log_filename}")
sys.stdout.flush()

with open(log_filename, "w") as log:
    log.write(f"# {shift_name.title()} Sprint - {time.strftime('%Y-%m-%d')}\n")
    log.write(f"- **Start Time**: {time.strftime('%H:%M:%S')}\n")
    log.write("- **Goal**: Monotonic val_bpb optimization via 15-min cycles (Config-Driven).\n\n")

env = os.environ.copy()
i = 0

while True:
    i += 1
    if time.localtime().tm_hour == end_hour:
        print(f"{shift_name} end reached. Ending sprint.")
        with open(log_filename, "a") as log:
            log.write(f"\n## Sprint Completed at {time.strftime('%H:%M:%S')}\n")
        break

    # Load current best config
    if os.path.exists(CONFIG_FILE):
        config = ExperimentConfig.load(CONFIG_FILE)
    else:
        config = ExperimentConfig()

    # Bayesian-Lite Sampling
    families = [t["family"] for t in tweak_templates]
    weights = [success_counts[f] for f in families]
    template = random.choices(tweak_templates, weights=weights, k=1)[0]
    
    val = random.choice(template["vals"])
    family = template["family"]
    attr = template["attr"]
    
    # Apply tweak to config object
    old_val = getattr(config, attr)
    setattr(config, attr, val)
    tweak_name = f"{attr}_{val}"

    print(f"\nCycle {i}: Applying {tweak_name} (Family Weight: {success_counts[family]})")
    sys.stdout.flush()
    
    # Save temporary config for this run
    TEMP_CONFIG = "config_temp.json"
    config.save(TEMP_CONFIG)
            
    cfg_str = ", ".join([f"{k}: {v}" for k, v in asdict(config).items() if k not in ['uri', 'val_uri']])

    print(f"Running 15-minute training for {tweak_name}...")
    sys.stdout.flush()
    
    with open("run.log", "a") as f:
        f.write(f"\n\n--- {shift_name} CYCLE {i}: {tweak_name} ---\n")
        f.flush()
        result = subprocess.run(
            f"uv run train.py --config {TEMP_CONFIG}",
            shell=True, stdout=f, stderr=subprocess.STDOUT, env=env, text=True
        )
    
    try:
        with open("run.log", "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 8192), 0) 
            log_tail = f.read().decode("utf-8", errors="ignore")
    except: log_tail = ""
        
    val_bpb = "N/A"; train_loss = "N/A"; params = "N/A"; vram = "N/A"; vps = "N/A"
    m = re.search(r"val_bpb:\s+([\d\.]+)", log_tail); 
    if m: val_bpb = m.group(1)
    m = re.search(r"train_loss:\s+([\d\.]+)", log_tail); 
    if m: train_loss = m.group(1)
    m = re.search(r"num_params_M:\s+([\d\.]+)", log_tail); 
    if m: params = m.group(1)
    m = re.search(r"peak_vram_mb:\s+([\d\.]+)", log_tail); 
    if m: vram = m.group(1)
    m = re.search(r"throughput_Mvps:\s+([\d\.]+)", log_tail); 
    if m: vps = m.group(1)

    is_success = "[NEW BEST]" in log_tail
    status = "SUCCESS" if is_success else "REVERTED"
    
    if is_success:
        success_counts[family] += 1 
        save_history(success_counts)
        # Promote temp config to main config
        os.rename(TEMP_CONFIG, CONFIG_FILE)
    else:
        if os.path.exists(TEMP_CONFIG):
            os.remove(TEMP_CONFIG)

    with open(log_filename, "a") as log:
        log.write(f"## Cycle {i}: {tweak_name} ({status})\n")
        log.write(f"- **Timestamp**: {time.strftime('%H:%M:%S')}\n")
        log.write(f"- **Config**: {cfg_str}\n")
        log.write(f"- **Stats**: val_bpb: {val_bpb}, loss: {train_loss}, params: {params}M, vram: {vram}MB, speed: {vps}Mvps\n")
        log.write(f"- **Result**: {'Improvement detected. Config updated.' if is_success else 'No improvement detected. Config reverted.'}\n\n")
        log.flush()

    if is_success:
        print("IMPROVEMENT FOUND! Committing config.")
        os.system(f'git add {CONFIG_FILE} results.tsv reports/figures/ best_model.pt autoresearch_history.json && git commit -m "{shift_name}: {tweak_name} improved model"')
    else:
        print("No improvement.")
    
    sys.stdout.flush()
    time.sleep(2)
