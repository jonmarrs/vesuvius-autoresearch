import fcntl
import json
import os
import random
import signal
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import asdict

import pandas as pd
import torch

from train import ExperimentConfig

LOCK_FILE = "autoresearch.lock"


def check_lock():
    fp = open(LOCK_FILE, "w")
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(
            "Another instance of run_autoresearch_loop.py is already running. Exiting."
        )
        sys.exit(1)
    return fp


active_child_p = None


def signal_handler(sig, frame):
    global active_child_p
    print(f"\nCaught signal {sig}. Cleaning up...")
    if active_child_p:
        print("Killing active child process group...")
        try:
            os.killpg(os.getpgid(active_child_p.pid), signal.SIGTERM)
            active_child_p.wait(timeout=5)
        except Exception as e:
            print(f"Error during cleanup: {e}")
    sys.exit(0)


# Define templates for architectural and hyperparameter tweaks
# These now map directly to ExperimentConfig attributes
tweak_templates = [
    {"family": "lr", "attr": "lr", "vals": [1e-3, 5e-4, 1e-4, 5e-5, 1e-5]},
    {"family": "wd", "attr": "weight_decay", "vals": [0.1, 0.01, 0.001, 0.0]},
    {"family": "capacity", "attr": "num_blocks", "vals": [8, 10, 12, 16, 20]},
    {"family": "attention", "attr": "num_heads", "vals": [4, 8, 12]},
    {"family": "regularization", "attr": "dropout", "vals": [0.1, 0.2, 0.0]},
    {"family": "preproc", "attr": "use_lasagna", "vals": [True, False]},
    # target_fiber_source: tests whether the fiber head's BCE target benefits
    # from being real Frangi vesselness (dataloader-side, ~86ms/patch CPU,
    # parallelized) instead of the cheap inline Sobel-Z gradient.
    {"family": "preproc", "attr": "target_fiber_source", "vals": ["sobel_z", "frangi"]},
    # multi_task_heads: replaces the GenericMultiTaskWrapper's dummy
    # fiber/qc/st outputs with real Conv3d/Linear heads operating on
    # cat(input, backbone_output). Adds ~5k params, but gradients from
    # loss_fiber/loss_qc/loss_st now flow back through the backbone.
    {"family": "regularization", "attr": "multi_task_heads", "vals": [True, False]},
    {"family": "batch", "attr": "batch_size", "vals": [8, 16, 24]},
    {"family": "spatial", "attr": "patch_size", "vals": [64, 96]},
    {"family": "temporal", "attr": "num_layers", "vals": [16, 24, 32]},
    {"family": "width", "attr": "base_feat", "vals": [32, 64, 128]},
    {"family": "loss_balance", "attr": "loss_ink_bce", "vals": [0.2, 0.4, 0.6]},
    {"family": "loss_balance", "attr": "loss_ink_dice", "vals": [0.2, 0.4, 0.6]},
    {"family": "loss_balance", "attr": "loss_fiber_bce", "vals": [0.1, 0.2, 0.3]},
    {"family": "loss_balance", "attr": "loss_st", "vals": [0.0, 0.1, 0.2]},
    {"family": "features", "attr": "use_ridges", "vals": [True, False]},
    # ridge_sigma is a no-op when use_ridges is False (ridges aren't computed
    # at all); gate the axis so the bandit only samples it when the enabling
    # flag is on. Without the gate, bandit-state analysis showed pure-noise
    # samples landing on this axis (2026-05-18 cycle 31 was the best val_bpb
    # of the day but ridge_sigma had no effect).
    {
        "family": "features",
        "attr": "ridge_sigma",
        "vals": [1.0, 2.0, 3.0],
        "applies_when": lambda c: getattr(c, "use_ridges", False),
    },
    {
        "family": "features",
        "attr": "aug_mode",
        "vals": ["albumentations", "batchgeneratorsv2"],
    },
    # Architecture family restricted to candidates with real (non-dummy) ST/QC
    # heads. Audit on 2026-05-17 found that lejepa_unet has been a topology
    # regression since the 2026-05-06 flip: skel_dist 27 px vs the May-5
    # resenc_unet's 1 px (prize gate: <= 2 px). lejepa_unet, timesformer, and
    # resnet3d_decoder all return torch.zeros(...) for the structure-tensor
    # head, which explains the regression. Only resenc_unet (ResEnc UNet) and
    # gated_unet (InkDetectorOptimized) have real ST heads.
    {
        "family": "architecture",
        "attr": "architecture",
        "vals": ["resenc_unet", "gated_unet"],
    },
    {
        "family": "scroll_augmentations",
        "attr": "aug_scroll_decohesion_p",
        "vals": [0.0, 0.25, 0.5],
    },
    {
        "family": "scroll_augmentations",
        "attr": "aug_scroll_warping_p",
        "vals": [0.0, 0.25, 0.5],
    },
    {
        "family": "scroll_augmentations",
        "attr": "aug_scroll_squeeze_p",
        "vals": [0.0, 0.25, 0.5],
    },
    {
        "family": "scroll_augmentations",
        "attr": "aug_scroll_z_dropout_p",
        "vals": [0.0, 0.25, 0.5],
    },
    # Removed 2026-05-17 after audit confirmed this axis has been a no-op since the
    # loop's inception: train.py:742 expects {segment_name}_pseudo.png in the
    # pseudo_label_dir, but no such file has ever existed on disk (the actual
    # files in local_data/pseudo_labels/ are 36 pred_*.png prediction outputs
    # whose names don't match the contract). Both vals (None and
    # "local_data/pseudo_labels") therefore produce bit-identical training that
    # falls back to manual inklabels_filled.png; cycles sampled to this family
    # always REVERTED. Re-add this entry after running
    # scripts/generate_pseudo_labels.py to produce real {segment_name}_pseudo.png
    # files matching the train.py contract.
    # {"family": "iterative", "attr": "pseudo_label_dir", "vals": [None, "local_data/pseudo_labels"]},
    {"family": "uamt", "attr": "use_uamt", "vals": [True, False]},
    # consistency_weight and ema_decay are both no-ops when use_uamt is False
    # (the UA-MT block at train.py is gated by `if config.use_uamt and ...`).
    # Gate them so the bandit doesn't waste cycles sampling them when UA-MT
    # is disabled. The bandit can still turn UA-MT on via the use_uamt
    # template above, which would re-enable these axes in the next cycle.
    {
        "family": "uamt",
        "attr": "consistency_weight",
        "vals": [0.05, 0.1, 0.2],
        "applies_when": lambda c: bool(getattr(c, "use_uamt", False)),
    },
    {
        "family": "uamt",
        "attr": "ema_decay",
        "vals": [0.99, 0.999, 0.9999],
        "applies_when": lambda c: bool(getattr(c, "use_uamt", False)),
    },
]

