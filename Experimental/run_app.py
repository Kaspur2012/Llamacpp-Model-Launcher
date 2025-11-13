import sys
from PyQt6.QtWidgets import QApplication

# Use absolute imports from the top-level package
from Llamacpp_Model_launcher.ui import MainWindow, get_dark_palette
from Llamacpp_Model_launcher.system_analyzer import initialize_pynvml, shutdown_pynvml


def main():
    """The main entry point for the application."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setPalette(get_dark_palette())

    initialize_pynvml()
    app.aboutToQuit.connect(shutdown_pynvml)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
