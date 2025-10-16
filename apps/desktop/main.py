# main.py — FINAL (Cement + Water + Admixture; Pump→Hopper pipes; dynamic steel pipe; PLC-ready stubs)
import os, json, csv
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QFrame,
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QRadioButton, QButtonGroup,
    QProgressBar, QSizePolicy
)

# ---------- SAFE MODE SWITCH ----------
USE_SPRITES = False  # keep False (no PNG/SVG); you can enable later

# ---------- THEME FALLBACK ----------
# If you have theme.py with GREY_TEXT (QColor), this will use it; otherwise it falls back to hex.
try:
    from theme import GREY_TEXT
    GREY_TEXT_CSS = GREY_TEXT.name()
except Exception:
    GREY_TEXT_CSS = "#9AA4AF"

# ---------- PLC (FX5U) STUBS ----------
def plc_read_real(addr: str) -> float:
    """TODO: replace with MC-Protocol read."""
    return 0.0

def plc_write_real(addr: str, value: float):
    """TODO: replace with MC-Protocol write."""
    pass

from contracts import SiloLike, MixerLike
from components.plant_view import PlantView
from components.silo import Silo
from components.mixer import Mixer
from components.agg_hopper import AggHopper
from components.collector_hopper import CollectingHopper
from components.belt_conveyor import BeltConveyor
from components.cement_hopper import CementHopper
from components.flow_connector import FlowConnectorItem
from components.motor_badge import MotorBadge

# Explicit classes for water/admixture visuals (code-only, no images)
from components.water_hopper import WaterHopper
from components.admixture_hopper import AdmixtureHopper
from components.water_pump import WaterPump
from components.admixture_pump import AdmixturePump

# (Sprites optional — not used when USE_SPRITES=False)
if USE_SPRITES:
    try:
        from components.image_items import ScrewMotor, PipeStrip, PixmapItem
        from components.sprite_pipe import SpritePipe
    except Exception:
        USE_SPRITES = False

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
BATCH_LOG = os.path.join(APP_DIR, "batches.csv")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_csv_header(path):
    header = [
        "BatchTime","Recipe",
        "Agg1_Target","Agg1_Actual","Agg1_VarPct",
        "Agg2_Target","Agg2_Actual","Agg2_VarPct",
        "Agg3_Target","Agg3_Actual","Agg3_VarPct",
        "Agg4_Target","Agg4_Actual","Agg4_VarPct",
        "Total_Target","Total_Actual","Total_VarPct"
    ]
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)

