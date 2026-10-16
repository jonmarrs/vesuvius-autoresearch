import copy
import datetime
import glob
import json
import os
import random
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Any

from scripts.loop_control import acquire_lock, describe_run, unsupervised_runs
from scripts.process_supervisor import ProcessSupervisor
from scripts.training.config import ExperimentConfig
from scripts.training.promotion import (
    IncumbentUnavailable,
    check_incumbent,
    first_use_record,
)

LOCK_FILE = "autoresearch.lock"


def load_current_config():
    """The promoted config (config.json), or the defaults before the first one."""
    if os.path.exists(CONFIG_FILE):
        return ExperimentConfig.load(CONFIG_FILE)
    return ExperimentConfig()


def check_lock():
    try:
        return acquire_lock(LOCK_FILE)
    except BlockingIOError:
        print(
            "Another instance of run_autoresearch_loop.py is already running. Exiting."
        )
        sys.exit(1)


supervisor = ProcessSupervisor()


def signal_handler(sig, frame):
    if sig == signal.SIGHUP:
        _leave_closed_terminal()
    if STOP_DEFERRED["active"]:
        # The cycle's outcome is being recorded (the config, the commit, the
        # sprint-log entry): stop once that is done, not halfway through it.
        if STOP_DEFERRED["signal"] is None:
            print(f"\nCaught signal {sig}. Stopping once this cycle is recorded...")
        else:
            print(f"\nCaught signal {sig}. Still recording this cycle; stopping after.")
        STOP_DEFERRED["signal"] = sig
        return
    if STOP_DEFERRED["stopping"]:
        # Stopped again while this stop runs (stop.sh twice, Ctrl-C twice): kill
        # the run at once (the supervisor escalates) and let the first handler
        # settle once and exit. Exiting here cut its settle short.
        print(f"\nCaught signal {sig}. Already stopping; the run is killed.")
        supervisor.stop()
        return
    STOP_DEFERRED["stopping"] = True
    print(f"\nCaught signal {sig}. Cleaning up...")
    supervisor.stop()
    # A stop (stop.sh sends SIGTERM) almost always lands mid-cycle: settle that
    # run as failed now, with its process group dead and config.json not yet
    # promoted, so what happens while the loop is stopped is not mistaken for it.
    if CYCLE_HOLD["active"]:
        note = settle_incumbent(CYCLE_HOLD["held"], failed=True)
        if note:
            print(f"Incumbent: {note}.")
    sys.exit(0)


LOOP_OUTPUT = "autoresearch.out"


def _leave_closed_terminal():
    """After a hangup, writing to the closed terminal fails (EIO): the handler's
    first message raised before it stopped the run, and later ones broke the
    recording of a cycle. From here the loop's output goes to autoresearch.out,
    as start.sh's does."""
    terminal = False
    for stream in (sys.stdout, sys.stderr):
        try:
            terminal = terminal or stream.isatty()
        except (OSError, ValueError, AttributeError):
            terminal = True
    if terminal:
        sys.stdout = sys.stderr = open(LOOP_OUTPUT, "a", buffering=1)


