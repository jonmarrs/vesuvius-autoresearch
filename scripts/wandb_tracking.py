"""Opt-in Weights & Biases experiment tracking for the autoresearch loop.

The official ScrollPrize/villa training stacks use wandb; this mirrors that for
our loop. Tracking is OFF unless config.use_wandb is set. When enabled it
defaults to ONLINE mode (logs to wandb.ai, matching villa's setup), which
requires `wandb login` (an API key) on the machine; set WANDB_MODE=offline to
keep runs local and sync later. Every helper is a safe no-op when tracking is
disabled, so the loop runs identically without wandb.

Each train.py cycle is its own run; set WANDB_RUN_GROUP in the loop parent to
group a session's cycles together. Override the mode with the standard
WANDB_MODE env var (online/offline/disabled).
"""

import os
from dataclasses import asdict, is_dataclass


def wandb_enabled(config) -> bool:
    """True iff experiment tracking should be active for this run."""
    if not getattr(config, "use_wandb", False):
        return False
    return os.environ.get("WANDB_MODE", "").lower() != "disabled"


def build_run_config(config) -> dict:
    """Flatten an ExperimentConfig (dataclass or object) to a loggable dict."""
    if is_dataclass(config) and not isinstance(config, type):
        return asdict(config)
    return {k: v for k, v in vars(config).items() if not k.startswith("_")}


def init_run(config, group=None):
    """Start an online-by-default wandb run if enabled, else return None.

    Online matches villa; requires `wandb login`. Set WANDB_MODE=offline to keep
    runs local. If online init fails (e.g. no login/network), fall back to
    offline so a tracking hiccup never crashes a training cycle.
    """
    if not wandb_enabled(config):
        return None
    import wandb

    kwargs = {
        "project": os.environ.get("WANDB_PROJECT", "vesuvius-autoresearch"),
        "group": group or os.environ.get("WANDB_RUN_GROUP"),
        "job_type": "autoresearch_cycle",
        "mode": os.environ.get("WANDB_MODE", "online"),
        "config": build_run_config(config),
        "reinit": True,
    }
    try:
        return wandb.init(**kwargs)
    except Exception as exc:
        print(
            f"Warning: wandb online init failed ({type(exc).__name__}: {exc}); "
            "falling back to offline."
        )
        kwargs["mode"] = "offline"
        return wandb.init(**kwargs)


def watch_model(run, model, log_freq: int = 100):
    """Log parameter + gradient histograms for the model. No-op if no run."""
    if run is None:
        return
    import wandb

    wandb.watch(model, log="all", log_freq=log_freq)


def log(metrics: dict, step=None):
    """Thin wrapper around wandb.log; safe no-op when no active run."""
    try:
        import wandb
    except ImportError:
        return
    if wandb.run is None:
        return
    wandb.log(metrics, step=step)


def log_prediction_image(run, prob_2d, gt_2d, threshold, key="val/prediction"):
    """Log a GT | probability | binarized-at-threshold montage for one patch,
    mirroring villa's mask logging. No-op if no run."""
    if run is None:
        return
    import numpy as np

    import wandb

    prob = np.asarray(prob_2d, dtype=np.float32).squeeze()
    gt = np.asarray(gt_2d, dtype=np.float32).squeeze()
    if prob.ndim != 2 or gt.ndim != 2:
        return
    binary = (prob > threshold).astype(np.float32)
    montage = np.concatenate([gt, prob, binary], axis=1)
    wandb.log({key: wandb.Image(montage, caption="GT | prob | pred@thr")})


def finish_run(run):
    """Close the active run. No-op if no run."""
    if run is None:
        return
    import wandb

    wandb.finish()
