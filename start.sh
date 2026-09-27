#!/bin/bash

# Vera — MagicPin AI Merchant Assistant
# Startup script

set -e

echo "=========================================="
echo "  Vera AI Merchant Assistant — Starting"
echo "=========================================="
echo

# Check Python version
python_version=$(python3 --version | awk '{print $2}')
echo "[✓] Python $python_version"

# Check/create venv
if [ ! -d "venv" ]; then
    echo "[→] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate || . venv/Scripts/activate
echo "[✓] Virtual environment activated"

# Install requirements
echo "[→] Installing requirements..."
pip install -q -r requirements.txt
echo "[✓] Requirements installed"

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "[✓] Environment loaded from .env"
else
    echo "[!] Warning: .env not found. Using defaults."
    echo "[→] Create .env from .env.example: cp .env.example .env"
fi

# Show config
echo
echo "=========================================="
echo "  Configuration"
echo "=========================================="
echo "Team:       ${TEAM_NAME:-Vera Team}"
echo "Contact:    ${CONTACT_EMAIL:-vera@magicpin.ai}"
echo "Version:    ${BOT_VERSION:-1.0.0}"
echo "Port:       ${PORT:-8080}"
echo "Host:       ${HOST:-0.0.0.0}"
echo "=========================================="
echo

# Start server
PORT=${PORT:-8080}
HOST=${HOST:-0.0.0.0}

echo "[→] Starting FastAPI server..."
echo "[→] Server will be available at http://$HOST:$PORT"
echo "[→] Health check: http://$HOST:$PORT/v1/healthz"
echo "[→] Metadata: http://$HOST:$PORT/v1/metadata"
echo
echo "Press Ctrl+C to stop the server"
echo

uvicorn app:app --host $HOST --port $PORT --reload