# Define templates for architectural and hyperparameter tweaks
# These now map directly to ExperimentConfig attributes
#
# PINNED-TO-PRODUCTION (2026-06-09): the structure-defining axes below are pinned
# to best_model.pt's values (resenc_unet, base_feat=64, num_blocks=16, num_heads=8,
# num_layers=16, patch_size=64, use_ridges=True). train.py only warm-starts from
# best_model.pt when ALL of these match (see the arch_match check); any other value
# forces "Starting fresh", which a 15-min cycle cannot recover. Pinning them keeps
# every cycle a fine-tune of the production model. To resume free architecture
# search, restore the original `vals` lists (see git history) for these families.
tweak_templates: list[dict[str, Any]] = [
    {"family": "lr", "attr": "lr", "vals": [1e-3, 5e-4, 1e-4, 5e-5, 1e-5]},
    {"family": "wd", "attr": "weight_decay", "vals": [0.1, 0.01, 0.001, 0.0]},
    {
        "family": "capacity",
        "attr": "num_blocks",
        "vals": [16],
    },  # pinned (was [8,10,12,16,20])
    {"family": "attention", "attr": "num_heads", "vals": [8]},  # pinned (was [4,8,12])
    # dropout reaches only gated_unet (InkDetectorOptimized): resenc_unet has no
    # dropout layers (model_wrappers.build_resenc_unet) and timesformer fixes its
    # own. On the pinned resenc_unet, 162 logged cycles (2026-05-03..07-11)
    # tweaked it to no effect, and one was promoted on noise.
    {
        "family": "regularization",
        "attr": "dropout",
        "vals": [0.1, 0.2, 0.0],
        "applies_when": lambda c: getattr(c, "architecture", "gated_unet")
        == "gated_unet",
    },
    # Pinned off (was [True, False]): villa's uint8 warp takes CUDA tensors and
    # patches are read on the CPU, so strict validation refuses it and a cycle
    # that requests it fails before training. It never ran in a logged run
    # (finding 86). Restore True once the warp runs and inference applies it.
    {"family": "preproc", "attr": "use_lasagna", "vals": [False]},
    # target_fiber_source: tests whether the fiber head's BCE target benefits
    # from being real Frangi vesselness (computed from the batch in the training
    # step, train.fiber_target) instead of the cheap inline Sobel-Z gradient. The
    # target feeds the fiber and QC heads only, so the axis needs one of them.
    {
        "family": "preproc",
        "attr": "target_fiber_source",
        "vals": ["sobel_z", "frangi"],
        "applies_when": lambda c: trains_head(c, "fiber") or trains_head(c, "qc"),
    },
    # multi_task_heads: replaces the GenericMultiTaskWrapper's placeholder
    # fiber/qc/st outputs with real Conv3d/Linear heads operating on
    # cat(input, backbone_output). Adds ~5k params, and gradients from
    # loss_fiber/loss_qc/loss_st flow back through the backbone. Without heads
    # the model trains on the ink losses alone (model_wrappers.task_heads).
    # Only resenc_unet's wrapper builds heads from it (resnet3d/i3d backbones
    # give no volume output for them); other architectures ignore it.
    {
        "family": "regularization",
        "attr": "multi_task_heads",
        "vals": [True, False],
        "applies_when": lambda c: getattr(c, "architecture", "gated_unet")
        == "resenc_unet",
    },
    {"family": "batch", "attr": "batch_size", "vals": [8, 16, 24]},
    {"family": "spatial", "attr": "patch_size", "vals": [64]},  # pinned (was [64,96])
    {
        "family": "temporal",
        "attr": "num_layers",
        "vals": [16],
    },  # pinned (was [16,24,32])
    {"family": "width", "attr": "base_feat", "vals": [64]},  # pinned (was [32,64,128])
    {"family": "loss_balance", "attr": "loss_ink_bce", "vals": [0.2, 0.4, 0.6]},
    {"family": "loss_balance", "attr": "loss_ink_dice", "vals": [0.2, 0.4, 0.6]},
    # The fiber and structure-tensor weights reach only a model that trains
    # those heads (see trains_head).
    {
        "family": "loss_balance",
        "attr": "loss_fiber_bce",
        "vals": [0.1, 0.2, 0.3],
        "applies_when": lambda c: trains_head(c, "fiber"),
    },
    {
        "family": "loss_balance",
        "attr": "loss_st",
        "vals": [0.0, 0.1, 0.2],
        "applies_when": lambda c: trains_head(c, "st"),
    },
    {
        "family": "features",
        "attr": "use_ridges",
        "vals": [True],
    },  # pinned (was [True,False])
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
    # Architecture family restricted to candidates with real ST/QC heads. Audit
    # on 2026-05-17 found that lejepa_unet has been a topology regression since
    # the 2026-05-06 flip: skel_dist 27 px vs the May-5 resenc_unet's 1 px
    # (prize gate: <= 2 px). lejepa_unet and timesformer return zeros for the
    # structure-tensor head; lejepa_unet and neural_tracing_vit also return the
    # ink logits as fiber and zeros as QC. resenc_unet has real heads only with
    # multi_task_heads (trains_head, which mirrors each model's task_heads).
    {
        "family": "architecture",
        "attr": "architecture",
        # pinned to the production model so every cycle warm-starts from best_model.pt
        # (was ["gated_unet", "mednext", "neural_tracing_vit"]).
        "vals": ["resenc_unet"],
    },
    # Disabled 2026-06-19: the scroll_augmentations family was starving the search.
    # It carries 9 templates (below), and the bandit weights selection per-template
    # by the family's success_count — so this family had ~9x the structural sampling
    # mass of single-template families, on top of a runaway weight (17.8 vs ~1.0 for
    # every other real family). Yet the aug-ablation study found augmentation is NOT
    # the bottleneck at 64px (both arms ~chance on train AND val); the ceiling is the
    # 64px window regime, not augmentation. The aug_scroll_*_p attrs keep their
    # baseline defaults in config (frozen, not swept). The companion success_count
    # was reset to 1.0 in autoresearch_history.json. Uncomment the block (and re-run
    # the ablation) to re-enable the sweep.
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_decohesion_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_warping_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_squeeze_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_z_dropout_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_intensity_drift_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_sheet_compression_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_thick_slice_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_rician_noise_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # {
    #     "family": "scroll_augmentations",
    #     "attr": "aug_scroll_blank_rectangles_p",
    #     "vals": [0.0, 0.25, 0.5],
    # },
    # Removed 2026-05-17 after audit confirmed this axis has been a no-op since the
    # loop's inception: train.py:742 expects {segment_name}_pseudo.png in the
    # pseudo_label_dir, but no such file has ever existed on disk (the actual
    # files in local_data/pseudo_labels/ are 36 pred_*.png prediction outputs
    # whose names don't match the contract). Both vals (None and
    # "local_data/pseudo_labels") therefore produce bit-identical training that
    # falls back to manual inklabels_filled.png; cycles sampled to this family
    # always REVERTED. Re-add this entry after running
    # scripts/generate_pseudo_labels.py to produce real {segment_name}_pseudo.png
    # files matching the train.py contract, and with use_confidence_weight set
    # alongside: train.py refuses a pseudo-label without it (2026-10-14).
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
# sprint_logs/sprint_log_<when it was started>_<shift>.md
RESUME_MARKER = "## Resumed at"
SHIFT_LOG_NAME = re.compile(
    r"sprint_log_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_(\w+)\.md"
)


def _ends_with_resume_marker(path):
    """Whether the log's last line is a resume marker: a restart since then
    wrote nothing."""
    with open(path, "rb") as log:
        log.seek(0, os.SEEK_END)
        log.seek(max(0, log.tell() - 512))
        lines = [line for line in log.read().splitlines() if line.strip()]
    return bool(lines) and lines[-1].decode(errors="replace").startswith(RESUME_MARKER)


def shift_began(when):
    """The date the shift running at ``when`` began: a night shift (19:00 to
    07:00) past midnight began the evening before."""
    day = when.date()
    return day - datetime.timedelta(days=1) if when.hour < 7 else day


def shift_log_to_resume(previous, shift_tag, now):
    """``previous``, the log the loop last wrote to, if it is this shift's log:
    in sprint_logs/, of the same shift, begun the same day, as its name records.
    A restart within a shift (a crash, a stop and start) then goes on writing
    the shift's record."""
    match = SHIFT_LOG_NAME.fullmatch(os.path.basename(previous))
    if (
        match is None
        or match.group(2) != shift_tag
        or os.path.dirname(os.path.normpath(previous)) != "sprint_logs"
        or not os.path.isfile(previous)
    ):
        return None
    try:
        started = datetime.datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M-%S")
    except ValueError:  # an impossible date: not a name the loop wrote
        return None
    # Started within its shift's hours: a log begun as the shift ended (the
    # hour and the time read a moment apart) is not the next one's.
    if (7 <= started.hour < 19) != (shift_tag == "day_shift"):
        return None
    return previous if shift_began(started) == shift_began(now) else None


# Pre-flight VRAM estimate (complexity heuristic, Sprint 023 refined). The
# reference config (base_feat 64, num_layers 24, patch_size 64, batch_size 8,
# num_blocks 16; ~14 GB) scores 1.0, and the cap allows 50% above it (~21 GB).
VRAM_COMPLEXITY_CAP = 1.5


def complexity_score(config) -> float:
    feat = config.base_feat / 64.0
    depth = config.num_layers / 24.0
    patch = config.patch_size / 64.0
    batch = config.batch_size / 8.0
    blocks = config.num_blocks / 16.0
    # Convolutions and activations grow with the patch area, attention with its
    # square; attention is weighted 0.4.
    linear = feat * depth * patch**2 * batch * blocks
    attention = depth * patch**4 * batch * blocks
    return 0.6 * linear + 0.4 * attention


def _tweaked(config, attr, val):
    candidate = copy.copy(config)
    setattr(candidate, attr, val)
    return candidate


# Mirrors each model's declared task_heads (model_wrappers.task_heads), without
# building one (the loop does not import torch): tests/test_task_heads.py checks
# they agree. resnet3d/i3d wrap backbones without a volume output, so they have
# no heads, and their wrapper refuses multi_task_heads.
_ARCHITECTURES_WITHOUT_HEADS = {"lejepa_unet", "neural_tracing_vit", "resnet3d", "i3d"}


def trains_head(config, head):
    """Whether a run of this config trains the auxiliary head (fiber, qc, st)."""
    architecture = getattr(config, "architecture", "gated_unet")
    if architecture in _ARCHITECTURES_WITHOUT_HEADS:
        return False
    if architecture == "resenc_unet":
        return bool(getattr(config, "multi_task_heads", False))
    if architecture == "timesformer":
        return head != "st"
    return True


def tweak_proposals(config, cap=None):
    """Split each enabled axis's changed values by the VRAM cap, in one pass.

    Returns the active templates, holding only values whose config fits under
    the cap, and (attr, value, estimate) for each value over it. The cap is a
    hard limit: a baseline already over it is offered only tweaks that bring
    it under.
    """
    cap = VRAM_COMPLEXITY_CAP if cap is None else cap
    active, excluded = [], []
    for template in tweak_templates:
        if not template.get("applies_when", lambda _c: True)(config):
            continue
        attr = template["attr"]
        fits = []
        for v in template["vals"]:
            if v == getattr(config, attr):
                continue
            score = complexity_score(_tweaked(config, attr, v))
            if score <= cap:
                fits.append(v)
            else:
                excluded.append((attr, v, score))
        if fits:
            active.append({**template, "vals": fits})
    return active, excluded


BENCHMARK_URI = "local_data/PHercParis2Fr143/surface_volume.zarr"


def template_weights(templates, success_counts):
    """Give each family its stated weight regardless of its number of axes."""
    sizes = Counter(t["family"] for t in templates)
    return [success_counts[t["family"]] / sizes[t["family"]] for t in templates]


def load_history():
    """The family weights; 1 for a family not yet recorded.

    An unreadable file is moved aside rather than left to be overwritten with
    the defaults at the end of the first cycle (save_history runs every cycle).
    """
    counts = defaultdict(lambda: 1)
    if not os.path.exists(HISTORY_FILE):
        return counts
    try:
        with open(HISTORY_FILE) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"expected an object, got {type(data).__name__}")
        counts.update(data)
    except (OSError, ValueError) as e:
        aside = f"{HISTORY_FILE}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}"
        try:
            os.replace(HISTORY_FILE, aside)
            kept = f"moved it to {aside}"
        except OSError as move_error:
            kept = f"could not move it aside ({move_error})"
        print(
            f"Warning: {HISTORY_FILE} is unreadable ({e}); {kept}. Starting from "
            "weight 1 for every family."
        )
    return counts


