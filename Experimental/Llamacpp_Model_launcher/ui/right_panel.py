# ui/right_panel.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QScrollArea, QFormLayout, QFrame, QPushButton, QCheckBox,
                             QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from Llamacpp_Model_launcher.core.command_builder import Parameter


class RightPanel(QWidget):
    """Manages the parameter editor for a selected model."""
    # Signals for actions taken within this panel
    save_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()
    add_new_clicked = pyqtSignal()
    duplicate_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    dirty_state_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dirty = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Model Name Editor
        name_frame = QFrame()
        name_layout = QHBoxLayout(name_frame)
        name_layout.setContentsMargins(0, 5, 0, 5)
        self.model_name_label = QLabel("Model Name:")
        self.model_name_input = QLineEdit()
        self.model_name_input.textChanged.connect(self._mark_as_dirty)
        name_layout.addWidget(self.model_name_label)
        name_layout.addWidget(self.model_name_input)
        layout.addWidget(name_frame)

        title = QLabel("Parameter Editor")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        # Parameter list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area, 1)
        self.param_widget = QWidget()
        self.param_layout = QFormLayout(self.param_widget)
        scroll_area.setWidget(self.param_widget)

        # Manual parameter adder
        add_frame = QFrame()
        add_frame.setFrameShape(QFrame.Shape.StyledPanel)
        add_layout = QVBoxLayout(add_frame)
        add_title = QLabel("Add New Parameter")
        add_title.setStyleSheet("font-weight: bold;")
        add_layout.addWidget(add_title)
        add_inputs_layout = QHBoxLayout()
        self.new_param_name_input = QLineEdit()
        self.new_param_name_input.setPlaceholderText("Parameter (e.g., --temp)")
        self.new_param_value_input = QLineEdit()
        self.new_param_value_input.setPlaceholderText("Value (leave empty for flags)")
        add_param_button = QPushButton("Add")
        add_param_button.clicked.connect(self._add_new_parameter_from_input)
        add_inputs_layout.addWidget(self.new_param_name_input, 1)
        add_inputs_layout.addWidget(self.new_param_value_input, 1)
        add_inputs_layout.addWidget(add_param_button)
        add_layout.addLayout(add_inputs_layout)
        layout.addWidget(add_frame)

        # Action Buttons
        button_layout = QHBoxLayout()
        add_model_button = QPushButton("Add")
        duplicate_model_button = QPushButton("Duplicate")
        delete_model_button = QPushButton("Delete")
        add_model_button.clicked.connect(self.add_new_clicked)
        duplicate_model_button.clicked.connect(self.duplicate_clicked)
        delete_model_button.clicked.connect(self.delete_clicked)

        reset_button = QPushButton("Reset")
        save_button = QPushButton("Save to File")
        reset_button.clicked.connect(self.reset_clicked)
        save_button.clicked.connect(self.save_clicked)

        button_layout.addWidget(add_model_button)
        button_layout.addWidget(duplicate_model_button)
        button_layout.addWidget(delete_model_button)
        button_layout.addStretch()
        button_layout.addWidget(reset_button)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

    # --- MODIFIED: Use blockSignals to prevent dirtying during initial load ---
    def populate(self, command_parts: list[Parameter], model_name: str):
        """Clears and fills the editor with a new set of parameters."""
        # Block signals on the container widget to prevent textChanged from firing
        self.param_widget.blockSignals(True)
        try:
            while self.param_layout.rowCount() > 0:
                self.param_layout.removeRow(0)

            self.model_name_input.blockSignals(True)
            self.model_name_input.setText(model_name)
            self.model_name_input.blockSignals(False)

            if not command_parts: return
            for param in command_parts:
                self.add_parameter_row(param.key, param.value)
        finally:
            # IMPORTANT: Unblock signals after setup is complete
            self.param_widget.blockSignals(False)

        self.clear_dirty_state()

    # --- MODIFIED: Simplified to always connect signals ---
    def add_parameter_row(self, param_key, param_value):
        """Adds a single row to the parameter editor form and connects its signals."""
        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)

        # Logic to decide which input widget to create
        if param_key in ("-m", "--model", "-md", "--model-draft", "--mmproj"):
            input_widget = QLineEdit(param_value)
            browse_button = QPushButton("Browse...")
            browse_button.setProperty("param_type", param_key)
            field_layout.addWidget(input_widget)
            field_layout.addWidget(browse_button)
        elif param_value is None:
            input_widget = QCheckBox()
            input_widget.setChecked(True)
            field_layout.addWidget(input_widget)
        else:
            input_widget = QLineEdit(param_value)
            field_layout.addWidget(input_widget)

        # --- FIX: Signals are now connected unconditionally ---
        if isinstance(input_widget, QLineEdit):
            input_widget.textChanged.connect(self._mark_as_dirty)
        elif isinstance(input_widget, QCheckBox):
            input_widget.stateChanged.connect(self._mark_as_dirty)

        remove_button = QPushButton("X")
        remove_button.setFixedWidth(30)
        remove_button.setToolTip(f"Remove {param_key}")
        if param_key == "Executable":
            remove_button.setEnabled(False)
        remove_button.clicked.connect(self._remove_parameter_row)
        field_layout.addWidget(remove_button)

        self.param_layout.addRow(QLabel(param_key), field_container)
        return input_widget

    def _remove_parameter_row(self):
        clicked_button = self.sender()
        if not clicked_button: return
        for i in range(self.param_layout.rowCount()):
            if self.param_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget() == clicked_button.parent():
                self.param_layout.removeRow(i)
                self._mark_as_dirty()
                break

    # --- MODIFIED: Call the simplified add_parameter_row ---
    def _add_new_parameter_from_input(self):
        param_name = self.new_param_name_input.text().strip()
        param_value = self.new_param_value_input.text().strip()

        if not param_name or not param_name.startswith('-'):
            QMessageBox.warning(self, "Input Error", "Parameter must start with '-' or '--'.")
            return

        for i in range(self.param_layout.rowCount()):
            label_widget = self.param_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            if label_widget.text() == param_name:
                reply = QMessageBox.question(self, "Parameter Exists",
                                             f"Parameter '{param_name}' already exists. Add anyway?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return

        self.add_parameter_row(param_name, param_value if param_value else None)
        self.new_param_name_input.clear()
        self.new_param_value_input.clear()
        self._mark_as_dirty()

    def get_parameters(self) -> list[Parameter]:
        """Reads all parameters from the editor and returns them as a list."""
        params = []
        for i in range(self.param_layout.rowCount()):
            label = self.param_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget().text()
            field_widget = self.param_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget()
            input_widget = field_widget.layout().itemAt(0).widget()

            if isinstance(input_widget, QCheckBox):
                if input_widget.isChecked():
                    params.append(Parameter(label, None))
            elif isinstance(input_widget, QLineEdit):
                params.append(Parameter(label, input_widget.text().strip()))
        return params

    def get_model_name(self) -> str:
        """Returns the current text from the model name input field."""
        return self.model_name_input.text().strip().replace(' (*)', '')

    def set_model_name(self, name):
        """Sets the text of the model name input field."""
        self.model_name_input.blockSignals(True)
        self.model_name_input.setText(name)
        self.model_name_input.blockSignals(False)

    def _mark_as_dirty(self):
        if self._is_dirty: return
        self._is_dirty = True
        current_text = self.model_name_input.text()
        if not current_text.endswith(' (*)'):
            self.model_name_input.setText(f"{current_text} (*)")
        self.dirty_state_changed.emit(True)

    def clear_dirty_state(self):
        if not self._is_dirty: return
        self._is_dirty = False
        self.set_model_name(self.get_model_name())  # This removes the asterisk
        self.dirty_state_changed.emit(False)