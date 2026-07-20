import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from bidsificator.ui.MainWindow import MainWindow

LOGO_PATH = Path(__file__).parent / "resources" / "logo.png"


def main() -> int | bool | None:
    app = QApplication(sys.argv)
    # Application-wide icon: Dock icon on macOS, taskbar/window icon elsewhere
    app.setWindowIcon(QIcon(str(LOGO_PATH)))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
