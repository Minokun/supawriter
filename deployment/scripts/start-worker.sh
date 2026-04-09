#!/bin/bash
# Start arq Worker for article generation

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Create logs directory if not exists
mkdir -p logs

echo "Starting Article Generator Worker..."
echo "Redis: ${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}"
echo "Max concurrent jobs: 3"
echo "Timeout: 600s"
echo "Log file: logs/worker.log"

# Activate virtual environment if exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Add backend to Python path
export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"

# Set encryption key (same as used in migration)
export ENCRYPTION_KEY="Txnojiw-jPRUlgScsp7-3CVWwOH5sNSLBuTor4pEjL0="

# Start worker with log redirection
# Run in background and save PID
nohup .venv/bin/python -m arq backend.api.workers.worker_settings.WorkerSettings \
    >> logs/worker.log 2>&1 &

WORKER_PID=$!
echo $WORKER_PID > .pids/backend-worker.pid

echo "Worker started with PID: $WORKER_PID"
echo "Log file: logs/worker.log"
echo "Press Ctrl+C to exit (worker will continue in background)"

# Wait a moment to check if worker started successfully
sleep 2

if ps -p $WORKER_PID > /dev/null; then
    echo "✅ Worker is running"
    echo "Recent logs:"
    tail -10 logs/worker.log
else
    echo "❌ Worker failed to start. Check logs/worker.log for details."
    rm -f .pids/backend-worker.pid
    exit 1
fi
