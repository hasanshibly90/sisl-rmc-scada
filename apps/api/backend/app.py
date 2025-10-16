import os, json, datetime, asyncio
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# ---------- App ----------
app = Flask(__name__, template_folder="templates")
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rmc.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tolerance_pct = db.Column(db.Float, default=2.5)
    mixer_capacity_m3 = db.Column(db.Float, default=1.0)
    default_recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    capacity_m3 = db.Column(db.Float, default=15.0)
    plate = db.Column(db.String(64))
    driver_name = db.Column(db.String(64))

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    cell = db.Column(db.String(32))
    email = db.Column(db.String(128))
    office_addr = db.Column(db.Text)
    delivery_addr = db.Column(db.Text)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    items = db.relationship("RecipeItem", backref="recipe", cascade="all, delete-orphan")

class RecipeItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    material = db.Column(db.String(16), nullable=False)  # cement/sand/agg1/agg2/water/admix
    per_m3_qty = db.Column(db.Float, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    total_m3 = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(16), default="running")  # running/paused/stopped/done
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    client = db.relationship("Client")
    recipe = db.relationship("Recipe")
    rows = db.relationship("OrderRow", order_by="OrderRow.seq_no", backref="order", cascade="all, delete-orphan")

class OrderRow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    seq_no = db.Column(db.Integer, nullable=False)
    planned_m3 = db.Column(db.Float, nullable=False, default=1.000)
    state = db.Column(db.String(16), default="pending")  # pending/running/done
    actual_json = db.Column(db.Text)  # JSON {cement,sand,agg1,agg2,water,admix}
    started_at = db.Column(db.DateTime)
    done_at = db.Column(db.DateTime)
    car_run_id = db.Column(db.Integer, db.ForeignKey("car_run.id"), nullable=True)

class CarRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)
    load_seq = db.Column(db.Integer, nullable=False)  # 1..n within order
    volume_m3 = db.Column(db.Float, default=15.0)
    note = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    row_start_seq = db.Column(db.Integer)
    row_end_seq = db.Column(db.Integer)
    order = db.relationship("Order", backref="car_runs")
    vehicle = db.relationship("Vehicle")

# ---------- Helpers ----------
def now(): return datetime.datetime.utcnow()
def round3(x: float) -> float: return float(f"{x:.3f}")

def recipe_to_dict(recipe):
    out = {"cement":0,"sand":0,"agg1":0,"agg2":0,"water":0,"admix":0}
    for it in recipe.items: out[it.material] = it.per_m3_qty
    return out

# ---------- Auto-migration (SQLite) ----------
from sqlalchemy import text
def migrate_client_table():
    with app.app_context():
        try:
            rows = db.session.execute(text("PRAGMA table_info(client)")).fetchall()
        except Exception:
            return
        existing = {row[1] for row in rows}
        stmts = []
        if "cell" not in existing: stmts.append("ALTER TABLE client ADD COLUMN cell TEXT")
        if "email" not in existing: stmts.append("ALTER TABLE client ADD COLUMN email TEXT")
        if "office_addr" not in existing: stmts.append("ALTER TABLE client ADD COLUMN office_addr TEXT")
        if "delivery_addr" not in existing: stmts.append("ALTER TABLE client ADD COLUMN delivery_addr TEXT")
        for s in stmts: db.session.execute(text(s))
        if stmts: db.session.commit()

