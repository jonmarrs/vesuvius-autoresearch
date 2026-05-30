#!/bin/bash
# stop.sh - Safely stop the autoresearch loop and allow it to clean up child processes

echo "Looking for run_autoresearch_loop.py processes..."

# Find the PID(s) of run_autoresearch_loop.py
PIDS=$(pgrep -f "python run_autoresearch_loop.py")

if [ -z "$PIDS" ]; then
    echo "No autoresearch loop processes found."
    exit 0
fi

for PID in $PIDS; do
    echo "Sending SIGTERM to PID $PID to trigger graceful shutdown..."
    kill -15 "$PID"

    # Wait for the process to exit
    echo "Waiting for process $PID to clean up child process groups and exit..."
    while kill -0 "$PID" 2>/dev/null; do
        sleep 1
    done
    echo "Process $PID has been successfully terminated."
done

echo "Autoresearch loop stopped safely."