def save_history(counts):
    """Write the family weights atomically: a stop mid-write leaves the old file."""
    try:
        _write_json_atomic(HISTORY_FILE, dict(counts), indent=4)
    except OSError as e:
        print(f"Warning: Could not save history: {e}")


def _write_json_atomic(path, data, **dump_options):
    """A temporary file, synced, then renamed over path, keeping path's mode
    (mkstemp creates 0600). A stop or crash leaves the old file or the new."""
    directory = os.path.dirname(os.path.abspath(path))
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=directory
        )
        if os.path.exists(path):
            os.fchmod(fd, stat.S_IMODE(os.stat(path).st_mode))
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, **dump_options)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


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
    # Atomically, like the history: written in place, a stop mid-write left a
    # truncated file, which the next start read as no recent configs at all.
    try:
        _write_json_atomic(RECENT_CONFIGS_FILE, configs[-20:])
    except Exception as e:
        print(f"Warning: Could not save {RECENT_CONFIGS_FILE}: {e}")


INCUMBENT = "best_model.pt"
# A hard link to the incumbent, kept while a training run may replace it.
INCUMBENT_HELD = ".best_model.pt.held"
# The cycle in flight, for the signal handler: whether it holds, and what.
CYCLE_HOLD: dict[str, Any] = {"active": False, "held": None, "logs": {}}
# Set from a run's end until its cycle is recorded; a stop then waits for it.
# "stopping": a stop is being handled, and a repeated one only kills the run.
STOP_DEFERRED: dict[str, Any] = {"active": False, "signal": None, "stopping": False}
# The rows train.py appends when it promotes, before it writes its result.
PROMOTION_LOGS = ("results.tsv", "prize_readiness.tsv")