# ---------- Seed ----------
def ensure_seed():
    with app.app_context():
        db.create_all()
        migrate_client_table()

        if Vehicle.query.count() == 0:
            db.session.add_all([
                Vehicle(name="Truck-01", capacity_m3=15.0),
                Vehicle(name="Truck-02", capacity_m3=15.0),
                Vehicle(name="Truck-03", capacity_m3=15.0),
            ])

        if Client.query.count() == 0:
            db.session.add(Client(name="ABC Builders", cell="+8801XXXXXXXXX",
                                  email="info@abc.example",
                                  office_addr="DOHS Mirpur, Dhaka-1216",
                                  delivery_addr="Tejgaon, Dhaka"))

        if Recipe.query.count() == 0:
            r = Recipe(name="M25 DEFAULT"); db.session.add(r)
            db.session.add_all([
                RecipeItem(recipe=r, material="cement", per_m3_qty=350.0),
                RecipeItem(recipe=r, material="sand",   per_m3_qty=650.0),
                RecipeItem(recipe=r, material="agg1",   per_m3_qty=600.0),
                RecipeItem(recipe=r, material="agg2",   per_m3_qty=400.0),
                RecipeItem(recipe=r, material="water",  per_m3_qty=180.0),
                RecipeItem(recipe=r, material="admix",  per_m3_qty=2.500),
            ])

        if Setting.query.count() == 0:
            db.session.add(Setting(tolerance_pct=2.5, mixer_capacity_m3=1.0))

        db.session.commit()

        s = Setting.query.first()
        if s.default_recipe_id is None:
            s.default_recipe_id = Recipe.query.filter_by(name="M25 DEFAULT").first().id
            db.session.commit()

# ---------- Health ----------
@app.get("/health")
def health(): return {"ok": True, "time": now().isoformat()}

# ---------- Clients / Vehicles / Recipes / Settings (CRUD) ----------
@app.get("/api/clients")
def list_clients():
    cs = Client.query.order_by(Client.id).all()
    return jsonify([{ "id":c.id,"name":c.name,"cell":c.cell,"email":c.email,
                      "office_addr":c.office_addr,"delivery_addr":c.delivery_addr } for c in cs])

@app.post("/api/clients")
def create_client():
    d = request.json or {}
    nm = (d.get("name") or "").strip()
    if not nm: return jsonify({"error":"Name required"}), 400
    c = Client(name=nm, cell=(d.get("cell") or None), email=(d.get("email") or None),
               office_addr=(d.get("office_addr") or None), delivery_addr=(d.get("delivery_addr") or None))
    db.session.add(c); db.session.commit(); return jsonify({"id": c.id}), 201

@app.put("/api/clients/<int:cid>")
def update_client(cid):
    d = request.json or {}
    c = Client.query.get_or_404(cid)
    if "name" in d:
        nm = (d.get("name") or "").strip()
        if not nm: return jsonify({"error":"Name required"}), 400
        c.name = nm
    for k in ["cell","email","office_addr","delivery_addr"]:
        if k in d: setattr(c, k, (d.get(k) or None))
    db.session.commit(); return jsonify({"ok": True})

@app.delete("/api/clients/<int:cid>")
def delete_client(cid):
    if Order.query.filter_by(client_id=cid).first():
        return jsonify({"error":"Client has related orders and cannot be deleted."}), 400
    c = Client.query.get_or_404(cid); db.session.delete(c); db.session.commit(); return jsonify({"ok": True})

@app.get("/api/vehicles")
def list_vehicles():
    v = Vehicle.query.order_by(Vehicle.id).all()
    return jsonify([{"id":x.id,"name":x.name,"capacity_m3":x.capacity_m3,"plate":x.plate,"driver_name":x.driver_name} for x in v])

@app.post("/api/vehicles")
def create_vehicle():
    d = request.json or {}
    nm = (d.get("name") or "").strip()
    if not nm: return jsonify({"error":"Name required"}), 400
    v = Vehicle(name=nm, capacity_m3=float(d.get("capacity_m3",15.0)), plate=d.get("plate"), driver_name=d.get("driver_name"))
    db.session.add(v); db.session.commit(); return jsonify({"id": v.id}), 201

@app.put("/api/vehicles/<int:vid>")
def update_vehicle(vid):
    d = request.json or {}
    v = Vehicle.query.get_or_404(vid)
    if "name" in d:
        nm = (d.get("name") or "").strip()
        if not nm: return jsonify({"error":"Name required"}), 400
        v.name = nm
    if "capacity_m3" in d: v.capacity_m3 = float(d["capacity_m3"])
    if "plate" in d: v.plate = d["plate"]
    if "driver_name" in d: v.driver_name = d["driver_name"]
    db.session.commit(); return jsonify({"ok": True})

@app.delete("/api/vehicles/<int:vid>")
def delete_vehicle(vid):
    if CarRun.query.filter_by(vehicle_id=vid).first():
        return jsonify({"error":"Vehicle has related delivery runs and cannot be deleted."}), 400
    v = Vehicle.query.get_or_404(vid); db.session.delete(v); db.session.commit(); return jsonify({"ok": True})

