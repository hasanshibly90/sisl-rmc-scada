$ErrorActionPreference = "Continue"
cd apps\api
if (-not (Test-Path .venv)) { python -m venv .venv }
. .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
python -m playwright install
$env:FLASK_ENV="development"
python app.py 2>&1 | Tee-Object -FilePath "..\..\logs_api.txt"