HISTORY_FILE = "autoresearch_history.json"
CONFIG_FILE = "config.json"
RECENT_CONFIGS_FILE = "recent_configs.json"
CURRENT_LOG_PTR = ".current_day_shift_log"
TEMP_CONFIG = "config_temp.json"


def load_history():
    counts = defaultdict(lambda: 1)
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    counts.update(data)
                return counts
        except Exception as e:
            print(f"Warning: Could not load history from {HISTORY_FILE}: {e}")
    return counts


def save_history(counts):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(dict(counts), f, indent=4)
    except Exception as e:
        print(f"Warning: Could not save history: {e}")


def load_recent_configs():
    if os.path.exists(RECENT_CONFIGS_FILE):
        try:
            with open(RECENT_CONFIGS_FILE) as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {RECENT_CONFIGS_FILE}: {e}")
            return []
    return []


def save_recent_configs(configs):
    try:
        with open(RECENT_CONFIGS_FILE, "w") as f:
            json.dump(configs[-20:], f)
    except Exception as e:
        print(f"Warning: Could not save {RECENT_CONFIGS_FILE}: {e}")


def main():
    """Entry point for the autonomous Day/Night Shift autoresearch loop.

    All process-level side effects (file lock acquisition, signal handler
    registration, directory creation, sprint-log writes) live inside this
    function so that ``from run_autoresearch_loop import tweak_templates``
    is a side-effect-free import. The previous module-level layout caused
    any importer (test runner, syntax-check, IDE introspection) to acquire
    the lock and write a sprint-log header; see 2026-05-16 incident notes.
    """
    global active_child_p

    lock_fp = check_lock()  # noqa: F841 (kept open for the duration of the process)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    success_counts = load_history()

    # Detect Shift
    current_hour = time.localtime().tm_hour
    if 7 <= current_hour < 19:
        shift_name = "DAY SHIFT"
        end_hour = 19
        default_budget = 900
    else:
        shift_name = "NIGHT SHIFT"
        end_hour = 7
        default_budget = 3600

    os.makedirs("sprint_logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    log_filename = f"sprint_logs/sprint_log_{time.strftime('%Y-%m-%d_%H-%M-%S')}_{shift_name.lower().replace(' ', '_')}.md"

    # Resume previous log if still same shift and file exists
    if os.path.exists(CURRENT_LOG_PTR):
        with open(CURRENT_LOG_PTR) as f:
            prev_log = f.read().strip()
            if os.path.exists(prev_log) and shift_name.lower() in prev_log.lower():
                # Check if it was today (simple check)
                if time.strftime("%Y-%m-%d") in prev_log:
                    log_filename = prev_log
                    print(f"Resuming existing shift log: {log_filename}")

    with open(CURRENT_LOG_PTR, "w") as f:
        f.write(log_filename)

    # Load best val_bpb baseline at startup
    best_val_bpb = 1.0
    if os.path.exists("best_model.pt"):
        try:
            best_model_data = torch.load(
                "best_model.pt", map_location="cpu", weights_only=False
            )
            best_val_bpb = best_model_data.get("val_bpb", 1.0)
            print(
                f"Starting with baseline val_bpb from best_model.pt: {best_val_bpb:.6f}"
            )
        except Exception as e:
            print(f"Warning: Could not load best_model.pt baseline: {e}")
    elif os.path.exists("results.tsv"):
        try:
            df = pd.read_csv("results.tsv", sep="\t")
            if len(df) > 0:
                best_val_bpb = df["val_bpb"].min()
                print(
                    f"Starting with baseline val_bpb from results.tsv: {best_val_bpb:.6f}"
                )
        except Exception as e:
            print(f"Warning: Could not load results.tsv baseline: {e}")

    print(f"--- {shift_name} STARTING AT {time.strftime('%H:%M:%S')} ---")
    print(f"Logging to: {log_filename}")
    sys.stdout.flush()

    if not os.path.exists(log_filename):
        with open(log_filename, "w") as log:
            log.write(f"# {shift_name.title()} Sprint - {time.strftime('%Y-%m-%d')}\n")
            log.write(f"- **Start Time**: {time.strftime('%H:%M:%S')}\n")
            log.write(
                f"- **Goal**: Monotonic val_bpb optimization via {default_budget // 60}-min cycles (Config-Driven).\n\n"
            )

    env = os.environ.copy()
    i = 0
    recent_configs = load_recent_configs()

    while True:
        i += 1
        # Refresh best_val_bpb from results.tsv if it changed
        if os.path.exists("results.tsv"):
            try:
                df = pd.read_csv("results.tsv", sep="\t")
                if len(df) > 0:
                    best_val_bpb = df["val_bpb"].min()
            except Exception as e:
                print(f"Warning: Could not refresh results.tsv baseline: {e}")

        # Have we crossed out of this shift's bucket? The previous check was
        # `tm_hour == end_hour`, which only matches for the single hour at
        # transition — if a long cycle was running through it, the check
        # missed and the loop kept spawning cycles until the next day's
        # boundary. On 2026-05-20 the Night Shift overran by ~3.5h before
        # being killed because of exactly this. The fix: exit when we've
        # transitioned INTO the next shift's bucket, not when we hit a
        # single hour value.
        _hr = time.localtime().tm_hour
        _in_day_bucket = 7 <= _hr < 19
        _shift_over = (shift_name == "DAY SHIFT" and not _in_day_bucket) or (
            shift_name == "NIGHT SHIFT" and _in_day_bucket
        )
        if _shift_over:
            print(f"{shift_name} end reached (hour={_hr}). Ending sprint.")
            next_shift = "DAY SHIFT" if shift_name == "NIGHT SHIFT" else "NIGHT SHIFT"
            with open(log_filename, "a") as log:
                log.write(f"\n## Sprint Completed at {time.strftime('%H:%M:%S')}\n")
                log.write(f"Transitioning to {next_shift}...\n")

            if shift_name == "NIGHT SHIFT":
                print("\n" + "=" * 60)
                print(
                    "ACTIVE LEARNING FLYWHEEL: It is highly recommended to run the Proofreader"
                )
                print("on the latest predictions before starting the Day Shift.")
                print(
                    "Run: uv run scripts/launch_proofreader.py --volume local_data/PHercParis2Fr47/surface_volume.zarr --predictions predictions/pred_10_1000_1000_64x64_ink.zarr"
                )
                print("=" * 60 + "\n")

            break

        # Load current best config
        if os.path.exists(CONFIG_FILE):
            config = ExperimentConfig.load(CONFIG_FILE)
        else:
            config = ExperimentConfig()

        # Sprint 022: Fixed GP-Winner Baseline Injection
        is_pinned_cycle = i % 10 == 0

        if is_pinned_cycle:
            print(f"Cycle {i}: Injecting FIXED GP-WINNER BASELINE for calibration...")
            # Maintain current URIs but force other parameters
            current_uris = config.uris
            current_val_uri = config.val_uri
            config = ExperimentConfig(
                uris=current_uris,
                val_uri=current_val_uri,
                architecture="timesformer",
                patch_size=256,
                num_layers=16,
                lr=3e-5,
                loss_ink_bce=0.5,
                loss_ink_dice=0.5,
                loss_fiber_bce=0.0,
                loss_st=0.0,
                label_smoothing=0.25,
                pinned=True,
                time_budget=default_budget,
            )
            tweak_name = "gp_winner_baseline"
            family = "baseline"
        else:
            # Conditional-axis gating: drop templates whose `applies_when`
            # predicate is False under the current baseline config (e.g.
            # ridge_sigma when use_ridges=False). Avoids spending cycles on
            # axes that produce identical results to the baseline.
            baseline_for_gate = (
                ExperimentConfig.load(CONFIG_FILE)
                if os.path.exists(CONFIG_FILE)
                else ExperimentConfig()
            )
            active_templates = [
                t
                for t in tweak_templates
                if t.get("applies_when", lambda _c: True)(baseline_for_gate)
            ]
            if not active_templates:
                # Defensive: should never happen (architecture/lr/etc are unconditional).
                active_templates = tweak_templates

            # Success-Biased Decay: Every cycle, all (active) families decay slightly.
            # This ensures that even successful families eventually lose their dominance
            # if they stop producing improvements, forcing exploration of other families.
            families = [t["family"] for t in active_templates]
            for f in set(families):
                success_counts[f] = max(1.0, success_counts[f] * 0.95)

            weights = [success_counts[f] for f in families]

            # Frontier-V: Config-Space Entropy Protection
            # Avoid testing the exact same thing twice in a row if it failed recently
            max_retries = 10
            applied = False
            for _ in range(max_retries):
                template = random.choices(active_templates, weights=weights, k=1)[0]
                val = random.choice(template["vals"])
                family = template["family"]
                attr = template["attr"]

                # Apply tweak to a copy of current config
                test_config = (
                    ExperimentConfig.load(CONFIG_FILE)
                    if os.path.exists(CONFIG_FILE)
                    else ExperimentConfig()
                )
                # Ensure we don't carry over 'pinned' status to evolved configs
                test_config.pinned = False
                test_config.time_budget = default_budget
                setattr(test_config, attr, val)

                cfg_dict = asdict(test_config)
                # Remove volatile fields for comparison
                for k in ["uri", "val_uri", "cache_dir", "time_budget"]:
                    cfg_dict.pop(k, None)

                if cfg_dict not in recent_configs:
                    config = test_config
                    recent_configs.append(cfg_dict)
                    save_recent_configs(recent_configs)
                    applied = True
                    break
                else:
                    print(
                        f"Cycle {i}: Sampled duplicate config ({attr}={val}). Re-sampling for entropy..."
                    )

            # Exhaustion fallback: if max_retries ran out without finding a
            # non-duplicate config, accept the LAST sampled config rather than
            # silently fall through (which would run the baseline config but
            # log it as having had the last rejected tweak — pollutes
            # success_counts attribution). Reset recent_configs to clear the
            # saturation so the next cycle has a fresh search space.
            if not applied:
                print(
                    f"Cycle {i}: {max_retries} retries exhausted; accepting last sampled config ({attr}={val}) and resetting recent_configs."
                )
                config = test_config
                recent_configs = [cfg_dict]
                save_recent_configs(recent_configs)

            tweak_name = f"{attr}_{val}"

        # Pre-flight VRAM estimation (Complexity Heuristic - Sprint 023 Refined)
        # Standard baseline: 64 feat, 24 layers, 64 patch, 8 batch, 16 blocks ~= 14GB VRAM
        feat_factor = config.base_feat / 64.0
        depth_factor = config.num_layers / 24.0
        patch_sq = (config.patch_size / 64.0) ** 2
        patch_quartic = (config.patch_size / 64.0) ** 4
        batch_factor = config.batch_size / 8.0
        block_factor = config.num_blocks / 16.0

        # Linear components (Convs, Activations)
        complexity_linear = (
            feat_factor * depth_factor * patch_sq * batch_factor * block_factor
        )
        # Quadratic components (Attention)
        complexity_attn = depth_factor * patch_quartic * batch_factor * block_factor

        # Weighted Score (Standard Config = 1.0). Attention weighted at 0.4 due to quadratic growth.
        complexity_score = 0.6 * complexity_linear + 0.4 * complexity_attn

        if complexity_score > 1.5:  # Cap at 50% overhead above baseline (~21GB VRAM)
            print(
                f"Cycle {i}: Skipping {tweak_name} (Complexity Score {complexity_score:.2f} > 1.5) to avoid OOM."
            )
            continue

        print(
            f"\nCycle {i}: Applying {tweak_name} (Family Weight: {success_counts[family]})"
        )
        sys.stdout.flush()

        # Save temporary config for this run
        config.save(TEMP_CONFIG)

        cfg_str = ", ".join(
            [
                f"{k}: {v}"
                for k, v in asdict(config).items()
                if k not in ["uri", "val_uri"]
            ]
        )

        print(f"Running {default_budget // 60}-minute training for {tweak_name}...")
        sys.stdout.flush()

        if os.path.exists("run_result.json"):
            os.remove("run_result.json")

        # Rotate run.log if it grows too large (> 10MB)
        if os.path.exists("run.log") and os.path.getsize("run.log") > 10 * 1024 * 1024:
            if os.path.exists("run.log.old"):
                os.remove("run.log.old")
            os.rename("run.log", "run.log.old")

        try:
            with open("run.log", "a") as f:
                f.write(f"\n\n--- {shift_name} CYCLE {i}: {tweak_name} ---\n")
                f.flush()

                # Robust Process Management: use session group to kill all descendants
                env_unbuffered = env.copy()
                env_unbuffered["PYTHONUNBUFFERED"] = "1"
                p = subprocess.Popen(
                    ["uv", "run", "python", "-u", "train.py", "--config", TEMP_CONFIG],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    env=env_unbuffered,
                    text=True,
                    start_new_session=True,
                )
                f.flush()
                active_child_p = p
                try:
                    p.wait(timeout=default_budget + 300)  # 5 minute safety buffer
                except subprocess.TimeoutExpired:
                    print(f"Cycle {i} timed out. Killing process group...")
                    try:
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                    except Exception as e:
                        print(f"Error killing process group: {e}")
                    p.wait()
                finally:
                    active_child_p = None
        except Exception as e:
            print(f"Subprocess error in cycle {i}: {e}")

        val_bpb = train_loss = params = vram = vps = "N/A"
        is_success = False
        is_crash = False
        oom_detected = False

        if not os.path.exists("run_result.json"):
            is_crash = True
            if os.path.exists("run.log"):
                try:
                    with open("run.log") as f:
                        lines = f.readlines()
                        log_tail_raw = "".join(lines[-20:])
                        log_tail = log_tail_raw.lower()
                        if (
                            "out of memory" in log_tail
                            or "cuda error: out of memory" in log_tail
                        ):
                            oom_detected = True
                        else:
                            print(f"--- DIAGNOSTICS FOR CYCLE {i} CRASH ---")
                            print(log_tail_raw)
                            print("---------------------------------------")
                except Exception as e:
                    print(
                        f"Warning: Could not read run.log diagnostics after crash: {e}"
                    )
        else:
            try:
                with open("run_result.json") as f:
                    res = json.load(f)
                val_bpb = res.get("val_bpb", "N/A")
                train_loss = res.get("train_loss", "N/A")
                params = res.get("num_params_M", "N/A")
                vram = res.get("peak_vram_mb", "N/A")
                vps = res.get("throughput_Mvps", "N/A")
                is_success = res.get("is_success", False)
            except Exception as e:
                print(f"Error reading run_result.json: {e}")
                is_crash = True

        if is_success:
            status = "SUCCESS"
            success_counts[family] += 1
            save_history(success_counts)
            # Promote temp config to main config
            os.rename(TEMP_CONFIG, CONFIG_FILE)
        elif is_crash:
            status = "CRASHED (OOM)" if oom_detected else "CRASHED"
            # "do NOT penalize" -> Increment so it stays in the rotation
            success_counts[family] += 1
            save_history(success_counts)
            if os.path.exists(TEMP_CONFIG):
                os.remove(TEMP_CONFIG)
        else:
            status = "REVERTED"
            # Only "penalize" (don't increment) if it finished but didn't improve
            if os.path.exists(TEMP_CONFIG):
                os.remove(TEMP_CONFIG)

        with open(log_filename, "a") as log:
            log.write(f"## Cycle {i}: {tweak_name} ({status})\n")
            log.write(f"- **Timestamp**: {time.strftime('%H:%M:%S')}\n")
            log.write(f"- **Config**: {cfg_str}\n")
            log.write(
                f"- **Stats**: val_bpb: {val_bpb}, loss: {train_loss}, params: {params}M, vram: {vram}MB, speed: {vps}Mvps\n"
            )

            result_msg = "No improvement detected. Config reverted."
            if is_success:
                result_msg = "Improvement detected. Config updated."
            elif is_crash:
                result_msg = f"Training crashed ({'OOM' if oom_detected else 'Unknown error'}). Family weight preserved/incremented to retry other values."

            log.write(f"- **Result**: {result_msg}\n\n")
            log.flush()

        if is_success:
            print(f"IMPROVEMENT FOUND! (val_bpb: {val_bpb}) Committing config.")
            os.system(
                f'git add {CONFIG_FILE} reports/figures/ best_model.pt autoresearch_history.json && git commit -m "{shift_name}: {tweak_name} improved model to {val_bpb}"'
            )
        elif is_crash:
            print(
                f"CYCLE CRASHED ({'OOM' if oom_detected else 'UNKNOWN'}). Reverting but keeping family weight."
            )
        else:
            print(f"No improvement. (val_bpb: {val_bpb}, best was: {best_val_bpb:.6f})")

        # Benchmark Inference Step (Every 5 cycles).
        # Uses subprocess.run (not os.system) so a predict.py crash surfaces
        # as a visible warning rather than silently swallowing the failure.
        if i % 5 == 0:
            print(f"Cycle {i}: Running Benchmark Inference...")
            benchmark_path = f"reports/benchmark_v210_cycle{i}.png"
            benchmark_cmd = [
                "uv",
                "run",
                "predict.py",
                "--uri",
                "local_data/PHercParis2Fr143/surface_volume.zarr",
                "--z",
                "10",
                "--y",
                "1000",
                "--x",
                "1000",
                "--output_img",
                benchmark_path,
            ]
            try:
                subprocess.run(benchmark_cmd, check=True, timeout=600)
            except subprocess.CalledProcessError as bench_exc:
                print(
                    f"Cycle {i}: Benchmark inference failed (rc={bench_exc.returncode}). Continuing."
                )
            except subprocess.TimeoutExpired:
                print(f"Cycle {i}: Benchmark inference timed out (>600s). Continuing.")
            except Exception as bench_exc:
                print(
                    f"Cycle {i}: Benchmark inference unexpected error: {type(bench_exc).__name__}: {bench_exc}. Continuing."
                )

        sys.stdout.flush()
        time.sleep(2)


if __name__ == "__main__":
    main()