@app.get("/api/recipes")
def list_recipes():
    rs = Recipe.query.order_by(Recipe.id).all()
    return jsonify([{"id":r.id,"name":r.name,"setpoints":recipe_to_dict(r)} for r in rs])

@app.post("/api/recipes")
def create_recipe():
    d = request.json or {}
    nm = (d.get("name") or "").strip()
    if not nm: return jsonify({"error":"Name required"}), 400
    sp = d.get("setpoints") or {}
    r = Recipe(name=nm); db.session.add(r); db.session.flush()
    for k in ["cement","sand","agg1","agg2","water","admix"]:
        db.session.add(RecipeItem(recipe_id=r.id, material=k, per_m3_qty=float(sp.get(k,0))))
    db.session.commit(); return jsonify({"id": r.id}), 201

@app.put("/api/recipes/<int:rid>")
def update_recipe(rid):
    d = request.json or {}
    r = Recipe.query.get_or_404(rid)
    if "name" in d:
        nm = (d.get("name") or "").strip()
        if not nm: return jsonify({"error":"Name required"}), 400
        r.name = nm
    if "setpoints" in d and isinstance(d["setpoints"], dict):
        for it in list(r.items): db.session.delete(it)
        sp = d["setpoints"]
        for k in ["cement","sand","agg1","agg2","water","admix"]:
            db.session.add(RecipeItem(recipe_id=r.id, material=k, per_m3_qty=float(sp.get(k,0))))
    db.session.commit(); return jsonify({"ok": True})

@app.delete("/api/recipes/<int:rid>")
def delete_recipe(rid):
    if Order.query.filter_by(recipe_id=rid).first():
        return jsonify({"error":"Recipe is used by orders and cannot be deleted."}), 400
    r = Recipe.query.get_or_404(rid); db.session.delete(r); db.session.commit(); return jsonify({"ok": True})

@app.get("/api/settings")
def get_settings():
    s = Setting.query.first()
    rec = Recipe.query.get(s.default_recipe_id) if s and s.default_recipe_id else None
    return jsonify({
        "tolerance_pct": s.tolerance_pct if s else 2.5,
        "mixer_capacity_m3": s.mixer_capacity_m3 if s else 1.0,
        "default_recipe_id": s.default_recipe_id if s else None,
        "default_recipe": {"id": rec.id, "name": rec.name, "setpoints": recipe_to_dict(rec)} if rec else None
    })

@app.put("/api/settings")
def update_settings():
    d = request.json or {}
    with app.app_context():
        s = Setting.query.first() or Setting()
        db.session.add(s)
        if "tolerance_pct" in d: s.tolerance_pct = float(d["tolerance_pct"])
        if "mixer_capacity_m3" in d: s.mixer_capacity_m3 = float(d["mixer_capacity_m3"])
        if "default_recipe_id" in d:
            rid = int(d["default_recipe_id"]) if d["default_recipe_id"] else None
            if rid is not None: _ = Recipe.query.get_or_404(rid)
            s.default_recipe_id = rid
        db.session.commit()
        rec = Recipe.query.get(s.default_recipe_id) if s.default_recipe_id else None
        return jsonify({
            "tolerance_pct": s.tolerance_pct,
            "mixer_capacity_m3": s.mixer_capacity_m3,
            "default_recipe_id": s.default_recipe_id,
            "default_recipe": {"id": rec.id, "name": rec.name, "setpoints": recipe_to_dict(rec)} if rec else None
        })

# ---------- Orders / Production ----------
def plan_rows(order):
    remaining = order.total_m3; seq = 1
    while remaining > 0:
        take = min(1.0, remaining); take = round3(take)
        db.session.add(OrderRow(order=order, seq_no=seq, planned_m3=take, state="pending"))
        seq += 1; remaining = round3(remaining - take)

@app.post("/api/orders")
def create_order():
    d = request.json or {}
    o = Order(client_id=int(d["clientId"]), recipe_id=int(d["recipeId"]), total_m3=float(d["totalM3"]), status="running")
    db.session.add(o); db.session.flush(); plan_rows(o); db.session.commit()
    return jsonify({"id": o.id}), 201

