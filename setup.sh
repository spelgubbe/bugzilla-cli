#!/usr/bin/env bash
set -e

python3 -m venv .venv
. .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup complete. Activate the environment with:"
echo "  source .venv/bin/activate"
echo ""
echo "Then copy .env.example to .env and fill in your credentials."
