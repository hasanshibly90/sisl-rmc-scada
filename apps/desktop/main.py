from pathlib import Path
import sys, traceback, os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QStatusBar, QMessageBox

BASE = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE))  # make "components" & "contracts.py" importable

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SISL — RMC SCADA Desktop")
        self.resize(1280, 800)
        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status.showMessage("Booting…")
        self._central = self._boot_plant_view_with_fallback()
        self.setCentralWidget(self._central)
        self._tick = QTimer(self); self._tick.setInterval(500)
        self._tick.timeout.connect(self._on_tick); self._tick.start()
        act_full = QAction("Toggle Fullscreen", self); act_full.setShortcut(QKeySequence(Qt.Key_F11))
        act_full.triggered.connect(self._toggle_fullscreen); self.addAction(act_full)
        act_esc = QAction("Exit Fullscreen", self); act_esc.setShortcut(QKeySequence(Qt.Key_Escape))
        act_esc.triggered.connect(self._exit_fullscreen); self.addAction(act_esc)

    def _boot_plant_view_with_fallback(self) -> QWidget:
        try:
            from components.plant_view import PlantView
            w = PlantView()
            self.status.showMessage("PlantView ready"); return w
        except Exception:
            print("\n[PlantView] Failed to load. Traceback:\n", flush=True)
            traceback.print_exc()
            msg = QLabel(
                "RMC Desktop boot…\n\n"
                "PlantView failed to import or construct.\n"
                "✔ Check that 'components/' and 'contracts.py' exist\n"
                f"✔ Running from: {BASE}\n\n"
                "Open the console for the full traceback."
            )
            msg.setAlignment(Qt.AlignLeft | Qt.AlignTop); msg.setMargin(14)
            self.status.showMessage("Fallback view (see console)"); return msg

    def _toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal(); self.status.showMessage("Windowed", 1500)
        else: self.showFullScreen(); self.status.showMessage("Fullscreen", 1500)

    def _exit_fullscreen(self):
        if self.isFullScreen(): self.showNormal(); self.status.showMessage("Windowed", 1500)

    def _on_tick(self): pass

if __name__ == "__main__":
    os.environ.setdefault("PYTHONFAULTHANDLER", "1")
    print("[RMC] Starting desktop…"); print(f"[RMC] BASE = {BASE}")
    try:
        app = QApplication(sys.argv)
        win = MainWindow(); win.show()
        sys.exit(app.exec())
    except Exception:
        print("\n[CRASH] Unhandled exception in main.py:\n"); traceback.print_exc()
        try: QMessageBox.critical(None, "RMC Desktop — Crash", traceback.format_exc())
        except Exception: pass
        input("\nPress Enter to close…")
