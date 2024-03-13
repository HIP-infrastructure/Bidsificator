from PyQt6.QtWidgets import QApplication
from ui.MainWindow import MainWindow
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())