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

import math
import os
from dataclasses import asdict, is_dataclass

# The tracking calls that have failed in this process, each reported once.
_REPORTED: set[str] = set()


def _swallow(what: str, exc: Exception) -> None:
    """Report a tracking error and go on. Raised, it ended the run: one in the
    validation log or image came before run_result.json, so a scored cycle,
    and any promotion, was discarded over tracking."""
    if what not in _REPORTED:
        _REPORTED.add(what)
        print(
            f"Warning: wandb {what} failed ({type(exc).__name__}: {exc}); the run "
            "goes on, and later failures of it are not printed."
        )


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
    offline so a tracking hiccup never crashes a training cycle. If wandb
    cannot be imported, or the offline init fails too, the run goes untracked
    with a warning: both used to raise, before the first training step.
    """
    if not wandb_enabled(config):
        return None
    try:
        import wandb
    except ImportError as exc:
        print(
            f"Warning: use_wandb is set but wandb cannot be imported ({exc}); "
            "this run is not tracked."
        )
        return None

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
        failure = exc
    if kwargs["mode"] != "offline":
        print(
            f"Warning: wandb {kwargs['mode']} init failed ({type(failure).__name__}: "
            f"{failure}); falling back to offline."
        )
        kwargs["mode"] = "offline"
        try:
            return wandb.init(**kwargs)
        except Exception as exc:
            failure = exc
    print(
        f"Warning: wandb offline init failed ({type(failure).__name__}: {failure}); "
        "this run is not tracked."
    )
    return None


def watch_model(run, model, log_freq: int = 100):
    """Log parameter + gradient histograms for the model. No-op if no run."""
    if run is None:
        return
    import wandb

    try:
        wandb.watch(model, log="all", log_freq=log_freq)
    except Exception as exc:
        _swallow("watch", exc)


def log(metrics: dict, step=None):
    """Thin wrapper around wandb.log; safe no-op when no active run."""
    try:
        import wandb
    except ImportError:
        return
    if wandb.run is None:
        return
    try:
        wandb.log(metrics, step=step)
    except Exception as exc:
        _swallow("log", exc)


def selection_metrics(*, val_f1, threshold, lift, roc_auc, incumbent, is_success):
    """What a cycle is selected on (train.promotion_decision: val_f1 gated by AP
    lift) and its context, under run_result.json's names. The incumbent's val_f1
    is left out when there is none (-inf) or it cannot be compared (NaN).

    The validation log was wired on 2026-06-10, before the loop came to select
    on these (2026-07-11), and never carried them."""
    metrics = {
        "val/val_f1": val_f1,
        "val/val_f1_threshold": threshold,
        "val/ap_prevalence_lift": lift,
        "val/roc_auc": roc_auc,
        "val/is_success": bool(is_success),
    }
    if math.isfinite(incumbent):
        metrics["val/incumbent_val_f1"] = incumbent
    return metrics


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
    try:
        wandb.log({key: wandb.Image(montage, caption="GT | prob | pred@thr")})
    except Exception as exc:
        _swallow("image log", exc)


def finish_run(run):
    """Close the active run. No-op if no run.

    A failure here is reported, not raised: train.py calls it after writing
    run_result.json, and the loop counts a non-zero exit as a failed cycle,
    which would discard a scored (or promoted) result over a tracking error.
    """
    if run is None:
        return
    import wandb

    try:
        wandb.finish()
    except Exception as exc:
        print(f"Warning: wandb.finish failed ({type(exc).__name__}: {exc}).")
