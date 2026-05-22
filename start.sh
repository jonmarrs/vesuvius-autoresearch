#!/bin/bash
# start.sh - Kick off the autoresearch loop in the background

if pgrep -f "python run_autoresearch_loop.py" > /dev/null; then
    echo "Warning: run_autoresearch_loop.py appears to be running already."
    echo "Check background processes before starting a new instance."
    exit 1
fi

echo "Starting run_autoresearch_loop.py in the background..."
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv/lib/python3.10/site-packages/nvidia/cusolver/lib
nohup uv run python run_autoresearch_loop.py > autoresearch.out 2>&1 &
PID=$!

echo "Process started with PID $PID"
echo "Main logs are managed internally by the script."
echo "You can check autoresearch.out for script-level stdout/stderr."
