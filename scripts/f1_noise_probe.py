"""Identical-config noise probe: run the CURRENT promoted config N times with
checkpoint_out set (isolated branch — never touches best_model.pt / history.tsv /
results.tsv / prize_readiness.tsv) and collect val_f1 spread. This measures TRUE
run-to-run noise (train dataloader is unseeded; eval is fixed-seed), calibrating
F1_NOISE_TOLERANCE properly (the 2026-07-11 estimate was a cross-tweak UPPER bound)."""
import json
import os
import subprocess
import time

N = 4
OUT_DIR = "local_data/noise_probe"
RESULTS = "reports/detector/f1_noise_probe.json"
os.makedirs(OUT_DIR, exist_ok=True)

with open("config.json") as f:
    base = json.load(f)

env = os.environ.copy()
env["PYTHONPATH"] = ".:villa/foundation/datasets/fibers-dataset:" + env.get("PYTHONPATH", "")
env["PYTHONUNBUFFERED"] = "1"

runs = []
for i in range(1, N + 1):
    cfg = dict(base)
    cfg["checkpoint_out"] = f"{OUT_DIR}/run_{i}.pt"
    cfg["use_wandb"] = False
    cfg_path = f"{OUT_DIR}/config_run_{i}.json"
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
    if os.path.exists("run_result.json"):
        os.remove("run_result.json")
    t0 = time.time()
    print(f"--- run {i}/{N} starting ---", flush=True)
    p = subprocess.run(
        ["uv", "run", "python", "-u", "scripts/training/train.py", "--config", cfg_path],
        env=env, stdout=open(f"{OUT_DIR}/run_{i}.log", "w"), stderr=subprocess.STDOUT,
        timeout=int(base.get("time_budget", 900)) + 900,
    )
    rec = {"run": i, "rc": p.returncode, "seconds": round(time.time() - t0, 1)}
    if os.path.exists("run_result.json"):
        with open("run_result.json") as f:
            r = json.load(f)
        rec.update({k: r.get(k) for k in
                    ["val_f1", "val_f1_threshold", "ap_prevalence_lift", "roc_auc"]})
    runs.append(rec)
    print(f"--- run {i}: rc={p.returncode} val_f1={rec.get('val_f1')} "
          f"lift={rec.get('ap_prevalence_lift')} ({rec['seconds']}s) ---", flush=True)
    with open(RESULTS, "w") as f:
        json.dump({"config": "config.json (promoted use_uamt) + checkpoint_out",
                   "runs": runs}, f, indent=2)

vals = [r["val_f1"] for r in runs if isinstance(r.get("val_f1"), float)]
if len(vals) >= 2:
    import statistics
    print(f"\nval_f1 values: {[round(v, 5) for v in vals]}")
    print(f"n={len(vals)} mean={statistics.mean(vals):.5f} "
          f"std={statistics.stdev(vals):.5f} range={max(vals) - min(vals):.5f}")
print(f"wrote {RESULTS}", flush=True)
