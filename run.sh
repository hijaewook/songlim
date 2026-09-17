#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python3}
if [ ! -d ".venv" ]; then
  "$PYTHON" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo
echo "Game server: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop."
echo
python -m uvicorn app:app --host 127.0.0.1 --port 8000
