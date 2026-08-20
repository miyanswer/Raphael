#!/bin/bash
# ==============================================================================
# Raphael Enterprise All-in-One Multi-Agent Pipeline Launcher Script
# Launches AI CTO, AI Coder, AI QA, and AI PM Web UI concurrently.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source /opt/ros/humble/setup.bash
if [ -f "$SCRIPT_DIR/install/setup.bash" ]; then
    source "$SCRIPT_DIR/install/setup.bash"
fi

echo "============================================================"
echo " 🚀 Starting Raphael Enterprise Multi-Agent Platform"
echo "  - AI CTO (Architect Node)     [Background]"
echo "  - AI Coder (Developer Node)  [Background]"
echo "  - AI QA (Inspector/Tester Node) [Background]"
echo "  - AI PM (Interpreter Web UI) [Foreground - Port 5001]"
echo "============================================================"

CTO_PID=""
CODER_PID=""
QA_PID=""

# Cleanup handler for Ctrl+C
cleanup() {
    echo ""
    echo "[INFO] Shutting down Raphael agents..."
    if [ -n "$CTO_PID" ]; then
        kill -TERM "$CTO_PID" 2>/dev/null
    fi
    if [ -n "$CODER_PID" ]; then
        kill -TERM "$CODER_PID" 2>/dev/null
    fi
    if [ -n "$QA_PID" ]; then
        kill -TERM "$QA_PID" 2>/dev/null
    fi
    echo "[INFO] All agents stopped cleanly."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start AI CTO Node in background
ros2 run new_raphael_enterprise architect_cto &
CTO_PID=$!
echo "[INFO] AI CTO Node started (PID: $CTO_PID)"

# 2. Start AI Coder Node in background
ros2 run new_raphael_enterprise coder_agent &
CODER_PID=$!
echo "[INFO] AI Coder Node started (PID: $CODER_PID)"

# 3. Start AI QA Node in background
ros2 run new_raphael_enterprise qa_agent &
QA_PID=$!
echo "[INFO] AI QA Node started (PID: $QA_PID)"

sleep 2

# 4. Start AI PM Web UI in foreground
echo "[INFO] Launching AI PM Web UI..."
ros2 run new_raphael_enterprise interpreter_pm
