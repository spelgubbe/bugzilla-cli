$ErrorActionPreference = "Stop"

python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete. Copy .env.example to .env and fill in your credentials:"
Write-Host "  copy .env.example .env"
