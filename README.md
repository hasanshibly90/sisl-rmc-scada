# SISL RMC SCADA (Monorepo)

**apps/api** — Flask + SQLite (clients, vehicles, recipes, orders, runs, reports).  
**apps/desktop** — PySide6 plant visualization (silos, hoppers, mixer, flows).

## Run API
cd apps/api
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python -m playwright install
python app.py

## Run Desktop
cd apps/desktop
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python main.py