def hold_incumbent():
    """Hard-link the incumbent before a training run, at no copy cost: train.py
    promotes by os.replace, so the link keeps the old checkpoint. True if there
    was one to hold, False if there was none, None if it could not be held."""
    if os.path.lexists(INCUMBENT_HELD):
        os.remove(INCUMBENT_HELD)
    held: bool | None = True
    if not os.path.exists(INCUMBENT):
        held = False
    else:
        try:
            os.link(INCUMBENT, INCUMBENT_HELD)
        except OSError as e:
            print(f"Warning: could not hold {INCUMBENT} for this cycle ({e}).")
            held = None
    CYCLE_HOLD.update(active=True, held=held, logs=_log_ends())
    return held


def _log_ends():
    """Each promotion log's bytes, or None where there is none. The logs are
    small (a row per promotion); content, not the inode, tells whether a log was
    only appended to, since a file git or an operator recreates can get its old
    inode number back."""
    ends = {}
    for path in PROMOTION_LOGS:
        try:
            with open(path, "rb") as f:
                ends[path] = f.read()
        except FileNotFoundError:
            ends[path] = None
        except OSError as e:
            print(f"Warning: could not read {path} before the run ({e}).")
    return ends


def _read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _undo_promotion_rows(before):
    """Put each promotion log back as it was before the run, so the reports read
    no promotion the loop undid. A log that still begins with its old bytes is
    cut to them; one the run created is removed; one append_tsv_row rotated
    (moved aside for a new header) is moved back. Any other change is left."""
    undone, left = [], []
    for path, old in before.items():
        try:
            if not os.path.exists(path):
                continue
            now = _read_bytes(path)
            if old is None:
                os.remove(path)
                undone.append(path)
            elif now.startswith(old):
                if len(now) > len(old):
                    os.truncate(path, len(old))
                    undone.append(path)
            else:
                stem, ext = os.path.splitext(path)
                pattern = f"{glob.escape(stem)}.until-*{ext}"
                rotated = [
                    a for a in sorted(glob.glob(pattern)) if _read_bytes(a) == old
                ]
                if rotated:
                    os.replace(rotated[-1], path)
                    undone.append(path)
                else:
                    left.append(path)
        except OSError as e:
            print(f"Warning: could not restore {path} ({e}).")
            left.append(path)
    return undone, left


def settle_incumbent(held, failed):
    """After a run: a failed one promotes neither the config nor the model.

    train.py replaces best_model.pt before it writes run_result.json and exits,
    so a run that fails after that point (an exit error, the timeout, a stop)
    left a model no config or commit records, which the next cycle would
    warm-start from and be compared with. Such a model is moved aside and the
    held incumbent put back. Returns a note for the sprint log, or None.
    """
    logs = CYCLE_HOLD["logs"]
    CYCLE_HOLD.update(active=False, logs={})
    if held and not os.path.exists(INCUMBENT_HELD):
        print(f"Warning: {INCUMBENT_HELD} disappeared during the cycle; not settled.")
        held = None
    if held:
        replaced = not (
            os.path.exists(INCUMBENT) and os.path.samefile(INCUMBENT, INCUMBENT_HELD)
        )
    else:
        replaced = held is False and os.path.exists(INCUMBENT)
    note = None
    if failed and replaced:
        aside = None
        if os.path.exists(INCUMBENT):
            stamp = time.strftime("%Y%m%d-%H%M%S")
            aside = f"{INCUMBENT}.failed-run-{stamp}"
            n = 1
            while os.path.lexists(aside):
                n += 1
                aside = f"{INCUMBENT}.failed-run-{stamp}-{n}"
            os.replace(INCUMBENT, aside)
        if held:
            os.replace(INCUMBENT_HELD, INCUMBENT)
        undone, left = _undo_promotion_rows(logs)
        note = (
            f"the run wrote {INCUMBENT} and then failed; "
            + ("the incumbent was restored" if held else "there was none before it")
            + (f", and the run's model kept as {aside}" if aside else "")
            + (f"; its rows were removed from {', '.join(undone)}" if undone else "")
            + (
                f"; {', '.join(left)} changed otherwise during the run, left as is"
                if left
                else ""
            )
        )
    if os.path.lexists(INCUMBENT_HELD):
        os.remove(INCUMBENT_HELD)
    return note


def leftover_hold():
    """A reason not to start, if a loop ended mid-cycle without settling its run
    (a kill or power loss; a stop settles). Released if best_model.pt is still
    the held file. Otherwise it cannot be told whether that run or the operator
    changed best_model.pt since, so the choice is left to the operator."""
    if not os.path.lexists(INCUMBENT_HELD):
        return None
    if os.path.exists(INCUMBENT) and os.path.samefile(INCUMBENT, INCUMBENT_HELD):
        os.remove(INCUMBENT_HELD)
        return None
    return (
        f"{INCUMBENT_HELD} remains from a loop that ended mid-cycle without settling "
        f"its run, and {INCUMBENT} has changed since that cycle began (the run "
        "replaced it, or it was changed by hand). To keep the current "
        f"{INCUMBENT}: rm {INCUMBENT_HELD}. To restore the incumbent from before "
        f"that cycle: mv {INCUMBENT_HELD} {INCUMBENT}, and remove that run's last "
        f"row from {' and '.join(PROMOTION_LOGS)} if it added one."
    )