@app.get("/api/orders/<int:oid>")
def get_order(oid):
    o = Order.query.get_or_404(oid)
    return jsonify({
        "id": o.id,
        "client": {"id":o.client.id,"name":o.client.name},
        "recipe": {"id":o.recipe.id,"name":o.recipe.name,"setpoints":recipe_to_dict(o.recipe)},
        "total_m3": o.total_m3, "status": o.status,
        "rows": [{
            "id":r.id,"seq_no":r.seq_no,"planned_m3":r.planned_m3,"state":r.state,
            "actual": json.loads(r.actual_json) if r.actual_json else None,
            "car_run_id": r.car_run_id
        } for r in o.rows],
        "created_at": o.created_at.isoformat()
    })

@app.get("/api/orders")
def list_orders():
    limit = request.args.get("limit", default=50, type=int)
    q = db.session.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
    return jsonify([{
        "id": o.id,
        "client": {"id":o.client.id,"name":o.client.name},
        "recipe": {"id":o.recipe.id,"name":o.recipe.name},
        "total_m3": o.total_m3,
        "status": o.status,
        "created_at": o.created_at.isoformat()
    } for o in q])

# ---- Pause/Resume/Stop + Summary ----
def _rollback_running_rows(order_id: int):
    running_rows = OrderRow.query.filter_by(order_id=order_id, state="running").all()
    for r in running_rows:
        r.state = "pending"; r.started_at = None
    db.session.commit()

def _summary_for_order(o: Order):
    setp = recipe_to_dict(o.recipe)
    mats = ["cement","sand","agg1","agg2","water","admix"]
    set_tot = {m:0.0 for m in mats}
    act_tot = {m:0.0 for m in mats}
    delta   = {m:0.0 for m in mats}
    produced_m3 = 0.0
    for r in o.rows:
        if r.state != "done": continue
        produced_m3 += float(r.planned_m3)
        for m in mats:
            set_tot[m] += float(setp[m]) * float(r.planned_m3)
        if r.actual_json:
            act = json.loads(r.actual_json)
            for m in mats:
                act_tot[m] += float(act.get(m,0.0))
    for m in mats:
        set_tot[m]=round3(set_tot[m]); act_tot[m]=round3(act_tot[m]); delta[m]=round3(act_tot[m]-set_tot[m])
    produced_m3 = round3(produced_m3)
    remaining_m3 = round3(float(o.total_m3)-produced_m3)
    return {"orderId":o.id,"status":o.status,"produced_m3":produced_m3,
            "remaining_m3":remaining_m3,"set_totals":set_tot,"act_totals":act_tot,"delta_totals":delta}

@app.post("/api/orders/<int:oid>/pause")
def pause_order(oid):
    o = Order.query.get_or_404(oid)
    if o.status in ("done","stopped"): return jsonify({"message":f"Order already {o.status}"}), 200
    _rollback_running_rows(oid)
    o.status = "paused"; db.session.commit()
    return jsonify({"ok":True,"status":o.status})

@app.post("/api/orders/<int:oid>/resume")
def resume_order(oid):
    o = Order.query.get_or_404(oid)
    if o.status == "done": return jsonify({"message":"Order already done"}), 200
    o.status = "running"; db.session.commit()
    return jsonify({"ok":True,"status":o.status})

@app.post("/api/orders/<int:oid>/stop")
def stop_order(oid):
    o = Order.query.get_or_404(oid)
    if o.status == "done": return jsonify({"message":"Order already done"}), 200
    _rollback_running_rows(oid)
    o.status = "stopped"; db.session.commit()
    return jsonify({"ok":True,"status":o.status})

@app.get("/api/orders/<int:oid>/summary")
def order_summary(oid):
    o = Order.query.get_or_404(oid)
    return jsonify(_summary_for_order(o))

