import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow

os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName("epub-reader")
    print("desktopFileName =", app.desktopFileName())

    icon = QIcon("assets/epub-reader.png")
    app.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)
    
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