TRAIN_SCRIPT = "scripts/training/train.py"
# The longest a supervised training run may last: the night budget plus the
# margin of its timeout (default_budget + 300 in main).
LONGEST_RUN_SECONDS = 3600 + 300


def unsupervised_runs_reason(running):
    """Stops a loop's own run that has outlived any cycle's timeout, as its
    supervisor would have, and says why the loop does not start."""
    lines = []
    for pid, age, own in running:
        lines.append(describe_run(pid, age, own))
        if own and age is not None and age > LONGEST_RUN_SECONDS:
            try:
                os.killpg(pid, signal.SIGTERM)
                lines[-1] += ", stopped now: past any cycle's timeout"
            except OSError:
                pass
    return (
        "a training run is going in this checkout outside any loop: "
        + "; ".join(lines)
        + ". A loop that ended without stopping its run (killed, or its terminal "
        "closed) leaves it going, and a run started here by hand writes the same "
        "files: either can still replace best_model.pt and write run_result.json. "
        "The watchdog tries again on its next tick. ./stop.sh stops the runs a "
        "loop or ablation started (it also pauses the watchdog); a run started "
        "by hand: kill -TERM <PID>. If it promoted, the hold then needs your call."
    )


def exit_description(returncode):
    if returncode is not None and returncode < 0:
        try:
            return f"was killed by {signal.Signals(-returncode).name}"
        except ValueError:
            pass
    return f"exited with code {returncode}"


# The files a promotion changes, and the only ones its commit records.
PROMOTION_FILES = (CONFIG_FILE, INCUMBENT, HISTORY_FILE)


def commit_promotion(message):
    """Commit a promotion: exactly PROMOTION_FILES, whatever else is staged.

    `git add ... && git commit` committed the whole index, so changes the
    operator had staged went in under "improved model" (a 248-line
    vesuvius_loader.py change on 2026-04-25), as did reports/figures/, which the
    loop does not write (35 of 50 promotion commits). `git commit --only` takes
    just these paths and leaves the rest of the index as it was; a failed commit
    unstages them again. Returns True, or why the commit failed.
    """
    try:
        code, output = _run_git("add", "--", *PROMOTION_FILES)
        if code != 0:
            return f"git add {_git_failure(code, output)}"
        code, output = _run_git(
            "commit", "--only", "-m", message, "--", *PROMOTION_FILES
        )
        if code != 0:
            # Or the operator's next commit would take them in.
            _run_git("reset", "-q", "--", *PROMOTION_FILES)
            return f"git commit {_git_failure(code, output)}"
    except OSError as e:
        return f"git could not be run ({e})"
    return True