# ---- Start/Done ----
@app.post("/api/orders/<int:oid>/start-next")
def start_next(oid):
    # don’t start when paused/stopped/done
    o = Order.query.get_or_404(oid)
    if o.status in ("paused","stopped","done"):
        return jsonify({"message":f"Order is {o.status}"}), 400
    r = OrderRow.query.filter_by(order_id=oid, state="pending").order_by(OrderRow.seq_no).first()
    if not r: return jsonify({"message":"no pending row"}), 400
    r.state="running"; r.started_at=now(); db.session.commit()
    return jsonify({"rowId": r.id, "seq_no": r.seq_no})

def simulate_actual(setpoints: dict, tol_pct: float):
    import random
    out={}
    for k,v in setpoints.items():
        v = v or 0.0
        jitter = random.uniform(-tol_pct, tol_pct)/100.0
        out[k] = float(f"{v*(1.0+jitter):.3f}")
    return out

@app.post("/api/orders/<int:oid>/rows/<int:rid>/mark-done")
def mark_done(oid, rid):
    r = OrderRow.query.filter_by(order_id=oid, id=rid).first_or_404()
    if r.state == "done": return jsonify({"message":"already done"}), 200
    s = Setting.query.first(); recipe = Order.query.get(oid).recipe
    actual = simulate_actual(recipe_to_dict(recipe), s.tolerance_pct if s else 2.5)
    scale = r.planned_m3 / 1.0
    for k in actual: actual[k] = float(f"{actual[k]*scale:.3f}")
    r.actual_json = json.dumps(actual); r.done_at=now(); r.state="done"
    remain = OrderRow.query.filter_by(order_id=oid).filter(OrderRow.state!="done").count()
    if remain == 0: Order.query.get(oid).status="done"
    db.session.commit()
    return jsonify({"ok": True, "actual": actual})

# ---------- Runs ----------
@app.get("/api/runs/by-order/<int:oid>")
def runs_by_order(oid):
    runs = CarRun.query.filter_by(order_id=oid).order_by(CarRun.load_seq).all()
    return jsonify([{
        "id":x.id,"load_seq":x.load_seq,
        "vehicle":{"id":x.vehicle.id,"name":x.vehicle.name} if x.vehicle else None,
        "row_start_seq":x.row_start_seq,"row_end_seq":x.row_end_seq,
        "volume_m3":x.volume_m3,"note":x.note
    } for x in runs])

# precise batch assignment (optional seq range)
@app.post("/api/vehicles/<int:vid>/runs")
def create_run(vid):
    d = request.json or {}
    oid = int(d["orderId"]); note = d.get("note","")
    row_start_seq = d.get("row_start_seq"); row_end_seq = d.get("row_end_seq")
    Vehicle.query.get_or_404(vid); Order.query.get_or_404(oid)
    last = CarRun.query.filter_by(order_id=oid).order_by(CarRun.load_seq.desc()).first()
    load_seq = (last.load_seq + 1) if last else 1
    if row_start_seq is not None and row_end_seq is not None:
        rows = (OrderRow.query.filter_by(order_id=oid)
                .filter(OrderRow.seq_no>=int(row_start_seq), OrderRow.seq_no<=int(row_end_seq))
                .order_by(OrderRow.seq_no).all())
        if not rows: return jsonify({"error":"range not found"}), 400
        unassigned = [r for r in rows if r.car_run_id is None]
        if not unassigned: return jsonify({"error":"range already assigned"}), 400
        run = CarRun(order_id=oid, vehicle_id=vid, load_seq=load_seq,
                     volume_m3=sum(r.planned_m3 for r in unassigned), note=note,
                     row_start_seq=int(row_start_seq), row_end_seq=int(row_end_seq))
        db.session.add(run); db.session.flush()
        for r in unassigned: r.car_run_id = run.id
        db.session.commit()
        return jsonify({"id": run.id, "load_seq": load_seq,
                        "row_start_seq": run.row_start_seq, "row_end_seq": run.row_end_seq})
    # legacy: next 15 unassigned
    unassigned = (OrderRow.query.filter_by(order_id=oid)
                  .filter(OrderRow.car_run_id.is_(None))
                  .order_by(OrderRow.seq_no).all())
    if not unassigned: return jsonify({"error":"no unassigned rows"}), 400
    block = unassigned[:15]
    run = CarRun(order_id=oid, vehicle_id=vid, load_seq=load_seq,
                 volume_m3=sum(r.planned_m3 for r in block), note=note,
                 row_start_seq=block[0].seq_no, row_end_seq=block[-1].seq_no)
    db.session.add(run); db.session.flush()
    for r in block: r.car_run_id = run.id
    db.session.commit()
    return jsonify({"id": run.id, "load_seq": load_seq,
                    "row_start_seq": run.row_start_seq, "row_end_seq": run.row_end_seq})

