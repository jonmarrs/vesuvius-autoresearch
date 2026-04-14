import os
import subprocess
import time
import re
import random
import sys
import json
from collections import defaultdict

# Define templates for architectural and hyperparameter tweaks
tweak_templates = [
    {"family": "lr", "name": "lr_{val}", "file": "train.py", "pattern": r"lr:\s*float\s*=\s*[\d\.e-]+", "repl": "lr: float = {val}", "vals": ["1e-3", "5e-4", "1e-4", "5e-5", "1e-5"]},
    {"family": "wd", "name": "wd_{val}", "file": "train.py", "pattern": r"weight_decay=[\d\.]+", "repl": "weight_decay={val}", "vals": ["0.1", "0.01", "0.001", "0.0"]},
    {"family": "capacity", "name": "blocks_{val}", "file": "train.py", "pattern": r"num_blocks=\d+", "repl": "num_blocks={val}", "vals": ["8", "10", "12", "16"]}, 
    {"family": "attention", "name": "heads_{val}", "file": "vesuvius_model.py", "pattern": r"num_heads=\d+", "repl": "num_heads={val}", "vals": ["4", "8", "12"]},
    {"family": "regularization", "name": "dropout_{val}", "file": "vesuvius_model.py", "pattern": r"dropout=[\d\.]+", "repl": "dropout={val}", "vals": ["0.1", "0.2", "0.0"]},
    {"family": "batch", "name": "batch_size_{val}", "file": "train.py", "pattern": r"batch_size:\s*int\s*=\s*\d+", "repl": "batch_size: int = {val}", "vals": ["8", "16", "24"]}, 
    {"family": "spatial", "name": "patch_size_{val}", "file": "train.py", "pattern": r"patch_size:\s*int\s*=\s*\d+", "repl": "patch_size: int = {val}", "vals": ["64", "96"]},
    {"family": "temporal", "name": "num_layers_{val}", "file": "train.py", "pattern": r"num_layers:\s*int\s*=\s*\d+", "repl": "num_layers: int = {val}", "vals": ["16", "24", "32"]}, 
    {"family": "width", "name": "base_feat_{val}", "file": "train.py", "pattern": r"base_feat=\d+", "repl": "base_feat={val}", "vals": ["32", "64"]}
]

# Persistent Bayesian-Lite Success Tracking
HISTORY_FILE = "autoresearch_history.json"
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

def get_current_config():
    config = {}
    try:
        with open('train.py', 'r') as f:
            content = f.read()
            m = re.search(r'lr:\s*float\s*=\s*([\d\.e-]+)', content)
            if m: config['lr'] = m.group(1)
            m = re.search(r'weight_decay=([\d\.]+)', content)
            if m: config['wd'] = m.group(1)
            m = re.search(r'num_blocks=(\d+)', content)
            if m: config['blocks'] = m.group(1)
            m = re.search(r'batch_size:\s*int\s*=\s*(\d+)', content)
            if m: config['batch_size'] = m.group(1)
            m = re.search(r'patch_size:\s*int\s*=\s*(\d+)', content)
            if m: config['patch_size'] = m.group(1)
            m = re.search(r'num_layers:\s*int\s*=\s*(\d+)', content)
            if m: config['num_layers'] = m.group(1)
            m = re.search(r'base_feat=(\d+)', content)
            if m: config['base_feat'] = m.group(1)
            m = re.search(r"uri:\s*str\s*=\s*'(.*?)'", content)
            if m: config['uri'] = m.group(1)
    except Exception as e:
        print(f"Error parsing train.py: {e}")
    try:
        with open('vesuvius_model.py', 'r') as f:
            content = f.read()
            m = re.search(r'num_heads=(\d+)', content)
            if m: config['heads'] = m.group(1)
            m = re.search(r'dropout=([\d\.]+)', content)
            if m: config['dropout'] = m.group(1)
    except Exception as e:
        print(f"Error parsing vesuvius_model.py: {e}")
    return config

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
print(f"Starting persistent background loop until {end_hour % 12 or 12}:00 {'PM' if end_hour >= 12 else 'AM'}...")
sys.stdout.flush()

with open(log_filename, "w") as log:
    log.write(f"# {shift_name.title()} Sprint - {time.strftime('%Y-%m-%d')}\n")
    log.write(f"- **Start Time**: {time.strftime('%H:%M:%S')}\n")
    log.write("- **Goal**: Monotonic val_bpb optimization via 15-min cycles.\n\n")

env = os.environ.copy()
i = 0

while True:
    i += 1
    if time.localtime().tm_hour == end_hour:
        print(f"{shift_name} end reached. Ending sprint.")
        with open(log_filename, "a") as log:
            log.write(f"\n## Sprint Completed at {time.strftime('%H:%M:%S')}\n")
        break

    # Bayesian-Lite Sampling
    families = [t["family"] for t in tweak_templates]
    weights = [success_counts[f] for f in families]
    template = random.choices(tweak_templates, weights=weights, k=1)[0]
    
    val = random.choice(template["vals"])
    tweak = {
        "name": template["name"].format(val=val),
        "family": template["family"],
        "file": template["file"],
        "pattern": template["pattern"],
        "repl": template["repl"].format(val=val)
    }

    print(f"\nCycle {i}: Applying {tweak['name']} (Family Weight: {success_counts[tweak['family']]})")
    sys.stdout.flush()
    try:
        with open(tweak["file"], "r") as f:
            file_content = f.read()
        
        new_content, count = re.subn(tweak["pattern"], tweak["repl"], file_content, flags=re.MULTILINE)
        if count > 0:
            with open(tweak["file"], "w") as f:
                f.write(new_content)
            print(f"Applied tweak: {tweak['name']}")
        else:
            print(f"Failed to apply {tweak['name']}, pattern not found. Skipping.")
            continue
            
        current_cfg = get_current_config()
        uri = current_cfg.pop('uri', 'N/A')
        cfg_str = ", ".join([f"{k}: {v}" for k, v in current_cfg.items()])

        print(f"Running 15-minute training for {tweak['name']}...")
        sys.stdout.flush()
        
        with open("run.log", "a") as f:
            f.write(f"\n\n--- {shift_name} CYCLE {i}: {tweak['name']} ---\n")
            f.flush()
            result = subprocess.run(
                "uv run train.py",
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
            success_counts[tweak["family"]] += 1 
            save_history(success_counts)

        with open(log_filename, "a") as log:
            log.write(f"## Cycle {i}: {tweak['name']} ({status})\n")
            log.write(f"- **Timestamp**: {time.strftime('%H:%M:%S')}\n")
            log.write(f"- **Data**: {uri}\n")
            log.write(f"- **Config**: {cfg_str}\n")
            log.write(f"- **Stats**: val_bpb: {val_bpb}, loss: {train_loss}, params: {params}M, vram: {vram}MB, speed: {vps}Mvps\n")
            log.write(f"- **Result**: {'Improvement detected. Changes committed.' if is_success else 'No improvement detected. Changes reverted.'}\n\n")
            log.flush()

        if is_success:
            print("IMPROVEMENT FOUND! Committing changes.")
            os.system(f'git add train.py vesuvius_model.py results.tsv reports/figures/ best_model.pt autoresearch_history.json && git commit -m "{shift_name}: {tweak["name"]} improved model"')
        else:
            print("No improvement. Reverting.")
            os.system("git restore train.py vesuvius_model.py")
        
        sys.stdout.flush()
        time.sleep(2)

    except Exception as e:
        print(f"An error occurred: {e}")
        os.system("git restore train.py vesuvius_model.py")
        time.sleep(2)
