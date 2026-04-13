import os
import subprocess
import time
import re
import random
import sys

# Define templates for architectural and hyperparameter tweaks
tweak_templates = [
    {"name": "lr_{val}", "file": "train.py", "pattern": r"lr:\s*float\s*=\s*[\d\.e-]+", "repl": "lr: float = {val}", "vals": ["1e-3", "5e-4", "1e-4", "5e-5", "1e-5"]},
    {"name": "wd_{val}", "file": "train.py", "pattern": r"weight_decay=[\d\.]+", "repl": "weight_decay={val}", "vals": ["0.1", "0.01", "0.001", "0.0"]},
    {"name": "blocks_{val}", "file": "train.py", "pattern": r"num_blocks=\d+", "repl": "num_blocks={val}", "vals": ["10", "12", "16", "20"]}, 
    {"name": "heads_{val}", "file": "vesuvius_model.py", "pattern": r"num_heads=\d+", "repl": "num_heads={val}", "vals": ["4", "8", "12"]},
    {"name": "dropout_{val}", "file": "vesuvius_model.py", "pattern": r"dropout=[\d\.]+", "repl": "dropout={val}", "vals": ["0.1", "0.2", "0.4", "0.0"]},
    {"name": "batch_size_{val}", "file": "train.py", "pattern": r"batch_size:\s*int\s*=\s*\d+", "repl": "batch_size: int = {val}", "vals": ["4", "8", "16"]}, 
    {"name": "patch_size_{val}", "file": "train.py", "pattern": r"patch_size:\s*int\s*=\s*\d+", "repl": "patch_size: int = {val}", "vals": ["64", "96", "128"]},
    {"name": "num_layers_{val}", "file": "train.py", "pattern": r"num_layers:\s*int\s*=\s*\d+", "repl": "num_layers: int = {val}", "vals": ["12", "16", "24"]}, 
    {"name": "base_feat_{val}", "file": "train.py", "pattern": r"base_feat=\d+", "repl": "base_feat={val}", "vals": ["32", "64", "128"]}
]

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

env = os.environ.copy()
i = 0

os.makedirs("sprint_logs", exist_ok=True)
log_filename = f"sprint_logs/sprint_log_{time.strftime('%Y-%m-%d_%H-%M-%S')}_day_shift.md"

print(f"--- DAY SHIFT STARTING AT {time.strftime('%H:%M:%S')} ---")
print(f"Logging to: {log_filename}")
print(f"Starting persistent background loop until 7:00 PM...")
sys.stdout.flush()

with open(log_filename, "w") as log:
    log.write(f"# Day Shift Sprint - {time.strftime('%Y-%m-%d')}\n")
    log.write(f"- **Start Time**: {time.strftime('%H:%M:%S')}\n")
    log.write("- **Goal**: Monotonic val_bpb optimization via 15-min cycles.\n\n")

while True:
    i += 1
    # Check if it's 7:00 PM (19:00)
    current_hour = time.localtime().tm_hour
    if current_hour == 19:
        print("7:00 PM reached. Ending Day Shift sprint.")
        sys.stdout.flush()
        with open(log_filename, "a") as log:
            log.write(f"\n## Sprint Completed at 7:00 PM\n")
        break



    # Select a random tweak
    template = random.choice(tweak_templates)
    val = random.choice(template["vals"])
    tweak = {
        "name": template["name"].format(val=val),
        "file": template["file"],
        "pattern": template["pattern"],
        "repl": template["repl"].format(val=val)
    }

    print(f"\nCycle {i}: Applying {tweak['name']}")
    sys.stdout.flush()
    try:
        with open(tweak["file"], "r") as f:
            file_content = f.read()
        
        # Apply the mutation using regex substitution
        new_content, count = re.subn(tweak["pattern"], tweak["repl"], file_content, flags=re.MULTILINE)
        if count > 0:
            with open(tweak["file"], "w") as f:
                f.write(new_content)
            print(f"Applied tweak: {tweak['name']}")
        else:
            print(f"Failed to apply {tweak['name']}, pattern not found. Skipping cycle.")
            sys.stdout.flush()
            continue
            
        # Get active config after tweak
        current_cfg = get_current_config()
        uri = current_cfg.pop('uri', 'N/A')
        cfg_str = ", ".join([f"{k}: {v}" for k, v in current_cfg.items()])

        print(f"Running 5-minute training for {tweak['name']}...")
        sys.stdout.flush()
        
        # Open run.log in append mode and stream subprocess output to it live
        with open("run.log", "a") as f:
            f.write(f"\n\n--- DAY SHIFT CYCLE {i}: {tweak['name']} ---\n")
            f.flush()

            
            # Using shell=True and explicit env propagation
            result = subprocess.run(
                "uv run train.py",
                shell=True,
                stdout=f,
                stderr=subprocess.STDOUT,
                env=env,
                text=True
            )
        
        # Check the last 4KB of run.log for stats
        try:
            with open("run.log", "rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 4096), 0)
                log_tail = f.read().decode("utf-8", errors="ignore")
        except Exception as e:
            log_tail = f"Error reading run.log: {e}"
            
        # Extract stats
        val_bpb = "N/A"
        train_loss = "N/A"
        params = "N/A"
        vram = "N/A"
        vps = "N/A"
        
        m = re.search(r"val_bpb:\s+([\d\.]+)", log_tail)
        if m: val_bpb = m.group(1)
        m = re.search(r"train_loss:\s+([\d\.]+)", log_tail)
        if m: train_loss = m.group(1)
        m = re.search(r"num_params_M:\s+([\d\.]+)", log_tail)
        if m: params = m.group(1)
        m = re.search(r"peak_vram_mb:\s+([\d\.]+)", log_tail)
        if m: vram = m.group(1)
        m = re.search(r"throughput_Mvps:\s+([\d\.]+)", log_tail)
        if m: vps = m.group(1)

        is_success = "[NEW BEST]" in log_tail
        status = "SUCCESS" if is_success else "REVERTED"
        
        with open(log_filename, "a") as log:
            log.write(f"## Cycle {i}: {tweak['name']} ({status})\n")
            log.write(f"- **Timestamp**: {time.strftime('%H:%M:%S')}\n")
            log.write(f"- **Data**: {uri}\n")
            log.write(f"- **Config**: {cfg_str}\n")
            log.write(f"- **Stats**: val_bpb: {val_bpb}, loss: {train_loss}, params: {params}M, vram: {vram}MB, speed: {vps}Mvps\n")
            if is_success:
                log.write(f"- **Result**: Improvement detected. Changes committed.\n\n")
            else:
                log.write(f"- **Result**: No improvement detected. Changes reverted.\n\n")

        if is_success:
            print("IMPROVEMENT FOUND! Committing changes.")
            os.system(f'git add . && git commit -m "Night Shift: {tweak["name"]} improved model"')
        else:
            print("No improvement. Reverting.")
            os.system("git restore .")
        
        sys.stdout.flush()
        time.sleep(2)

    except Exception as e:
        print(f"An error occurred during cycle {i}: {e}")
        sys.stdout.flush()
        os.system("git restore .")
        time.sleep(2)

print("\nAutoresearch loop completed.")
sys.stdout.flush()