def _run_git(*args, timeout=300):
    """Run git in a process group of its own, with its hooks (a terminal's
    Ctrl-C reaches neither). A hang is stopped with SIGTERM to the group, on
    which git removes its index.lock (a SIGKILL would leave it, failing every
    later git command), then SIGKILL. Signalling git alone left a hook holding
    the output pipes, and the wait for them had no end, so a stop deferred
    behind it never came."""
    process = subprocess.Popen(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        for sig, grace in ((signal.SIGTERM, 30), (signal.SIGKILL, 10)):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
            try:
                process.communicate(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                pass
        else:  # a descendant that left the group still holds the pipes
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        return None, f"timed out after {timeout} s"
    return process.returncode, f"{err}\n{out}"


def _git_failure(code, output):
    """The reason git gives: its fatal/error lines and failed hooks, not only
    the last line (pre-commit ends on its stash-restore message)."""
    if code is None:
        return output
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    key = [
        line
        for line in lines
        if line.startswith(("fatal:", "error:", "- hook id:"))
        or line.endswith("Failed")
    ]
    reason = " | ".join((key or lines)[-3:])
    return f"exited {code}" + (f": {reason}" if reason else "")


def last_log_line(path="run.log", limit=300):
    """The run log's last non-empty line, for a failed cycle's sprint log entry."""
    try:
        with open(path, errors="replace") as f:
            lines = [line.strip() for line in f.readlines()[-50:] if line.strip()]
    except OSError:
        return None
    return lines[-1][:limit] if lines else None


def main():
    """Entry point for the autonomous Day/Night Shift autoresearch loop.

    All process-level side effects (file lock acquisition, signal handler
    registration, directory creation, sprint-log writes) live inside this
    function so that ``from run_autoresearch_loop import tweak_templates``
    is a side-effect-free import. The previous module-level layout caused
    any importer (test runner, syntax-check, IDE introspection) to acquire
    the lock and write a sprint-log header; see 2026-05-16 incident notes.
    """
    # The controller can be imported without loading torch or mutating training
    # modules. Resolve all run artifacts relative to this checkout.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    lock_fp = check_lock()  # noqa: F841 (kept open for the duration of the process)
    if os.path.exists(".loop_paused"):
        print("Autoresearch is paused. Use ./start.sh to resume.")
        return

    # Before the hold: a run still going may yet replace best_model.pt.
    running = unsupervised_runs(".")
    if running:
        print(f"Not starting: {unsupervised_runs_reason(running)}")
        return

    reason = leftover_hold()
    if reason:
        print(f"Not starting: {reason}")
        return

    # The incumbent must be comparable before any GPU time is spent: train.py
    # refuses to promote over an unreadable or differently-scored best_model.pt,
    # so a shift started anyway would revert every cycle. The watchdog restarts
    # a returned loop, which reprints this until the operator acts.
    try:
        # The protocol includes config.json's depth band: an incumbent scored on
        # other slices must be re-scored before a candidate can be compared, and
        # so must one scored on other validation inputs (label file, mask,
        # patches.json; promotion.validation_inputs_fingerprint).
        config = load_current_config()
        best_val_f1, inputs_known = check_incumbent(
            "best_model.pt", config.val_uri, config.depth_band
        )
    except (IncumbentUnavailable, ValueError) as exc:
        # ValueError: config.json fails ExperimentConfig's checks (e.g. depth_band).
        print(f"Not starting: {exc}")
        return
    print(
        f"Starting with incumbent val_f1 from best_model.pt: {best_val_f1:.6f}"
        if best_val_f1 > float("-inf")
        else "No best_model.pt yet; the first lift-positive cycle bootstraps it."
    )
    if inputs_known == "recorded now":
        print(
            "best_model.pt records no validation-input fingerprint (scored before "
            "2026-10-14). The current inputs were recorded in "
            f"{first_use_record('best_model.pt')}, and candidates are compared on "
            "them until it is re-scored or replaced."
        )
    STOP_DEFERRED.update(active=False, signal=None, stopping=False)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    # A closed terminal (SIGHUP) stops the loop like stop.sh, not at once with
    # its run left going. start.sh runs it under nohup, which ignores SIGHUP.
    if signal.getsignal(signal.SIGHUP) is not signal.SIG_IGN:
        signal.signal(signal.SIGHUP, signal_handler)

    success_counts: dict[str, float] = load_history()

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
    shift_tag = shift_name.lower().replace(" ", "_")
    now = datetime.datetime.now()
    log_filename = f"sprint_logs/sprint_log_{now:%Y-%m-%d_%H-%M-%S}_{shift_tag}.md"

    # After a restart within the shift, go on with its log. The check used to
    # look for "day shift" in a name spelled "day_shift", so every restart
    # began another log; and a night shift past midnight compared the date.
    if os.path.exists(CURRENT_LOG_PTR):
        with open(CURRENT_LOG_PTR) as f:
            resumed = shift_log_to_resume(f.read().strip(), shift_tag, now)
        if resumed:
            log_filename = resumed
            print(f"Resuming existing shift log: {log_filename}")

    with open(CURRENT_LOG_PTR, "w") as f:
        f.write(log_filename)

    print(f"--- {shift_name} STARTING AT {time.strftime('%H:%M:%S')} ---")
    print(f"Logging to: {log_filename}")
    sys.stdout.flush()

    if not os.path.exists(log_filename):
        with open(log_filename, "w") as log:
            log.write(f"# {shift_name.title()} Sprint - {time.strftime('%Y-%m-%d')}\n")
            log.write(f"- **Start Time**: {time.strftime('%H:%M:%S')}\n")
            log.write(
                f"- **Goal**: Monotonic val_f1 optimization (honest F1, AP-lift gated) via {default_budget // 60}-min cycles (Config-Driven).\n\n"
            )
    elif not _ends_with_resume_marker(log_filename):
        # Once: a restart that runs no cycle (nothing under the VRAM cap) is
        # restarted by the watchdog every few minutes, and adds nothing else.
        with open(log_filename, "a") as log:
            log.write(
                f"\n{RESUME_MARKER} {time.strftime('%H:%M:%S')} "
                "(the loop restarted; its cycles count from 1 again)\n\n"
            )

    env = os.environ.copy()
    i = 0
    recent_configs = load_recent_configs()
    last_excluded: list = []

    while True:
        i += 1
        # (best_val_f1 display refresh happens on SUCCESS below, from
        # run_result.json — results.tsv's frozen schema has no val_f1 column.)

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
                # The benchmark's map: predict.py writes it beside its figure in
                # reports/, at the z it centres (recorded in its _meta.json).
                print(
                    f"Run: uv run scripts/launch_proofreader.py --volume {BENCHMARK_URI} "
                    "--predictions reports/pred_<z>_1000_1000_64x64_ink.zarr"
                )
                print("=" * 60 + "\n")

            break

        # The validation inputs can change under a running shift (a refined label
        # file written beside the fragment): stop before training on a sample the
        # incumbent's score does not describe. The watchdog's restart then
        # reprints the reason as "Not starting" until the incumbent is re-scored.
        try:
            current = load_current_config()
            if i > 1:  # cycle 1 follows the startup check
                check_incumbent("best_model.pt", current.val_uri, current.depth_band)
        except (IncumbentUnavailable, ValueError) as exc:
            print(f"Stopping before cycle {i}: {exc}")
            with open(log_filename, "a") as log:
                log.write(f"- **Stopped before cycle {i}**: {exc}\n\n")
            break

        # Every cycle is a single tweak of the promoted config. The every-10th-cycle
        # "GP-winner baseline" (timesformer, patch 256) was removed 2026-10-12: the
        # VRAM estimate (complexity_score) scored it 74.7 > 1.5, so it was always skipped, and
        # had it run it could have been promoted, replacing config.json with a
        # from-scratch timesformer. Run-to-run calibration is scripts/f1_noise_probe.py.

        # Conditional-axis gating: drop templates whose `applies_when`
        # predicate is False under the current baseline config (e.g.
        # ridge_sigma when use_ridges=False). Avoids spending cycles on
        # axes that produce identical results to the baseline.
        baseline_for_gate = load_current_config()
        # The VRAM estimate filters values before sampling, so a rejected value
        # never takes a cycle number, a dedup slot or a decay step.
        active_templates, excluded = tweak_proposals(baseline_for_gate)
        baseline_score = complexity_score(baseline_for_gate)
        if baseline_score > VRAM_COMPLEXITY_CAP:
            note = (
                "every value that leaves config.json over it "
                f"(config.json scores {baseline_score:.2f})"
            )
        else:
            note = ", ".join(f"{a}={v} ({s:.2f})" for a, v, s in excluded) or "none"
        if not active_templates:
            # Stdout only, like "Not starting": the watchdog restarts the loop every
            # few minutes, and each restart would add the same lines to the sprint log.
            print(
                f"No tweak differs from the baseline within VRAM cap "
                f"{VRAM_COMPLEXITY_CAP} (excluded: {note}). Ending sprint."
            )
            break
        if excluded != last_excluded:
            print(f"VRAM cap {VRAM_COMPLEXITY_CAP} excludes: {note}")
            with open(log_filename, "a") as log:
                log.write(f"- **VRAM cap {VRAM_COMPLEXITY_CAP} excludes**: {note}\n\n")
            last_excluded = excluded

        # Families this cycle could sample; they decay once it is scored (below).
        families = [t["family"] for t in active_templates]
        weights = template_weights(active_templates, success_counts)

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
            test_config = load_current_config()
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

        training_returncode = None
        # Why the cycle produced no result, and its run's last log line.
        failure = log_line = None
        held = hold_incumbent()
        try:
            with open("run.log", "a") as f:
                f.write(f"\n\n--- {shift_name} CYCLE {i}: {tweak_name} ---\n")
                f.flush()

                # Robust Process Management: use session group to kill all descendants
                env_unbuffered = env.copy()
                env_unbuffered["PYTHONUNBUFFERED"] = "1"
                # Ensure moved modules and dependencies are discoverable
                current_pp = env_unbuffered.get("PYTHONPATH", "")
                env_unbuffered["PYTHONPATH"] = (
                    f".:villa/foundation/datasets/fibers-dataset:{current_pp}"
                )

                # Preflight smoke gate: build the model and run one
                # forward/backward in seconds so a broken architecture fails
                # fast here instead of burning the full training budget.
                f.write("--- PREFLIGHT SMOKE CHECK ---\n")
                f.flush()
                try:
                    preflight = supervisor.run(
                        [
                            "uv",
                            "run",
                            "python",
                            "-u",
                            TRAIN_SCRIPT,
                            "--config",
                            TEMP_CONFIG,
                            "--smoke",
                        ],
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        env=env_unbuffered,
                        text=True,
                        timeout=300,
                    )
                    preflight_ok = preflight.returncode == 0
                    if not preflight_ok:
                        failure = f"preflight {exit_description(preflight.returncode)}"
                except subprocess.TimeoutExpired:
                    preflight_ok = False
                    failure = "preflight timed out after 300 s"
                if not preflight_ok:  # before the loop's own markers below
                    f.flush()
                    log_line = last_log_line()
                    if failure.startswith("preflight timed out"):
                        f.write("PREFLIGHT TIMED OUT — skipping training.\n")
                f.flush()

                if not preflight_ok:
                    f.write("PREFLIGHT FAILED — skipping training for this cycle.\n")
                    f.flush()
                    print(
                        f"Cycle {i}: PREFLIGHT FAILED — skipping 60-min run "
                        "(model did not pass forward/backward)."
                    )
                    sys.stdout.flush()
                else:
                    try:
                        training = supervisor.run(
                            [
                                "uv",
                                "run",
                                "python",
                                "-u",
                                TRAIN_SCRIPT,
                                "--config",
                                TEMP_CONFIG,
                            ],
                            stdout=f,
                            stderr=subprocess.STDOUT,
                            env=env_unbuffered,
                            text=True,
                            timeout=default_budget + 300,
                        )
                        training_returncode = training.returncode
                    except subprocess.TimeoutExpired:
                        print(f"Cycle {i} timed out. Process group stopped.")
                        failure = f"killed at the {default_budget + 300} s timeout"
        except Exception as e:
            print(f"Subprocess error in cycle {i}: {e}")
            failure = f"could not be run ({type(e).__name__}: {e})"

        # From the run's end until the cycle is recorded, a stop (stop.sh) waits.
        # Exiting halfway settled a clean run as failed, or left a promoted
        # config and model without their commit or sprint-log entry, or with the
        # three files staged but not committed. A stop during the run is not
        # deferred: the supervisor has returned by now.
        STOP_DEFERRED.update(active=True, signal=None)
        val_bpb = train_loss = params = vram = vps = val_f1 = "N/A"
        skipped_updates = 0
        promotion_blocked = None
        is_success = False
        is_crash = False
        oom_detected = False

        if training_returncode != 0 or not os.path.exists("run_result.json"):
            is_crash = True
            # Promotion requires a clean exit as well as a result (2026-10-01).
            if failure is None:
                failure = (
                    "wrote no run_result.json"
                    if training_returncode == 0
                    else exit_description(training_returncode)
                )
            if os.path.exists("run_result.json"):  # deleted before the run
                failure += " after writing run_result.json"
            log_line = log_line or last_log_line()
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
                val_bpb = res.get("val_bpb", "N/A")  # type: ignore[attr-defined]
                train_loss = res.get("train_loss", "N/A")  # type: ignore[attr-defined]
                params = res.get("num_params_M", "N/A")  # type: ignore[attr-defined]
                vram = res.get("peak_vram_mb", "N/A")  # type: ignore[attr-defined]
                vps = res.get("throughput_Mvps", "N/A")  # type: ignore[attr-defined]
                val_f1 = res.get("val_f1", "N/A")  # type: ignore[attr-defined]
                is_success = res.get("is_success", False)  # type: ignore[attr-defined]
                promotion_blocked = res.get("promotion_blocked")  # type: ignore[attr-defined]
                skipped_updates = res.get("skipped_updates", 0)  # type: ignore[attr-defined]
            except Exception as e:
                print(f"Error reading run_result.json: {e}")
                is_crash = True
                failure = f"run_result.json is unreadable ({e})"
        incumbent_note = settle_incumbent(held, failed=is_crash)

        # Success-biased decay: every scored cycle decays all the families it
        # could have sampled, so a family that stops producing promotions loses
        # its dominance; a promotion then rewards its family. A crash (or failed
        # preflight, or a stop mid-run) ran no experiment and changes nothing, so
        # a broken environment cannot wear the weights down. Saved now, before
        # the config files move: REVERTED, the usual outcome, used to leave the
        # decay unsaved, and every restart put the old weights back.
        if not is_crash:
            for f in set(families):
                success_counts[f] = max(1.0, success_counts[f] * 0.95)
        if is_success:
            success_counts[family] += 1
        save_history(success_counts)

        if is_success:
            status = "SUCCESS"
            # Promote temp config to main config
            os.rename(TEMP_CONFIG, CONFIG_FILE)
        else:
            # Neither a crash nor a non-improvement is rewarded.
            status = (
                ("CRASHED (OOM)" if oom_detected else "CRASHED")
                if is_crash
                else "REVERTED"
            )
            if os.path.exists(TEMP_CONFIG):
                os.remove(TEMP_CONFIG)

        # Committed before the cycle is logged, so a failure is in its entry.
        commit_failure = None
        if is_success:
            committed = commit_promotion(
                f"{shift_name}: {tweak_name} improved model to val_f1 {val_f1}"
            )
            if committed is not True:
                commit_failure = committed

        with open(log_filename, "a") as log:
            log.write(f"## Cycle {i}: {tweak_name} ({status})\n")
            log.write(f"- **Timestamp**: {time.strftime('%H:%M:%S')}\n")
            log.write(f"- **Config**: {cfg_str}\n")
            log.write(
                f"- **Stats**: val_f1: {val_f1}, val_bpb: {val_bpb}, loss: {train_loss}, params: {params}M, vram: {vram}MB, speed: {vps}Mvps\n"
            )
            if skipped_updates:
                # Steps train.py did not apply (non-finite loss or gradient).
                log.write(f"- **Skipped updates**: {skipped_updates}\n")

            result_msg = "No improvement detected. Config reverted."
            if promotion_blocked:
                result_msg = f"Promotion blocked: {promotion_blocked}. Config reverted."
            if is_success:
                result_msg = "Improvement detected. Config updated."
            elif is_crash:
                result_msg = f"Training crashed ({'out of memory' if oom_detected else failure}). No success reward; family remains eligible for exploration."
                if log_line and not oom_detected:
                    log.write(
                        f"- **Last log line**: `{log_line.replace('`', chr(39))}`\n"
                    )
            if incumbent_note:
                log.write(f"- **Incumbent**: {incumbent_note}.\n")
            if commit_failure:
                log.write(
                    f"- **Commit**: failed ({commit_failure}); {CONFIG_FILE}, "
                    f"{INCUMBENT} and {HISTORY_FILE} are promoted on disk but "
                    "not committed.\n"
                )

            log.write(f"- **Result**: {result_msg}\n\n")
            log.flush()

        if is_success:
            print(f"IMPROVEMENT FOUND! (val_f1: {val_f1}) Committing config.")
            if isinstance(val_f1, (int, float)):
                best_val_f1 = val_f1  # display tracker; authority is train.py
            if commit_failure:
                print(f"Warning: the promotion was not committed ({commit_failure}).")
        elif is_crash:
            print(
                f"CYCLE CRASHED ({'OOM' if oom_detected else failure}). Reverting but keeping family weight."
            )
            if incumbent_note:
                print(f"Incumbent: {incumbent_note}.")
        else:
            best_str = (
                f"{best_val_f1:.6f}" if best_val_f1 > float("-inf") else "none yet"
            )
            print(f"No improvement. (val_f1: {val_f1}, best was: {best_str})")
        STOP_DEFERRED["active"] = False
        if STOP_DEFERRED["signal"] is not None:
            signal_handler(STOP_DEFERRED["signal"], None)

        # Benchmark Inference Step (Every 5 cycles).
        # Uses subprocess.run (not os.system) so a predict.py crash surfaces
        # as a visible warning rather than silently swallowing the failure.
        if i % 5 == 0:
            print(f"Cycle {i}: Running Benchmark Inference...")
            benchmark_path = f"reports/benchmark_v210_cycle{i}.png"
            benchmark_cmd = [
                "uv",
                "run",
                "scripts/inference/predict.py",
                "--uri",
                BENCHMARK_URI,
                # No --z: predict.py centres the checkpoint's window in its
                # recorded depth_band on the checkpoint's own volumes (today
                # BENCHMARK_URI is config.json's val_uri, so it is one), else in
                # the volume's depth; it says so in the log when it drops a band.
                "--y",
                "1000",
                "--x",
                "1000",
                "--output_img",
                benchmark_path,
            ]
            # Ensure moved modules and dependencies are discoverable
            bench_env = env.copy()
            current_pp = bench_env.get("PYTHONPATH", "")
            bench_env["PYTHONPATH"] = (
                f".:villa/foundation/datasets/fibers-dataset:{current_pp}"
            )

            try:
                supervisor.run(benchmark_cmd, check=True, timeout=600, env=bench_env)
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
    # Force unbuffered output
    import io
    import os
    import sys

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, write_through=True)

    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR in main loop: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
