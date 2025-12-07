# Llamacpp_Model_launcher/core/workers.py

from PyQt6.QtCore import QObject, pyqtSignal


class ApiRequestWorker(QObject):
    """Worker thread for running API benchmark requests."""
    finished = pyqtSignal()

    def __init__(self, wizard_instance):
        super().__init__()
        self.wizard = wizard_instance

    def run(self):
        self.wizard.run_api_benchmark_requests()
        self.finished.emit()


class StabilityRequestWorker(QObject):
    """Worker thread for running the stability API request."""
    finished = pyqtSignal()

    def __init__(self, wizard_instance):
        super().__init__()
        self.wizard = wizard_instance

    def run(self):
        self.wizard.run_stability_api_request()
        self.finished.emit()
