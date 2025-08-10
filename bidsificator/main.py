import sys

from PyQt6.QtWidgets import QApplication

from bidsificator.ui.MainWindow import MainWindow


def main() -> int | bool | None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
