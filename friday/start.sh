#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -f .venv/ready ]; then
  echo "First run: setting up Friday..."
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
  touch .venv/ready
fi
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Put your API key in the .env file (open it in any text editor), then run ./start.sh again."
  exit 0
fi
( sleep 2; (command -v open >/dev/null && open http://localhost:8000) || (command -v xdg-open >/dev/null && xdg-open http://localhost:8000) || true ) &
exec .venv/bin/python server.py
