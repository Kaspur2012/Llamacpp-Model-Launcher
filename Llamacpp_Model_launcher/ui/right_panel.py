# ui/right_panel.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QScrollArea, QFormLayout, QFrame, QPushButton, QCheckBox,
                             QMessageBox, QFileDialog, QTextEdit)
from PyQt6.QtGui import QFont
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
    llamacpp_dir_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dirty = False
        self._is_ninfer_model = False
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

        # Environment Variables Editor
        env_frame = QFrame()
        env_frame.setFrameShape(QFrame.Shape.StyledPanel)
        env_frame.setStyleSheet("QFrame { background-color: #2D323B; border: 1px solid #40454E; border-radius: 4px; }")
        env_layout = QVBoxLayout(env_frame)
        env_layout.setContentsMargins(8, 6, 8, 6)
        env_layout.setSpacing(4)
        env_title = QLabel("Environment Variables")
        env_title.setStyleSheet("font-weight: bold; color: #D1D1D1; font-size: 10pt; background: transparent;")
        env_hint = QLabel('One per line: KEY=value  (e.g., MTMD_BACKEND_DEVICE=cuda1) — do not include "set"')
        env_hint.setStyleSheet("color: #808080; font-size: 8pt; background: transparent;")
        self.env_vars_input = QTextEdit()
        self.env_vars_input.setPlaceholderText("MTMD_BACKEND_DEVICE=cuda1")
        self.env_vars_input.setMaximumHeight(60)
        self.env_vars_input.setFont(QFont('Menlo', 9))
        self.env_vars_input.setStyleSheet(
            "QTextEdit { background-color: #252930; color: #E0E0E0; border: 1px solid #505660; "
            "border-radius: 4px; padding: 4px; font-size: 9pt; } "
            "QTextEdit:focus { border: 1px solid #4D90E2; }"
        )
        self.env_vars_input.textChanged.connect(self._mark_as_dirty)
        env_layout.addWidget(env_title)
        env_layout.addWidget(env_hint)
        env_layout.addWidget(self.env_vars_input)
        layout.addWidget(env_frame)

        # Llama.cpp Directory Override
        dir_frame = QFrame()
        dir_frame.setFrameShape(QFrame.Shape.StyledPanel)
        dir_frame.setStyleSheet("QFrame { background-color: #2D323B; border: 1px solid #40454E; border-radius: 4px; }")
        dir_layout = QVBoxLayout(dir_frame)
        dir_layout.setContentsMargins(8, 6, 8, 6)
        dir_layout.setSpacing(4)
        dir_title = QLabel("Llama.cpp Directory (per-model)")
        dir_title.setStyleSheet("font-weight: bold; color: #D1D1D1; font-size: 10pt; background: transparent;")
        dir_hint = QLabel('Override the global Llama.cpp directory for this model (e.g., CUDA vs Vulkan build)')
        dir_hint.setStyleSheet("color: #808080; font-size: 8pt; background: transparent;")
        dir_hint.setWordWrap(True)
        dir_input_layout = QHBoxLayout()
        self.llamacpp_dir_input = QLineEdit()
        self.llamacpp_dir_input.setPlaceholderText("Leave empty to use global directory from config.ini")
        self.llamacpp_dir_input.setFont(QFont('Menlo', 9))
        self.llamacpp_dir_input.setStyleSheet(
            "QLineEdit { background-color: #252930; color: #E0E0E0; border: 1px solid #505660; "
            "border-radius: 4px; padding: 4px; font-size: 9pt; } "
            "QLineEdit:focus { border: 1px solid #4D90E2; }"
        )
        self.llamacpp_dir_input.textChanged.connect(self._mark_as_dirty)
        self.llamacpp_dir_input.textChanged.connect(self.llamacpp_dir_changed)
        dir_input_layout.addWidget(self.llamacpp_dir_input, 1)
        dir_browse_button = QPushButton("Browse...")
        dir_browse_button.clicked.connect(lambda: self._browse_directory())
        dir_input_layout.addWidget(dir_browse_button)
        dir_clear_button = QPushButton("\u00d7")
        dir_clear_button.setFixedWidth(24)
        dir_clear_button.setToolTip("Clear per-model directory (use global)")
        dir_clear_button.setStyleSheet(
            "QPushButton { background-color: #4A4A5A; color: #CCC; border: 1px solid #555; "
            "border-radius: 3px; font-size: 10pt; font-weight: bold; padding: 2px 4px; } "
            "QPushButton:hover { background-color: #5A5A6A; color: white; }"
        )
        dir_clear_button.clicked.connect(lambda: self._clear_llamacpp_dir())
        dir_input_layout.addWidget(dir_clear_button)
        dir_layout.addWidget(dir_title)
        dir_layout.addWidget(dir_hint)
        dir_layout.addLayout(dir_input_layout)
        layout.addWidget(dir_frame)

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

    def populate(self, command_parts: list[Parameter], model_name: str, env_vars=None, llamacpp_dir=None, is_ninfer=False):
        """Clears and fills the editor with a new set of parameters.

        env_vars and llamacpp_dir default to None (leave as-is) so callers that
        forget to pass them won't silently wipe the user's input.
        """
        self._is_ninfer_model = is_ninfer
        # Block signals on the container widget to prevent textChanged from firing
        self.param_widget.blockSignals(True)
        self.env_vars_input.blockSignals(True)
        try:
            while self.param_layout.rowCount() > 0:
                self.param_layout.removeRow(0)

            self.model_name_input.blockSignals(True)
            self.model_name_input.setText(model_name)
            self.model_name_input.blockSignals(False)

            if env_vars is not None:
                self.env_vars_input.setPlainText(env_vars)

            self.llamacpp_dir_input.blockSignals(True)
            if llamacpp_dir is not None:
                self.llamacpp_dir_input.setText(llamacpp_dir)
            self.llamacpp_dir_input.blockSignals(False)

            if not command_parts: return
            for param in command_parts:
                self.add_parameter_row(param.key, param.value)
        finally:
            # IMPORTANT: Unblock signals after setup is complete
            self.param_widget.blockSignals(False)
            self.env_vars_input.blockSignals(False)

        self.clear_dirty_state()

    def _browse_file(self, line_edit, file_filter=None):
        """Helper to open file dialog and set line edit text."""
        if file_filter is None:
            file_filter = "Model Files (*.gguf *.ninfer);;GGUF Files (*.gguf);;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if path:
            line_edit.setText(path)

    @staticmethod
    def _is_file_path(value):
        """Detect if a value looks like a file or directory path.
        Returns ('file', filter) or ('dir',) or None."""
        import os
        if not value or not isinstance(value, str):
            return None
        # Remove surrounding quotes if present
        clean = value.strip('"\'')
        known_file_exts = {'.gguf', '.ggsuf', '.bin', '.safetensors', '.pth', '.ckpt', '.pt',
                           '.onnx', '.ggml', '.json', '.txt', '.jinja', '.yaml', '.yml',
                           '.ini', '.cfg', '.conf', '.xml', '.html', '.md', '.csv', '.log',
                           '.dat', '.model', '.weights', '.ninfer'}
        # Windows absolute path (e.g., D:\path\to\file)
        if len(clean) >= 3 and clean[1:3] == ':\\' and clean[0].isalpha():
            _, ext = os.path.splitext(clean)
            if ext.lower() in known_file_exts:
                return ('file', clean)
            return ('dir',)
        # Unix absolute path
        if clean.startswith('/'):
            _, ext = os.path.splitext(clean)
            if ext.lower() in known_file_exts:
                return ('file', clean)
            return ('dir',)
        # Relative path with extension
        _, ext = os.path.splitext(clean)
        if ext and ext.lower() in known_file_exts:
            return ('file', clean)
        return None

    def add_parameter_row(self, param_key, param_value):
        """Adds a single row to the parameter editor form and connects its signals."""
        field_container = QWidget()
        field_layout = QHBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)

        # Determine if this parameter's value is a file/directory path
        path_info = None
        if param_value is not None:
            path_info = self._is_file_path(param_value)

        # Determine file filter based on path extension
        def get_file_filter(path_value):
            if not path_value:
                return "Model Files (*.gguf *.ninfer);;GGUF Files (*.gguf);;All Files (*)"
            lower = path_value.lower()
            if lower.endswith('.ninfer'):
                return "NInfer Models (*.ninfer);;All Files (*)"
            if lower.endswith('.gguf'):
                return "GGUF Files (*.gguf);;All Files (*)"
            elif lower.endswith(('.jinja', '.txt', '.json')):
                return "Jinja Templates (*.jinja);;Text Files (*.txt *.jinja *.json);;All Files (*)"
            else:
                return "All Files (*)"

        if path_info and path_info[0] == 'file':
            input_widget = QLineEdit(param_value)
            browse_button = QPushButton("Browse...")
            browse_button.setProperty("param_type", param_key)
            file_filter = get_file_filter(path_info[1])
            browse_button.clicked.connect(lambda _, le=input_widget, f=file_filter: self._browse_file(le, f))
            field_layout.addWidget(input_widget)
            field_layout.addWidget(browse_button)
        elif path_info and path_info[0] == 'dir':
            input_widget = QLineEdit(param_value)
            browse_button = QPushButton("Browse...")
            browse_button.setToolTip("Browse for directory")
            browse_button.clicked.connect(lambda _, le=input_widget: self._browse_directory_param(le))
            field_layout.addWidget(input_widget)
            field_layout.addWidget(browse_button)
        elif param_value is None:
            input_widget = QCheckBox()
            input_widget.setChecked(True)
            field_layout.addWidget(input_widget)
        else:
            input_widget = QLineEdit(param_value)
            field_layout.addWidget(input_widget)

        # Tag the actual input widget so get_parameters() can find it reliably
        # instead of assuming it's always the first item in the container layout.
        input_widget.setProperty("is_param_input", True)

        # Signals are now connected unconditionally
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

        # Display label — show "Model Path (positional)" for NInfer's -m
        display_label = param_key
        if self._is_ninfer_model and param_key == '-m':
            display_label = "Model Path (positional)"

        label_widget = QLabel(display_label)
        # Store the original key so get_parameters() can retrieve it
        label_widget.setProperty("param_key", param_key)
        self.param_layout.addRow(label_widget, field_container)
        return input_widget

    def _remove_parameter_row(self):
        clicked_button = self.sender()
        if not clicked_button: return
        for i in range(self.param_layout.rowCount()):
            if self.param_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget() == clicked_button.parent():
                self.param_layout.removeRow(i)
                self._mark_as_dirty()
                break

    def _add_new_parameter_from_input(self):
        param_name = self.new_param_name_input.text().strip()
        param_value = self.new_param_value_input.text().strip()

        if not param_name or not param_name.startswith('-'):
            QMessageBox.warning(self, "Input Error", "Parameter must start with '-' or '--'.")
            return

        for i in range(self.param_layout.rowCount()):
            label_widget = self.param_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            # Check against both stored key and display text
            existing_key = label_widget.property("param_key") or label_widget.text()
            if label_widget.text() == param_name or existing_key == param_name:
                reply = QMessageBox.question(self, "Parameter Exists",
                                             f"Parameter '{param_name}' already exists. Add anyway?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return
                else:
                    break

        self.add_parameter_row(param_name, param_value if param_value else None)
        self.new_param_name_input.clear()
        self.new_param_value_input.clear()
        self._mark_as_dirty()

    @staticmethod
    def _find_param_input_widget(field_widget):
        """Locates the tagged input widget inside a parameter row's field container.

        Uses the "is_param_input" property set in add_parameter_row() instead of
        assuming the input is always at layout index 0 — keeps this resilient to
        future changes in row layout (icons, warning labels, etc. added before it).
        """
        layout = field_widget.layout()
        if layout is None:
            return None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget() if item else None
            if widget is not None and widget.property("is_param_input"):
                return widget
        # Fallback for safety: behave like the old code if nothing was tagged
        # (shouldn't happen for rows created via add_parameter_row).
        first_item = layout.itemAt(0) if layout.count() > 0 else None
        return first_item.widget() if first_item else None

    def get_parameters(self) -> list[Parameter]:
        """Reads all parameters from the editor and returns them as a list."""
        params = []
        for i in range(self.param_layout.rowCount()):
            label_widget = self.param_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            # Use the stored original key (e.g. "-m") instead of display text (e.g. "Model Path (positional)")
            param_key = label_widget.property("param_key") or label_widget.text()
            field_widget = self.param_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget()
            input_widget = self._find_param_input_widget(field_widget)

            if isinstance(input_widget, QCheckBox):
                if input_widget.isChecked():
                    params.append(Parameter(param_key, None))
            elif isinstance(input_widget, QLineEdit):
                params.append(Parameter(param_key, input_widget.text().strip()))
        return params

    def get_model_name(self) -> str:
        """Returns the current text from the model name input field."""
        return self.model_name_input.text().strip().replace(' (*)', '')

    def get_env_vars(self) -> str:
        """Returns the raw environment variables text."""
        return self.env_vars_input.toPlainText().strip()

    def set_env_vars(self, text: str):
        """Sets the environment variables text."""
        self.env_vars_input.blockSignals(True)
        self.env_vars_input.setPlainText(text)
        self.env_vars_input.blockSignals(False)

    def get_llamacpp_dir(self) -> str:
        """Returns the per-model Llama.cpp directory path."""
        return self.llamacpp_dir_input.text().strip()

    def set_llamacpp_dir(self, path: str):
        """Sets the per-model Llama.cpp directory path."""
        self.llamacpp_dir_input.blockSignals(True)
        self.llamacpp_dir_input.setText(path)
        self.llamacpp_dir_input.blockSignals(False)

    def _browse_directory(self):
        """Open a directory browser dialog for the Llama.cpp directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Llama.cpp Directory")
        if directory:
            self.llamacpp_dir_input.setText(directory)

    def _browse_directory_param(self, line_edit):
        """Open a directory browser dialog for a parameter value."""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            line_edit.setText(directory)

    def _clear_llamacpp_dir(self):
        """Clear the per-model Llama.cpp directory (fall back to global)."""
        self.llamacpp_dir_input.clear()

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