# ---------- Reports (JSON/HTML & Playwright PDF) ----------
def row_view(o: Order, only_vehicle_id=None):
    setp = recipe_to_dict(o.recipe)
    s = Setting.query.first(); tol = s.tolerance_pct if s else 2.5
    rows = o.rows
    if only_vehicle_id:
        run_ids = [r.id for r in o.car_runs if r.vehicle_id == only_vehicle_id]
        rows = [r for r in rows if r.car_run_id in run_ids]
    view=[]; totals = {"planned_m3":0, "set":{k:0 for k in setp}, "act":{k:0 for k in setp}, "delta":{k:0 for k in setp}}
    for r in rows:
        actual = json.loads(r.actual_json) if r.actual_json else {k:None for k in setp}
        delta={}
        for k in setp:
            sv = round3(setp[k] * r.planned_m3)
            av = actual[k] if actual[k] is not None else None
            dv = (round3(av - sv) if av is not None else None)
            delta[k]=dv; totals["set"][k]+=sv
            if av is not None:
                totals["act"][k]+=av; totals["delta"][k]+=dv
        totals["planned_m3"] = round3(totals["planned_m3"] + r.planned_m3)
        view.append({"seq":r.seq_no,"m3":r.planned_m3,
                     "set":{k:round3(setp[k]*r.planned_m3) for k in setp},
                     "act":actual,"delta":delta,"state":r.state})
    for k in setp:
        totals["set"][k]=round3(totals["set"][k]); totals["act"][k]=round3(totals["act"][k]); totals["delta"][k]=round3(totals["delta"][k])
    return view, totals, tol

@app.get("/api/reports3/<int:oid>/loads")
def loads_json(oid):
    vehicle_id = request.args.get("vehicleId", type=int)
    o = Order.query.get_or_404(oid)
    rows, totals, tol = row_view(o, vehicle_id)
    veh = Vehicle.query.get(vehicle_id) if vehicle_id else None
    return jsonify({
        "orderId": o.id, "client": o.client.name, "recipe": o.recipe.name,
        "vehicle": ({"id":veh.id,"name":veh.name} if veh else None),
        "rows": rows, "totals": totals, "tolerance_pct": tol
    })

@app.get("/api/reports3/<int:oid>/loads.html")
def loads_html(oid):
    vehicle_id = request.args.get("vehicleId", type=int)
    o = Order.query.get_or_404(oid)
    rows, totals, tol = row_view(o, vehicle_id)
    veh = Vehicle.query.get(vehicle_id) if vehicle_id else None
    return render_template("loads.html",
        order=o, client=o.client.name, recipe=o.recipe.name,
        vehicle=veh, rows=rows, totals=totals, tolerance_pct=tol
    )

async def render_pdf_with_playwright(url: str, out_path: Path):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.emulate_media(media="screen")
        await page.pdf(path=str(out_path), format="A4", landscape=True,
                       margin={"top":"10mm","bottom":"10mm","left":"8mm","right":"8mm"},
                       print_background=True)
        await browser.close()

@app.get("/api/reports3/<int:oid>/loads.pdf")
def loads_pdf(oid):
    vehicle_id = request.args.get("vehicleId", type=int)
    base_url = f"http://127.0.0.1:8000/api/reports3/{oid}/loads.html"
    if vehicle_id: base_url += f"?vehicleId={vehicle_id}"
    out_path = Path(f"loads_{oid}_{vehicle_id or 'ALL'}.pdf").absolute()
    try:
        asyncio.run(render_pdf_with_playwright(base_url, out_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not out_path.exists(): abort(500, "PDF not generated")
    return send_file(str(out_path), as_attachment=True, download_name=out_path.name)

if __name__ == "__main__":
    ensure_seed()
    app.run(host="127.0.0.1", port=8000, debug=True)
