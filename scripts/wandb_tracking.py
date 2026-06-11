"""Opt-in Weights & Biases experiment tracking for the autoresearch loop.

The official ScrollPrize/villa training stacks use wandb; this mirrors that for
our loop. Tracking is OFF unless config.use_wandb is set, and defaults to
OFFLINE mode (local wandb/ files, syncable later with `wandb sync`) so nothing
leaves the machine and no login/network is required. Every helper is a safe
no-op when tracking is disabled, so the loop runs identically without wandb.

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
    """Start an offline-by-default wandb run if enabled, else return None."""
    if not wandb_enabled(config):
        return None
    import wandb

    return wandb.init(
        project=os.environ.get("WANDB_PROJECT", "vesuvius-autoresearch"),
        group=group or os.environ.get("WANDB_RUN_GROUP"),
        job_type="autoresearch_cycle",
        mode=os.environ.get("WANDB_MODE", "offline"),
        config=build_run_config(config),
        reinit=True,
    )


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


def finish_run(run):
    """Close the active run. No-op if no run."""
    if run is None:
        return
    import wandb

    wandb.finish()
