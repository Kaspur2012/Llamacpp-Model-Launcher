# ui/left_panel.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QCheckBox, QStackedWidget, QTextEdit)
from PyQt6.QtGui import QFont
# --- FIX: Added the missing import for pyqtSignal ---
from PyQt6.QtCore import pyqtSignal
# ---------------------------------------------------
from parameter_browser import ParameterBrowser
from Llamacpp_Model_launcher.parameters_db import HELP_DOCUMENTATION


class LeftPanel(QWidget):
    """Manages the main control and display area of the application."""
    # Signals for user actions
    dir_browse_clicked = pyqtSignal()
    file_browse_clicked = pyqtSignal()
    model_selected = pyqtSignal(int)
    load_model_clicked = pyqtSignal()
    unload_model_clicked = pyqtSignal()
    tune_model_clicked = pyqtSignal()
    exit_clicked = pyqtSignal()
    webui_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._showing_commands = False
        self._showing_help = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Top Path Selection ---
        path_layout = QHBoxLayout()
        self.llamacpp_dir_label = QLabel('Llama.cpp Directory: Not Set')
        self.llamacpp_dir_label.setWordWrap(True)
        browse_dir_button = QPushButton('Browse...')
        browse_dir_button.clicked.connect(self.dir_browse_clicked)

        self.models_file_label = QLabel('Models File: Not Set')
        self.models_file_label.setWordWrap(True)
        browse_file_button = QPushButton('Browse...')
        browse_file_button.clicked.connect(self.file_browse_clicked)

        path_layout.addWidget(self.llamacpp_dir_label, 1)
        path_layout.addWidget(browse_dir_button)
        path_layout.addWidget(self.models_file_label, 1)
        path_layout.addWidget(browse_file_button)
        layout.addLayout(path_layout)

        # --- Model Dropdown and Options ---
        self.model_dropdown = QComboBox()
        self.model_dropdown.currentIndexChanged.connect(self.model_selected)
        layout.addWidget(self.model_dropdown)

        options_layout = QHBoxLayout()
        self.webui_checkbox = QCheckBox('Enable Web UI')
        self.webui_checkbox.setChecked(True)
        self.webui_checkbox.stateChanged.connect(lambda state: self.webui_toggled.emit(state == 2))
        self.open_on_load_checkbox = QCheckBox('Auto-Open Web UI')
        self.open_on_load_checkbox.setChecked(True)
        options_layout.addWidget(self.webui_checkbox)
        options_layout.addWidget(self.open_on_load_checkbox)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # --- Process Controls ---
        controls_layout = QHBoxLayout()
        self.load_button = QPushButton('Load Model')
        self.unload_button = QPushButton('Unload Model')
        self.tuning_wizard_button = QPushButton("Tune Model")
        self.tuning_wizard_button.setStyleSheet("font-weight: bold;")
        self.commands_button = QPushButton('Commands')
        self.help_button = QPushButton('Help')
        self.exit_button = QPushButton('Exit')

        self.load_button.clicked.connect(self.load_model_clicked)
        self.unload_button.clicked.connect(self.unload_model_clicked)
        self.tuning_wizard_button.clicked.connect(self.tune_model_clicked)
        self.exit_button.clicked.connect(self.exit_clicked)
        self.commands_button.clicked.connect(self._toggle_commands_view)
        self.help_button.clicked.connect(self._toggle_help_view)

        self.status_label = QLabel('Status: Unloaded')
        self.status_indicator = QLabel()

        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(self.unload_button)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.status_indicator)
        controls_layout.addWidget(self.status_label)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.tuning_wizard_button)
        controls_layout.addWidget(self.commands_button)
        controls_layout.addWidget(self.help_button)
        controls_layout.addWidget(self.exit_button)
        layout.addLayout(controls_layout)

        # --- Main View Stack ---
        self.view_stack = QStackedWidget()
        self.output_viewer = QTextEdit()
        self.output_viewer.setReadOnly(True)
        self.output_viewer.setFont(QFont('Courier', 10))

        self.parameter_browser = ParameterBrowser()  # Instantiate child widget

        self.help_viewer = QTextEdit()
        self.help_viewer.setReadOnly(True)

        self.view_stack.addWidget(self.output_viewer)
        self.view_stack.addWidget(self.parameter_browser)
        self.view_stack.addWidget(self.help_viewer)
        layout.addWidget(self.view_stack)

    def _set_view(self, index):
        self.view_stack.setCurrentIndex(index)
        self._showing_commands = (index == 1)
        self._showing_help = (index == 2)
        self.commands_button.setText("Show Output" if self._showing_commands else "Commands")
        self.help_button.setText("Show Output" if self._showing_help else "Help")

    def _toggle_commands_view(self):
        self._set_view(0 if self._showing_commands else 1)

    def _toggle_help_view(self):
        if self._showing_help:
            self._set_view(0)
        else:
            self._load_and_display_documentation()
            self._set_view(2)

    def _load_and_display_documentation(self):
        if self.help_viewer.toPlainText(): return
        if HELP_DOCUMENTATION:
            self.help_viewer.setMarkdown(HELP_DOCUMENTATION)
        else:
            self.help_viewer.setMarkdown("### Error\nHelp documentation could not be loaded.")

    # --- Public methods for the main window to call ---

    def update_path_labels(self, dir_path, models_path, dir_valid, models_valid):
        error_style = "color: #F44336; font-weight: bold;"

        if not dir_path:
            self.llamacpp_dir_label.setText('Llama.cpp Directory: Not Set')
            self.llamacpp_dir_label.setStyleSheet("")
        elif not dir_valid:
            self.llamacpp_dir_label.setText('Llama.cpp Directory: NOT FOUND')
            self.llamacpp_dir_label.setStyleSheet(error_style)
        else:
            self.llamacpp_dir_label.setText(f'Llama.cpp Directory: {dir_path}')
            self.llamacpp_dir_label.setStyleSheet("")

        if not models_path:
            self.models_file_label.setText('Models File: Not Set')
            self.models_file_label.setStyleSheet("")
        elif not models_valid:
            self.models_file_label.setText('Models File: NOT FOUND')
            self.models_file_label.setStyleSheet(error_style)
        else:
            self.models_file_label.setText(f'Models File: {models_path}')
            self.models_file_label.setStyleSheet("")

    def set_status(self, status_enum):
        self.status_label.setText(status_enum.label)
        self.status_indicator.setStyleSheet(
            f"background-color: {status_enum.color}; border-radius: 10px; min-width: 20px; min-height: 20px;")

    def update_button_states(self, can_load, is_running):
        self.load_button.setEnabled(can_load)
        self.unload_button.setEnabled(is_running)
        self.tuning_wizard_button.setEnabled(can_load)

    def populate_dropdown(self, model_names):
        self.model_dropdown.blockSignals(True)
        self.model_dropdown.clear()
        if model_names:
            self.model_dropdown.addItems(model_names)
        self.model_dropdown.blockSignals(False)

    def set_dropdown_index(self, index):
        self.model_dropdown.blockSignals(True)
        self.model_dropdown.setCurrentIndex(index)
        self.model_dropdown.blockSignals(False)

    def append_output(self, text):
        self.output_viewer.append(text)
        self.output_viewer.verticalScrollBar().setValue(self.output_viewer.verticalScrollBar().maximum())

    def clear_output(self):
        self.output_viewer.clear()

    def show_output_view(self):
        self._set_view(0)