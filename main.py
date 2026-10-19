import os

os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
# os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QT_OPENGL"] = "software"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu "
    "--disable-gpu-compositing "
    "--disable-software-rasterizer "
    "--disable-vulkan "
    "--disable-features=Vulkan "
    "--disable-gpu-process"
)
os.environ["QT_LOGGING_RULES"] = "*.debug=false"

devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(devnull, 2)

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName("epub-reader")

    icon = QIcon("assets/epub-reader.png")
    app.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)

    print("Loading main window...")
    
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