class MainWindow(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("RMC Plant — Cement/Water/Admixture (Pump→Hopper)")
        self.setStyleSheet("QMainWindow { background: #1E2024; color: #EAECEE; }")

        # targets
        tcfg = cfg.get("targets", {})
        self.t_agg = [
            float(tcfg.get("Agg1", 600)),
            float(tcfg.get("Agg2", 500)),
            float(tcfg.get("Agg3", 400)),
            float(tcfg.get("Agg4", 300)),
        ]
        self.t_total = float(tcfg.get("Total", sum(self.t_agg)))
        self.recipe = cfg.get("recipe", "Default")

        # central + scene/view
        central = QFrame(); central.setStyleSheet("QFrame { background:#1E2024; }")
        self.setCentralWidget(central)
        self.scene = QGraphicsScene(self); self.scene.setSceneRect(-3600, -1800, 7200, 3600)
        self.view  = PlantView(self.scene)
        flags = cfg.get("flags", {"draggable": True})

        # Mixer
        self.mixer: MixerLike = Mixer(draggable=flags["draggable"])
        self.mixer.setPos(*cfg["layout"]["mixer_pos"]); self.scene.addItem(self.mixer)

        # Cement silos (list)
        self.silos: list[SiloLike] = []
        for s in cfg.get("silos", []):
            silo = Silo(draggable=flags["draggable"])
            silo.setPos(*s["pos"]); self.scene.addItem(silo); self.silos.append(silo)
        self.active_feeder = 1

        # Aggregate hoppers
        self.hoppers: list[AggHopper] = []
        for i, h in enumerate(cfg.get("hoppers", []), start=1):
            hp = AggHopper(draggable=flags["draggable"])
            if hasattr(hp, "set_title"): hp.set_title(h.get("name", f"Agg {i}"))
            if hasattr(hp, "set_capacity_kg"): hp.set_capacity_kg(h.get("capacity_kg", 1500))
            hp.setPos(*h["pos"]); self.scene.addItem(hp); self.hoppers.append(hp)

        # Cement Weigh Hopper
        self.cement_hopper: CementHopper | None = None
        ch = cfg.get("cement_hopper")
        if ch:
            self.cement_hopper = CementHopper(
                capacity_kg=ch.get("capacity_kg", 500.0),
                title=ch.get("name","Cement Weigh Hopper"),
                draggable=flags["draggable"],
            )
            self.cement_hopper.setPos(*ch.get("pos",[560,-40])); self.scene.addItem(self.cement_hopper)

        # Collector + Belt
        self.collector: CollectingHopper | None = None
        self.belt: BeltConveyor | None = None
        col = cfg.get("collector")
        if col:
            self.collector = CollectingHopper(w=1500, h=260, draggable=flags["draggable"])
            if hasattr(self.collector, "set_title"): self.collector.set_title(col.get("name","Collecting Hopper"))
            if hasattr(self.collector, "set_capacity_kg"): self.collector.set_capacity_kg(col.get("capacity_kg",6000))
            self.collector.setPos(*col["pos"]); self.scene.addItem(self.collector)

            labels = [getattr(hp,"_title",f"Agg {i+1}") for i,hp in enumerate(self.hoppers)]
            if hasattr(self.collector, "set_segment_labels"): self.collector.set_segment_labels(labels)

            belt_cfg = cfg.get("belt", {})
            self.belt = BeltConveyor(length_px=self.collector.w,
                                     belt_h=float(belt_cfg.get("height", 28)),
                                     draggable=flags["draggable"])
            self.belt.set_speed(float(belt_cfg.get("speed", 3.0)))
            self.belt.set_direction(str(belt_cfg.get("direction","right")).lower())
            cx, cy = self.collector.pos().x(), self.collector.pos().y()
            self.belt.setPos(cx, cy + float(belt_cfg.get("offset_y", 110)))
            self.belt.start(); self.scene.addItem(self.belt)

        # -------------------- Runtime states --------------------
        self.cement_screw_running = False
        self.water_pump_running   = False
        self.admix_pump_running   = False

        # Virtual source tanks (for pump→hopper flow; replace with FX5U later)
        self.water_tank_capacity_kg = float(self.cfg.get("water_tank_capacity_kg", 1000.0))
        self.water_tank_kg          = float(self.cfg.get("water_tank_start_kg", 800.0))
        self.admix_tank_capacity_kg = float(self.cfg.get("admixture_tank_capacity_kg", 200.0))
        self.admix_tank_kg          = float(self.cfg.get("admixture_tank_start_kg", 160.0))

        # -------------------- Water & Admixture Hoppers --------------------
        self.water_hopper = None; self.admix_hopper = None
        wh = cfg.get("water_hopper"); ah = cfg.get("admixture_hopper")
        if wh:
            self.water_hopper = WaterHopper(
                capacity_kg=wh.get("capacity_kg", 100),
                title=wh.get("name","Water Weigh Hopper"), draggable=flags["draggable"])
            self.water_hopper.setPos(*wh.get("pos", [1160, -120])); self.scene.addItem(self.water_hopper)
        if ah:
            self.admix_hopper = AdmixtureHopper(
                capacity_kg=ah.get("capacity_kg", 10),
                title=ah.get("name","Admixture Weigh Hopper"), draggable=flags["draggable"])
            self.admix_hopper.setPos(*ah.get("pos", [1160, 120])); self.scene.addItem(self.admix_hopper)

        # -------------------- Pumps (code visuals) --------------------
        self.water_pump = None; self.admix_pump = None
        wp_pos = self.cfg.get("water_pump", {}).get("pos", [900, -60])
        ap_pos = self.cfg.get("admixture_pump", {}).get("pos", [900, 200])
        self.water_pump = WaterPump(draggable=True); self.water_pump.setPos(*wp_pos); self.scene.addItem(self.water_pump)
        self.admix_pump = AdmixturePump(draggable=True); self.admix_pump.setPos(*ap_pos); self.scene.addItem(self.admix_pump)

        # -------------------- Cement: Silo[0] → Hopper (unchanged) --------------------
        self.cement_pipe: FlowConnectorItem | None = None
        self.cement_outlet_badge: MotorBadge | None = None
        if self.silos and self.cement_hopper:
            cement_silo = self.silos[0]
            silo_cap = float(self.cfg.get("cement_silo_capacity_kg", 20000.0))
            get_src_kg = lambda: max(0.0, min(100.0, cement_silo.get_percent())) * silo_cap / 100.0
            def set_src_kg(v_kg): cement_silo.set_percent(0 if silo_cap<=0 else max(0,min(100,(v_kg/silo_cap)*100)))
            get_dst_kg = self.cement_hopper.get_weight_kg
            def set_dst_kg(v_kg): self.cement_hopper.set_weight_kg(max(0,min(self.cement_hopper.get_capacity_kg(), v_kg)))
            pipe_cfg = self.cfg.get("cement_pipe", {})
            self.cement_pipe = FlowConnectorItem(
                cement_silo, cement_silo.pipe_origin_scene,
                self.cement_hopper, self.cement_hopper.inlet_scene,
                get_src_kg, set_src_kg, get_dst_kg, set_dst_kg,
                enabled_fn=lambda: self.cement_screw_running,
                rate_kgps=float(pipe_cfg.get("rate_kgps", 22.5)),
                src_capacity_kg=silo_cap,
                dst_capacity_kg=self.cement_hopper.get_capacity_kg(),
                shape=pipe_cfg.get("shape","L"),
                z=-1.0, diameter_px=int(pipe_cfg.get("diameter_px",18)), wall_px=int(pipe_cfg.get("wall_px",2))
            )
            self.scene.addItem(self.cement_pipe)
            self.cement_outlet_badge = MotorBadge(cement_silo.pipe_origin_scene, radius=10.0)
            self.cement_outlet_badge.set_running(False); self.scene.addItem(self.cement_outlet_badge)

        # -------------------- Water: Pump → Water Hopper --------------------
        self.water_pipe = None; self.water_pump_badge = None
        wp_cfg = self.cfg.get("water_pipe", {})
        if self.water_pump and self.water_hopper:
            def get_src_w(): return self.water_tank_kg
            def set_src_w(v): self.water_tank_kg = max(0.0, min(self.water_tank_capacity_kg, float(v)))
            get_dst_w = self.water_hopper.get_weight_kg
            def set_dst_w(v):
                cap = self.water_hopper.get_capacity_kg()
                self.water_hopper.set_weight_kg(max(0.0, min(cap, float(v))))
            self.water_pipe = FlowConnectorItem(
                self.water_pump, self.water_pump.outlet_scene,
                self.water_hopper, self.water_hopper.inlet_scene,
                get_src_w, set_src_w, get_dst_w, set_dst_w,
                enabled_fn=lambda: self.water_pump_running and self.water_pump.is_running(),
                rate_kgps=float(wp_cfg.get("rate_kgps", 18.0)),
                src_capacity_kg=self.water_tank_capacity_kg,
                dst_capacity_kg=self.water_hopper.get_capacity_kg(),
                shape=wp_cfg.get("shape", "L"),
                z=-1.0, diameter_px=int(wp_cfg.get("diameter_px",16)), wall_px=int(wp_cfg.get("wall_px",2))
            )
            self.scene.addItem(self.water_pipe)
            self.water_pump_badge = MotorBadge(self.water_pump.outlet_scene, radius=9.0)
            self.water_pump_badge.set_running(False); self.scene.addItem(self.water_pump_badge)

        # -------------------- Admixture: Pump → Admixture Hopper --------------------
        self.admix_pipe = None; self.admix_pump_badge = None
        ap_cfg = self.cfg.get("admixture_pipe", {})
        if self.admix_pump and self.admix_hopper:
            def get_src_a(): return self.admix_tank_kg
            def set_src_a(v): self.admix_tank_kg = max(0.0, min(self.admix_tank_capacity_kg, float(v)))
            get_dst_a = self.admix_hopper.get_weight_kg
            def set_dst_a(v):
                cap = self.admix_hopper.get_capacity_kg()
                self.admix_hopper.set_weight_kg(max(0.0, min(cap, float(v))))
            self.admix_pipe = FlowConnectorItem(
                self.admix_pump, self.admix_pump.outlet_scene,
                self.admix_hopper, self.admix_hopper.inlet_scene,
                get_src_a, set_src_a, get_dst_a, set_dst_a,
                enabled_fn=lambda: self.admix_pump_running and self.admix_pump.is_running(),
                rate_kgps=float(ap_cfg.get("rate_kgps", 3.5)),
                src_capacity_kg=self.admix_tank_capacity_kg,
                dst_capacity_kg=self.admix_hopper.get_capacity_kg(),
                shape=ap_cfg.get("shape", "L"),
                z=-1.0, diameter_px=int(ap_cfg.get("diameter_px",12)), wall_px=int(ap_cfg.get("wall_px",2))
            )
            self.scene.addItem(self.admix_pipe)
            self.admix_pump_badge = MotorBadge(self.admix_pump.outlet_scene, radius=8.0)
            self.admix_pump_badge.set_running(False); self.scene.addItem(self.admix_pump_badge)

        # ---------- UI rows ----------
        ensure_csv_header(BATCH_LOG)
        lay = QVBoxLayout(central); lay.setContentsMargins(12,12,12,12); lay.setSpacing(10)

        # Row 1 — silos + active + pumps + mixer
        row1 = QHBoxLayout(); row1.setSpacing(10)
        for i, s in enumerate(cfg.get("silos", []), start=1):
            b1 = QPushButton(f"{s['name']} Start"); b2 = QPushButton(f"{s['name']} Stop")
            for b in (b1, b2): b.setStyleSheet(self._btn_style())
            b1.clicked.connect(lambda _, n=i: self._set_silo(n, True))
            b2.clicked.connect(lambda _, n=i: self._set_silo(n, False))
            row1.addWidget(b1); row1.addWidget(b2)

        if self.silos:
            row1.addSpacing(10); row1.addWidget(QLabel("Active Feeder:"))
            self.feeder_group = QButtonGroup(self); self.feeder_group.setExclusive(True)
            for i, s in enumerate(cfg["silos"], start=1):
                r = QRadioButton(s["name"]); r.setStyleSheet("color:#EAECEE;")
                row1.addWidget(r); self.feeder_group.addButton(r, i)
            self.feeder_group.buttons()[0].setChecked(True)
            self.feeder_group.idClicked.connect(self._set_active_feeder)

        row1.addSpacing(16); row1.addWidget(QLabel("Cement Screw:"))
        self.btn_screw_start = QPushButton("START"); self.btn_screw_stop = QPushButton("STOP")
        for b in (self.btn_screw_start, self.btn_screw_stop): b.setStyleSheet(self._btn_style())
        row1.addWidget(self.btn_screw_start); row1.addWidget(self.btn_screw_stop)

        row1.addSpacing(16); row1.addWidget(QLabel("Water Pump:"))
        self.btn_water_start = QPushButton("START"); self.btn_water_stop = QPushButton("STOP")
        for b in (self.btn_water_start, self.btn_water_stop): b.setStyleSheet(self._btn_style())
        row1.addWidget(self.btn_water_start); row1.addWidget(self.btn_water_stop)

        row1.addSpacing(12); row1.addWidget(QLabel("Admixture Pump:"))
        self.btn_admix_start = QPushButton("START"); self.btn_admix_stop = QPushButton("STOP")
        for b in (self.btn_admix_start, self.btn_admix_stop): b.setStyleSheet(self._btn_style())
        row1.addWidget(self.btn_admix_start); row1.addWidget(self.btn_admix_stop)

        self.btn_mix_start = QPushButton("Mixer Start")
        self.btn_mix_stop  = QPushButton("Mixer Stop")
        self.btn_discharge = QPushButton("Discharge (Log)")
        self.btn_fs        = QPushButton("Fullscreen (F11)")
        for b in (self.btn_mix_start, self.btn_mix_stop, self.btn_discharge, self.btn_fs): b.setStyleSheet(self._btn_style())
        row1.addSpacing(10)
        row1.addWidget(self.btn_mix_start); row1.addWidget(self.btn_mix_stop)
        row1.addWidget(self.btn_discharge); row1.addWidget(self.btn_fs)
        lay.addLayout(row1)

        # hook pump buttons
        self.btn_screw_start.clicked.connect(lambda: self._set_cement_screw(True))
        self.btn_screw_stop.clicked.connect(lambda: self._set_cement_screw(False))
        self.btn_water_start.clicked.connect(lambda: self._set_water_pump(True))
        self.btn_water_stop.clicked.connect(lambda: self._set_water_pump(False))
        self.btn_admix_start.clicked.connect(lambda: self._set_admix_pump(True))
        self.btn_admix_stop.clicked.connect(lambda: self._set_admix_pump(False))

        # Row 2 — per-agg bars
        row2 = QVBoxLayout(); row2.setSpacing(6)
        self.pb_aggs=[]
        for i,hp in enumerate(self.hoppers, start=1):
            title=getattr(hp,"_title",f"Agg {i}")
            hrow=QHBoxLayout(); hrow.setSpacing(8)
            addb=QPushButton(f"{title} +50 kg"); subb=QPushButton("-50 kg"); rstb=QPushButton("Reset")
            for b in (addb,subb,rstb): b.setStyleSheet(self._btn_style_small())
            addb.clicked.connect(lambda _,idx=i-1: self._bump_hopper(idx,+50))
            subb.clicked.connect(lambda _,idx=i-1: self._bump_hopper(idx,-50))
            rstb.clicked.connect(lambda _,idx=i-1: self._set_hopper(idx,0))
            pb=QProgressBar(); pb.setRange(0,int(max(1,self.t_agg[i-1]))); pb.setValue(0)
            pb.setFormat(f"{title} %p% (0/{self.t_agg[i-1]:.0f} kg)")
            pb.setMinimumWidth(380); pb.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            hrow.addWidget(addb); hrow.addWidget(subb); hrow.addWidget(rstb); hrow.addSpacing(8); hrow.addWidget(pb,1)
            row2.addLayout(hrow); self.pb_aggs.append(pb)
        lay.addLayout(row2)

        # Row 3 — totals + collector/belt
        row3 = QHBoxLayout(); row3.setSpacing(8)
        self.pb_total=QProgressBar(); self.pb_total.setRange(0,int(max(1,self.t_total))); self.pb_total.setValue(0)
        self.pb_total.setFormat(f"TOTAL %p% (0/{self.t_total:.0f} kg)")
        self.pb_total.setMinimumWidth(480); self.pb_total.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        row3.addWidget(self.pb_total,1)

        if self.collector:
            copen=QPushButton("Collector Gate Open"); cclose=QPushButton("Gate Close")
            for b in (copen,cclose): b.setStyleSheet(self._btn_style_small())
            copen.clicked.connect(self.collector.open_gate); cclose.clicked.connect(self.collector.close_gate)
            row3.addSpacing(12); row3.addWidget(copen); row3.addWidget(cclose)

        if self.belt:
            bstart=QPushButton("Belt Start"); bstop=QPushButton("Belt Stop")
            for b in (bstart,bstop): b.setStyleSheet(self._btn_style_small())
            bstart.clicked.connect(self._belt_start); bstop.clicked.connect(self._belt_stop)
            row3.addSpacing(12); row3.addWidget(bstart); row3.addWidget(bstop)
        lay.addLayout(row3)

        # View + status
        lay.addWidget(self.view,1)
        self.status=QLabel(self._status_text()); self.status.setStyleSheet(f"QLabel{{color:{GREY_TEXT_CSS};}}")
        lay.addWidget(self.status)

        # wiring
        self.timer=QTimer(self); self.timer.setInterval(30); self.timer.timeout.connect(self._tick)
        self.btn_mix_start.clicked.connect(lambda: self._set_mixer(True))
        self.btn_mix_stop.clicked.connect(lambda: self._set_mixer(False))
        self.btn_discharge.clicked.connect(self._do_discharge)
        self.btn_fs.clicked.connect(self.toggle_fullscreen)
        if not self.timer.isActive(): self.timer.start()

        self.showMaximized(); self.view.fit_to_items()

    # ===== Handlers =====
    def _ensure_timer(self):
        if not self.timer.isActive(): self.timer.start()

    def _set_cement_screw(self, run: bool):
        self.cement_screw_running = bool(run)
        if self.cement_outlet_badge: self.cement_outlet_badge.set_running(self.cement_screw_running)
        self._ensure_timer(); self._update_status()

    def _set_water_pump(self, run: bool):
        self.water_pump_running = bool(run)
        if self.water_pump: (self.water_pump.start() if run else self.water_pump.stop())
        if self.water_pump_badge: self.water_pump_badge.set_running(self.water_pump_running)
        self._ensure_timer(); self._update_status()

    def _set_admix_pump(self, run: bool):
        self.admix_pump_running = bool(run)
        if self.admix_pump: (self.admix_pump.start() if run else self.admix_pump.stop())
        if self.admix_pump_badge: self.admix_pump_badge.set_running(self.admix_pump_running)
        self._ensure_timer(); self._update_status()

    def _belt_start(self):
        if self.belt:
            self.belt.set_speed(float(self.cfg.get("belt", {}).get("speed", 3.0)) or 3.0)
            self.belt.start(); self._ensure_timer()

    def _belt_stop(self):
        if self.belt: self.belt.stop(); self.belt.set_speed(0.0)

    def _btn_style(self):
        return ("QPushButton { color:white; font-weight:600; padding:8px 12px; border-radius:10px; "
                "border:1px solid rgba(255,255,255,0.12); background:#2E3239; } "
                "QPushButton:hover { border-color: rgba(255,255,255,0.25);} ")

    def _btn_style_small(self):
        return ("QPushButton { color:white; font-weight:600; padding:6px 10px; border-radius:8px; "
                "border:1px solid rgba(255,255,255,0.12); background:#2E3239;} "
                "QPushButton:hover { border-color: rgba(255,255,255,0.25);} ")

    def _set_active_feeder(self, feeder_id:int):
        self.active_feeder = feeder_id; self._update_status()

    def _set_silo(self, n:int, run:bool):
        idx = n-1; silo = self.silos[idx]
        if run: silo.start()
        else:   silo.stop()
        if run and not self.timer.isActive(): self.timer.start()
        self._update_status()

    def _set_mixer(self, run:bool):
        if run: self.mixer.start()
        else:   self.mixer.stop()
        if run and not self.timer.isActive(): self.timer.start()
        self._update_status()

    def _bump_hopper(self, idx:int, delta:float):
        hp = self.hoppers[idx]
        new_w = max(0.0, min(hp.get_weight_kg()+delta, hp.get_capacity_kg()))
        hp.set_weight_kg(new_w)
        if self.collector and hasattr(self.collector,"set_active_and_amount"):
            self.collector.set_active_and_amount(idx, new_w)
        if hasattr(hp,"set_dosing"): hp.set_dosing(True)
        self._ensure_timer(); self._update_status()

    def _set_hopper(self, idx:int, kg:float):
        hp = self.hoppers[idx]
        hp.set_weight_kg(max(0.0, min(kg, hp.get_capacity_kg())))
        if self.collector and hasattr(self.collector,"set_active_and_amount"):
            self.collector.set_active_and_amount(idx, hp.get_weight_kg())
        if hasattr(hp,"set_dosing"): hp.set_dosing(True)
        self._ensure_timer(); self._update_status()

    def _do_discharge(self):
        self.mixer.open_gate(); self.mixer.stop()
        self._write_batch_csv()
        self._update_status(tag="DISCHARGING")
        QTimer.singleShot(1200, self._finish_discharge)

    def _finish_discharge(self):
        self.mixer.close_gate(); self._update_status()

    def _write_batch_csv(self):
        a = [hp.get_weight_kg() for hp in self.hoppers]; tot = sum(a)
        def varpct(t,x): return 0.0 if t==0 else (x-t)*100.0/t
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.recipe,
            f"{self.t_agg[0]:.0f}", f"{a[0]:.0f}", f"{varpct(self.t_agg[0],a[0]):.2f}",
            f"{self.t_agg[1]:.0f}", f"{a[1]:.0f}", f"{varpct(self.t_agg[1],a[1]):.2f}",
            f"{self.t_agg[2]:.0f}", f"{a[2]:.0f}", f"{varpct(self.t_agg[2],a[2]):.2f}",
            f"{self.t_agg[3]:.0f}", f"{a[3]:.0f}", f"{varpct(self.t_agg[3],a[3]):.2f}",
            f"{self.t_total:.0f}", f"{tot:.0f}", f"{varpct(self.t_total,tot):.2f}"
        ]
        with open(BATCH_LOG,"a",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow(row)

    def _tick(self):
        spd = self.cfg["speeds"]

        # badges follow pump outlets
        if getattr(self, "cement_outlet_badge", None): self.cement_outlet_badge.refresh()
        if getattr(self, "water_pump_badge", None): self.water_pump_badge.refresh()
        if getattr(self, "admix_pump_badge", None): self.admix_pump_badge.refresh()

        # interlocks (close when hoppers almost full)
        if self.cement_hopper and self.cement_hopper.get_weight_kg() >= self.cement_hopper.get_capacity_kg()*0.995:
            self.cement_screw_running = False
            if self.cement_outlet_badge: self.cement_outlet_badge.set_running(False)
        if self.water_hopper and self.water_hopper.get_weight_kg() >= self.water_hopper.get_capacity_kg()*0.995:
            self.water_pump_running = False
            if self.water_pump_badge: self.water_pump_badge.set_running(False)
            if getattr(self, "water_pump", None): self.water_pump.stop()
        if self.admix_hopper and self.admix_hopper.get_weight_kg() >= self.admix_hopper.get_capacity_kg()*0.995:
            self.admix_pump_running = False
            if self.admix_pump_badge: self.admix_pump_badge.set_running(False)
            if getattr(self, "admix_pump", None): self.admix_pump.stop()

        # demo: silo fill/bleed (local sim; replace with PLC reads later)
        for silo in self.silos:
            pct = silo.get_percent()
            delta = spd["silo_fill_per_tick"] if silo.is_running() else spd["silo_bleed_per_tick"]
            silo.set_percent(max(0.0, min(100.0, pct + delta)))

        # mixer anim
        self.mixer.advance_phase(spd["mixer_arrow_deg_per_tick"])

        # agg glow
        for hp in self.hoppers: hp.advance_phase(2.4)

        # collector + belt
        if self.collector:
            amounts=[hp.get_weight_kg() for hp in self.hoppers]
            if hasattr(self.collector,"set_segment_amounts"):
                self.collector.set_segment_amounts(amounts)
                act_idx=max(0,min(len(self.hoppers)-1,self.active_feeder-1))
                self.collector.set_active_segment(act_idx)
                self.collector.advance_phase(2.4)

        if self.belt:
            if self.collector: self.belt.set_length(self.collector.w)
            self.belt.advance_phase(1.0)

        # progress bars
        for i,pb in enumerate(self.pb_aggs):
            actual=self.hoppers[i].get_weight_kg(); target=self.t_agg[i]
            pb.setMaximum(int(max(1,target))); pb.setValue(int(min(actual,target)))
            pct = 0 if target==0 else int(round(actual*100.0/target))
            title=getattr(self.hoppers[i],"_title",f"Agg {i+1}")
            pb.setFormat(f"{title} {pct}% ({actual:.0f}/{target:.0f} kg)")

        total=sum(hp.get_weight_kg() for hp in self.hoppers)
        self.pb_total.setMaximum(int(max(1,self.t_total))); self.pb_total.setValue(int(min(total,self.t_total)))
        pct_t = 0 if self.t_total==0 else int(round(total*100.0/self.t_total))
        self.pb_total.setFormat(f"TOTAL %p% ({total:.0f}/{self.t_total:.0f} kg)")
        self._update_status()

    def _status_text(self, tag: str | None = None):
        parts=[]
        for i,silo in enumerate(self.silos,start=1):
            st="RUNNING" if silo.is_running() else "STOPPED"
            parts.append(f"Silo{i}: {st} • {int(round(silo.get_percent()))}%")
        for i,hp in enumerate(self.hoppers,start=1):
            parts.append(f"Agg{i}: {hp.get_weight_kg():.0f}/{hp.get_capacity_kg():.0f} kg")
        if self.cement_hopper:
            parts.append(f"Cement: {self.cement_hopper.get_weight_kg():.0f}/{self.cement_hopper.get_capacity_kg():.0f} kg")
        if self.water_hopper:
            parts.append(f"Water: {self.water_hopper.get_weight_kg():.0f}/{self.water_hopper.get_capacity_kg():.0f} kg")
        if self.admix_hopper:
            parts.append(f"Admixture: {self.admix_hopper.get_weight_kg():.0f}/{self.admix_hopper.get_capacity_kg():.0f} kg")
        parts.append(f"Water Tank: {self.water_tank_kg:.0f}/{self.water_tank_capacity_kg:.0f} kg")
        parts.append(f"Admix Tank: {self.admix_tank_kg:.0f}/{self.admix_tank_capacity_kg:.0f} kg")
        m_state="RUNNING" if self.mixer.is_running() else ("DISCHARGING" if tag=="DISCHARGING" else "STOPPED")
        parts.append(f"Mixer: {m_state}")
        parts.append(f"Cement Screw: {'ON' if self.cement_screw_running else 'OFF'}")
        parts.append(f"Water Pump: {'ON' if self.water_pump_running else 'OFF'}")
        parts.append(f"Admix Pump: {'ON' if self.admix_pump_running else 'OFF'}")
        if self.silos and hasattr(self, "active_feeder"):
            parts.append(f"Active Feeder: Silo {self.active_feeder}")
        return "   |   ".join(parts)

    def _update_status(self, tag: str | None = None):
        self.status.setText(self._status_text(tag))

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal(); self.showMaximized(); self.btn_fs.setText("Fullscreen (F11)")
        else:
            self.showFullScreen(); self.btn_fs.setText("Exit Fullscreen (F11)")
        self.view.fit_to_items()

def main():
    import sys
    cfg = load_config()
    app = QApplication(sys.argv)
    w = MainWindow(cfg)
    w.setWindowFlag(Qt.Window); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
