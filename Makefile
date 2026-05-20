# Vesuvius Autoresearch — common dev tasks.
#
# All targets run inside the project's uv-managed venv. If `uv` is not on
# PATH, install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

.PHONY: help install smoke test reeval shift clean clean-cache check-deps

help:
	@echo "Common targets:"
	@echo "  make install      uv sync — install / update project dependencies"
	@echo "  make smoke        run scripts/smoke_test.py (CPU-only, ~20s)"
	@echo "  make test         alias for smoke"
	@echo "  make reeval       re-evaluate best_model.pt under today's code path"
	@echo "  make shift        spawn an autoresearch bandit shift in background"
	@echo "  make check-deps   verify GPU + key imports"
	@echo "  make clean        remove transient stdout logs (keeps sprint_logs/)"
	@echo "  make clean-cache  also remove __pycache__ and valid_coords_*.npy"

install:
	uv sync

smoke:
	CUDA_VISIBLE_DEVICES="" uv run python scripts/smoke_test.py

test: smoke

reeval:
	uv run python scripts/reevaluate_best_model.py

# Spawn a shift via nohup so it survives terminal disconnect. The loop
# auto-detects DAY (07-19 PT) vs NIGHT (19-07 PT) from system clock.
shift:
	@if pgrep -f "uv run python run_autoresearch_loop" > /dev/null; then \
		echo "A shift is already running (pgrep matched run_autoresearch_loop). Refusing to spawn a duplicate."; \
		exit 1; \
	fi
	@ts=$$(date +%Y-%m-%d_%H-%M-%S); \
	out="shift_stdout_$$ts.log"; \
	nohup uv run python run_autoresearch_loop.py > "$$out" 2>&1 & \
	echo "Spawned PID $$! — stdout: $$out"

check-deps:
	@uv run python -c "import torch; print('torch:', torch.__version__, 'cuda:', torch.cuda.is_available())"
	@uv run python -c "import train, vesuvius_loader, model_wrappers, run_autoresearch_loop; print('main modules import OK')"
	@nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "(no GPU detected; CPU-only mode)"

clean:
	rm -f shift_stdout_*.log dayshift_stdout.log nightshift_stdout.log run.log /tmp/reeval.log /tmp/fiber_gen.log

clean-cache: clean
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -maxdepth 2 -name "valid_coords_*.npy" -delete 2>/dev/null || true
