cd apps\desktop
if (-not (Test-Path .venv)) { python -m venv .venv }
. .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
python -X dev -W default main.py 2>&1 | Tee-Object -FilePath "..\logs_desktop.txt"
