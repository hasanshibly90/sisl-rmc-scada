from PySide6.QtWidgets import QApplication, QLabel
import sys
app = QApplication(sys.argv)
w = QLabel("Qt OK — Hello SISL")
w.resize(320, 100)
w.show()
sys.exit(app.exec())