import sys
import os
import subprocess
import configparser
import tempfile
import webbrowser
import shlex
import re
from collections import defaultdict
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox,
    QCheckBox, QSplitter, QScrollArea, QFormLayout, QLineEdit, QFrame, QStackedWidget
)
from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon


class LlamaCppGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.process = None
        self.config_file = 'config.ini'
        self.llamacpp_dir = ''
        self.models_file = ''
        self.models = {}
        self.temp_batch_file = ''
        self.command_parts = []
        self.is_editing_new_model = False
        self.is_dirty = False
        self.previous_model_index = -1

        self.output_buffer = ""
        self.output_update_timer = QTimer(self)
        self.output_update_timer.setInterval(100)
        self.output_update_timer.timeout.connect(self.flush_output_buffer)

        self.showing_commands = False
        self.showing_help = False

        self.init_ui()
        self.load_config()
        self.parse_models_file()

    def init_ui(self):
        self.setWindowTitle('Llama.cpp Model Launcher')
        self.setGeometry(100, 100, 1450, 900)
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        left_panel = QWidget()
        self.setup_left_panel(left_panel)
        splitter.addWidget(left_panel)
        right_panel = QWidget()
        self.setup_right_panel(right_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([1050, 400])

    def setup_left_panel(self, parent):
        layout = QVBoxLayout(parent)
        controls_layout, options_layout = QHBoxLayout(), QHBoxLayout()
        self.llamacpp_dir_label = QLabel('Llama.cpp Directory: Not Set')
        self.llamacpp_dir_label.setWordWrap(True)
        browse_dir_button = QPushButton('Browse...')
        browse_dir_button.clicked.connect(self.browse_llamacpp_directory)
        self.models_file_label = QLabel('Models File: Not Set')
        self.models_file_label.setWordWrap(True)
        browse_file_button = QPushButton('Browse...')
        browse_file_button.clicked.connect(self.browse_models_file)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.llamacpp_dir_label, 1)
        path_layout.addWidget(browse_dir_button)
        path_layout.addWidget(self.models_file_label, 1)
        path_layout.addWidget(browse_file_button)
        self.model_dropdown = QComboBox()
        self.model_dropdown.currentIndexChanged.connect(self.model_selected)
        self.open_on_load_checkbox = QCheckBox('Auto-Open Web UI')
        self.open_on_load_checkbox.setChecked(True)
        self.open_on_load_checkbox.setToolTip("Opens the Web UI once, then unchecks itself.")
        self.webui_checkbox = QCheckBox('Enable Web UI')
        self.webui_checkbox.setChecked(True)
        self.webui_checkbox.setToolTip("Uncheck to add the '--no-webui' flag when loading a model.")
        self.webui_checkbox.stateChanged.connect(self.update_auto_open_visibility)
        options_layout.addWidget(self.webui_checkbox)
        options_layout.addWidget(self.open_on_load_checkbox)
        options_layout.addStretch()
        self.load_button = QPushButton('Load Model')
        self.unload_button = QPushButton('Unload Model')
        self.commands_button = QPushButton('Commands')
        self.help_button = QPushButton('Help')
        self.exit_button = QPushButton('Exit')
        self.load_button.clicked.connect(self.load_model)
        self.unload_button.clicked.connect(self.unload_model)
        self.commands_button.clicked.connect(self.toggle_commands_view)
        self.help_button.clicked.connect(self.toggle_help_view)
        self.exit_button.clicked.connect(self.close)
        self.status_label = QLabel('Status: Unloaded')
        self.status_indicator = QLabel()
        self.set_status('unloaded')
        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(self.unload_button)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.status_indicator)
        controls_layout.addWidget(self.status_label)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.commands_button)
        controls_layout.addWidget(self.help_button)
        controls_layout.addWidget(self.exit_button)
        self.view_stack = QStackedWidget()
        self.output_viewer = QTextEdit()
        self.output_viewer.setReadOnly(True)
        self.output_viewer.setFont(QFont('Courier', 10))
        self.commands_viewer = QTextEdit()
        self.commands_viewer.setReadOnly(True)
        self.commands_viewer.setFont(QFont('Courier', 10))
        self.help_viewer = QTextEdit()
        self.help_viewer.setReadOnly(True)
        self.view_stack.addWidget(self.output_viewer)
        self.view_stack.addWidget(self.commands_viewer)
        self.view_stack.addWidget(self.help_viewer)
        layout.addLayout(path_layout)
        layout.addWidget(self.model_dropdown)
        layout.addLayout(options_layout)
        layout.addLayout(controls_layout)
        layout.addWidget(self.view_stack)
        self.update_auto_open_visibility()

    def setup_right_panel(self, parent):
        layout = QVBoxLayout(parent)
        name_frame = QFrame()
        name_layout = QHBoxLayout(name_frame)
        name_layout.setContentsMargins(0, 5, 0, 5)
        self.model_name_label = QLabel("Model Name:")
        self.model_name_input = QLineEdit()
        self.model_name_input.textChanged.connect(self.mark_as_dirty)
        name_layout.addWidget(self.model_name_label)
        name_layout.addWidget(self.model_name_input)
        layout.addWidget(name_frame)
        title = QLabel("Parameter Editor")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area, 1)
        self.param_widget = QWidget()
        self.param_layout = QFormLayout(self.param_widget)
        scroll_area.setWidget(self.param_widget)
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
        add_param_button.clicked.connect(self.add_new_parameter_from_input)
        add_inputs_layout.addWidget(self.new_param_name_input, 1)
        add_inputs_layout.addWidget(self.new_param_value_input, 1)
        add_inputs_layout.addWidget(add_param_button)
        add_layout.addLayout(add_inputs_layout)
        layout.addWidget(add_frame)
        button_layout = QHBoxLayout()
        add_model_button = QPushButton("Add")
        duplicate_model_button = QPushButton("Duplicate")
        delete_model_button = QPushButton("Delete")
        add_model_button.clicked.connect(self.add_new_model)
        duplicate_model_button.clicked.connect(self.duplicate_model)
        delete_model_button.clicked.connect(self.delete_model)
        reset_button = QPushButton("Reset")
        save_button = QPushButton("Save to File")
        reset_button.clicked.connect(self.populate_editor_panel)
        save_button.clicked.connect(self.save_parameters)
        button_layout.addWidget(add_model_button)
        button_layout.addWidget(duplicate_model_button)
        button_layout.addWidget(delete_model_button)
        button_layout.addStretch()
        button_layout.addWidget(reset_button)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

    def set_view(self, index):
        self.view_stack.setCurrentIndex(index)
        self.showing_commands, self.showing_help = (index == 1), (index == 2)
        self.commands_button.setText("Show Output" if self.showing_commands else "Commands")
        self.help_button.setText("Show Output" if self.showing_help else "Help")

    def toggle_commands_view(self):
        if self.showing_commands:
            self.set_view(0)
        else:
            self.load_and_display_commands(); self.set_view(1)

    def toggle_help_view(self):
        if self.showing_help:
            self.set_view(0)
        else:
            self.load_and_display_documentation(); self.set_view(2)

    def load_and_display_commands(self):
        if self.commands_viewer.toPlainText(): return
        if not self.models_file:
            self.commands_viewer.setText("\n\nCannot load commands: 'Models File' path is not set.");
            return
        base_dir = os.path.dirname(self.models_file)
        commands_file_path = os.path.join(base_dir, 'models_commands.txt')
        if not os.path.exists(commands_file_path):
            error_msg = f"\n\nmodels_commands.txt not found.\n\nPlease make sure this file is in the same directory as your Models File:\n{base_dir}"
            self.commands_viewer.setText(error_msg);
            self.commands_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter);
            return
        try:
            with open(commands_file_path, 'r', encoding='utf-8') as f:
                self.commands_viewer.setText(f.read())
            self.commands_viewer.setAlignment(Qt.AlignmentFlag.AlignLeft)
        except Exception as e:
            self.commands_viewer.setText(f"Error: Failed to read the commands file:\n{e}")

    def load_and_display_documentation(self):
        if self.help_viewer.toPlainText(): return
        if not self.models_file:
            self.help_viewer.setMarkdown("### Error\nCannot load documentation: 'Models File' path is not set.");
            return
        base_dir = os.path.dirname(self.models_file)
        commands_file_path = os.path.join(base_dir, 'models_commands.txt')
        if not os.path.exists(commands_file_path):
            self.help_viewer.setMarkdown(
                f"### File Not Found\n\n`models_commands.txt` could not be found.\n\nPlease make sure it is in:\n`{base_dir}`");
            return
        try:
            with open(commands_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            doc_lines, in_doc_section = [], False
            for line in lines:
                if '-----Documentation-----' in line: in_doc_section = True; continue
                if in_doc_section: doc_lines.append(line)
            if doc_lines:
                self.help_viewer.setMarkdown("".join(doc_lines))
            else:
                self.help_viewer.setMarkdown(
                    "### No Documentation Found\nCould not find `-----Documentation-----` section in file.")
        except Exception as e:
            self.help_viewer.setMarkdown(f"### Error\nFailed to read file:\n`{e}`")

    def model_selected(self, index):
        if index == -1 or index == self.previous_model_index: return
        if self.is_dirty:
            reply = QMessageBox.question(self, 'Unsaved Changes',
                                         "You have unsaved changes. Do you want to save them before switching?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                self.save_parameters();
                return
            elif reply == QMessageBox.StandardButton.Cancel:
                self.model_dropdown.blockSignals(True)
                self.model_dropdown.setCurrentIndex(self.previous_model_index)
                self.model_dropdown.blockSignals(False)
                return

        self.model_name_input.blockSignals(True)
        self.param_widget.blockSignals(True)
        try:
            self.is_editing_new_model = False
            current_name = self.model_dropdown.itemText(index)
            if not current_name:
                self.model_name_input.clear();
                self.command_parts = [];
                self.populate_editor_panel();
                return
            self.model_name_input.setText(current_name)
            self.parse_command()
            self.populate_editor_panel()
        finally:
            self.model_name_input.blockSignals(False)
            self.param_widget.blockSignals(False)
        self.previous_model_index = index

    def parse_command(self):
        self.command_parts = [];
        model_name = self.model_dropdown.currentText()
        if not model_name: return
        command_str = self.models.get(model_name, "")
        if not command_str: return
        prefix_str, suffix_str = "", command_str
        path_matches = list(re.finditer(r'\S+\.gguf', command_str))
        if path_matches:
            split_point = path_matches[-1].end()
            prefix_str, suffix_str = command_str[:split_point], command_str[split_point:]
        try:
            prefix_tokens = shlex.split(prefix_str, posix=False)
        except ValueError:
            prefix_tokens = prefix_str.split()
        try:
            suffix_tokens = shlex.split(suffix_str, posix=True)
        except ValueError:
            suffix_tokens = suffix_str.split()
        all_tokens = prefix_tokens + suffix_tokens
        if not all_tokens: return
        self.command_parts.append((all_tokens[0], None))
        i = 1
        while i < len(all_tokens):
            part = all_tokens[i]
            if part.startswith('-'):
                if (i + 1 < len(all_tokens)) and not all_tokens[i + 1].startswith('-'):
                    self.command_parts.append((part, all_tokens[i + 1]));
                    i += 2
                else:
                    self.command_parts.append((part, None)); i += 1
            else:
                i += 1

    def populate_editor_panel(self):
        while self.param_layout.rowCount() > 0: self.param_layout.removeRow(0)
        if not self.command_parts: return
        self._add_parameter_row("Executable", self.command_parts[0][0])
        for param, value in self.command_parts[1:]: self._add_parameter_row(param, value)
        self.clear_dirty_state()

    def _add_parameter_row(self, param, value):
        field_container = QWidget()
        field_layout = QHBoxLayout(field_container);
        field_layout.setContentsMargins(0, 0, 0, 0)

        if param in ("-m", "--model", "-md", "--model-draft"):
            input_widget = QLineEdit(value)
            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(lambda: self.browse_for_model_file(input_widget))
            field_layout.addWidget(input_widget);
            field_layout.addWidget(browse_button)
        elif param == "--mmproj":
            input_widget = QLineEdit(value)
            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(lambda: self.browse_for_mmproj_file(input_widget))
            field_layout.addWidget(input_widget);
            field_layout.addWidget(browse_button)
        elif value is None:
            input_widget = QCheckBox();
            input_widget.setChecked(True);
            field_layout.addWidget(input_widget)
        else:
            input_widget = QLineEdit(value);
            field_layout.addWidget(input_widget)

        if isinstance(input_widget, QLineEdit):
            input_widget.textChanged.connect(self.mark_as_dirty)
        elif isinstance(input_widget, QCheckBox):
            input_widget.stateChanged.connect(self.mark_as_dirty)

        remove_button = QPushButton("X");
        remove_button.setFixedWidth(30)
        remove_button.setToolTip(f"Remove {param}")
        if param == "Executable": remove_button.setEnabled(False)
        remove_button.clicked.connect(self.remove_parameter_row)
        field_layout.addWidget(remove_button)
        self.param_layout.addRow(QLabel(param), field_container)

    # --- CORRECTED: This logic now correctly finds the row to delete ---
    def remove_parameter_row(self):
        clicked_button = self.sender()
        if not clicked_button:
            return

        # The button's direct parent widget is the container for the input field and the button.
        field_container_to_remove = clicked_button.parent()

        # Iterate through the form layout to find the row that contains this specific container widget.
        for i in range(self.param_layout.rowCount()):
            widget_in_row = self.param_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget()

            if widget_in_row == field_container_to_remove:
                self.param_layout.removeRow(i)
                self.mark_as_dirty()
                break # Exit the loop once the correct row has been found and removed.

    def add_new_parameter_from_input(self):
        param_name = self.new_param_name_input.text().strip()
        param_value = self.new_param_value_input.text().strip()
        if not param_name or not param_name.startswith('-'):
            QMessageBox.warning(self, "Input Error", "Parameter must start with '-' or '--'.");
            return

        parameter_exists = any(self.param_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget().text() == param_name
                               for i in range(self.param_layout.rowCount()))

        if parameter_exists:
            reply = QMessageBox.question(self, "Parameter Exists",
                                         f"The parameter '{param_name}' already exists.\n\n"
                                         "Some parameters (like -ot) can be added multiple times.\n\n"
                                         "Do you want to add it anyway?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        self._add_parameter_row(param_name, param_value if param_value else None)
        self.new_param_name_input.clear();
        self.new_param_value_input.clear()
        self.mark_as_dirty()

    def reconstruct_command(self):
        args_list = []
        for i in range(self.param_layout.rowCount()):
            label = self.param_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            field_container = self.param_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget()
            input_widget = field_container.layout().itemAt(0).widget()
            param = label.text()
            if param == "Executable": args_list.append(input_widget.text().strip()); continue
            if isinstance(input_widget, QCheckBox):
                if input_widget.isChecked(): args_list.append(param)
            elif isinstance(input_widget, QLineEdit):
                value = input_widget.text().strip()
                if value: args_list.extend([param, value])
        return subprocess.list2cmdline(args_list) if args_list else ""

    def add_new_model(self):
        if self.is_dirty and QMessageBox.question(self, 'Unsaved Changes', "Save unsaved changes first?",
                                                  QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Save:
            self.save_parameters();
            return
        self.is_editing_new_model = True
        base_name, new_name, count = "New Model", "New Model", 1
        while new_name in self.models: count += 1; new_name = f"{base_name} {count}"
        self.command_parts = [
            ('llama-server.exe', None), ('-m', 'D:\\path_to_your_model.gguf'), ('-c', '4096'),
            ('-fa', 'on'), ('--temp', '0.1'), ('--top-k', '64'), ('--top-p', '0.95'), ('--min-p', '0.05')]
        self.model_dropdown.blockSignals(True);
        self.model_dropdown.setCurrentIndex(-1);
        self.model_dropdown.blockSignals(False)
        self.model_name_input.blockSignals(True)
        try:
            self.model_name_input.setText(new_name)
        finally:
            self.model_name_input.blockSignals(False)
        self.populate_editor_panel();
        self.mark_as_dirty()

    def delete_model(self):
        model_to_delete = self.model_dropdown.currentText()
        if not model_to_delete: QMessageBox.warning(self, "Warning", "No model selected to delete."); return
        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     f"Are you sure you want to permanently delete '{model_to_delete}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(self.models_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                output_lines, skip_next_line = [], False
                for line in lines:
                    if skip_next_line: skip_next_line = False; continue
                    if line.strip() == model_to_delete: skip_next_line = True; continue
                    output_lines.append(line)
                with open(self.models_file, 'w', encoding='utf-8') as f:
                    f.writelines(output_lines)
                QMessageBox.information(self, "Success", f"'{model_to_delete}' was deleted.")
                self.clear_dirty_state();
                self.parse_models_file()
            except Exception as e:
                QMessageBox.critical(self, "File Error", f"Failed to delete model from file:\n{e}")

    def save_parameters(self):
        new_name = self.model_name_input.text().strip().replace(' (*)', '')
        if not new_name: QMessageBox.warning(self, "Input Error", "Model name cannot be empty."); return
        new_command = self.reconstruct_command()

        self.model_dropdown.blockSignals(True)
        try:
            if self.is_editing_new_model:
                if new_name in self.models:
                    QMessageBox.warning(self, "Input Error", f"A model named '{new_name}' already exists.");
                    return
                with open(self.models_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{new_name}\n{new_command}\n")
                self.is_editing_new_model = False;
                self.parse_models_file();
                self.model_dropdown.setCurrentText(new_name)
                QMessageBox.information(self, "Success", f"New model '{new_name}' was saved.")
            else:
                old_name = self.previous_model_index
                if old_name == -1: return
                old_name_text = self.model_dropdown.itemText(old_name)

                if new_name != old_name_text and new_name in self.models:
                    QMessageBox.warning(self, "Input Error", f"A model named '{new_name}' already exists.");
                    return

                with open(self.models_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                found = False
                for i, line in enumerate(lines):
                    if line.strip() == old_name_text:
                        lines[i], lines[i + 1] = new_name + '\n', new_command + '\n';
                        found = True;
                        break
                if not found:
                    QMessageBox.critical(self, "Error", f"Could not find '{old_name_text}' in file.");
                    return

                with open(self.models_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                self.parse_models_file();
                self.model_dropdown.setCurrentText(new_name)
                QMessageBox.information(self, "Success", f"Configuration for '{new_name}' updated.")
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to update file:\n{e}")
        finally:
            self.model_dropdown.blockSignals(False)
            self.clear_dirty_state()
            self.previous_model_index = self.model_dropdown.currentIndex()

    def update_auto_open_visibility(self):
        is_webui_enabled = self.webui_checkbox.isChecked()
        self.open_on_load_checkbox.setVisible(is_webui_enabled)
        if not is_webui_enabled: self.open_on_load_checkbox.setChecked(False)

    def set_status(self, status):
        colors = {'loaded': '#4CAF50', 'unloaded': '#F44336', 'loading': '#FFEB3B', 'error': '#F44336'}
        labels = {'loaded': 'Status: Loaded', 'unloaded': 'Status: Unloaded', 'loading': 'Status: Loading...',
                  'error': 'Status: Error'}
        self.status_label.setText(labels.get(status, 'Status: Unknown'))
        self.status_indicator.setStyleSheet(
            f"background-color: {colors.get(status, '#F44336')}; border-radius: 10px; min-width: 20px; min-height: 20px;")

    def update_button_states(self):
        is_running = self.process is not None and self.process.state() == QProcess.ProcessState.Running
        self.load_button.setEnabled(not is_running and bool(self.llamacpp_dir) and bool(self.models))
        self.unload_button.setEnabled(is_running)

    def browse_llamacpp_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Llama.cpp Directory")
        if directory:
            self.llamacpp_dir = directory;
            self.save_config()
            if not os.path.exists(os.path.join(directory, 'llama-server.exe')):
                QMessageBox.warning(self, "Warning", "llama-server.exe not found.")
        self.update_path_labels();
        self.update_button_states()

    def browse_models_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Models Command File", "", "Text Files (*.txt)")
        if file:
            self.models_file = file;
            self.save_config();
            self.commands_viewer.clear()
            self.parse_models_file()
        self.update_path_labels()

    def parse_models_file(self):
        self.previous_model_index = -1
        if not self.models_file or not os.path.exists(self.models_file):
            self.model_dropdown.clear();
            self.models.clear();
            return
        self.commands_viewer.clear();
        self.help_viewer.clear()
        grouped_models = defaultdict(list)
        current_model_name = ""
        try:
            with open(self.models_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read models file:\n{e}"); return
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('-----'): continue
            if not line.lower().startswith('llama-server.exe'):
                if (i + 1 < len(lines)) and lines[i + 1].strip().lower().startswith('llama-server.exe'):
                    current_model_name = line
            else:
                if current_model_name: grouped_models[current_model_name].append(line)
        self.models.clear()
        for name, commands in grouped_models.items():
            if len(commands) == 1:
                self.models[name] = commands[0]
            else:
                base_name = name.split(' - ')[0].strip()
                for i, cmd in enumerate(commands, 1): self.models[f"{base_name} - Config {i}"] = cmd

        self.model_dropdown.blockSignals(True)
        try:
            self.model_dropdown.clear();
            self.model_dropdown.addItems(sorted(self.models.keys()))
        finally:
            self.model_dropdown.blockSignals(False)

        self.update_button_states()
        self.clear_dirty_state()
        if self.model_dropdown.count() > 0:
            self.model_dropdown.blockSignals(True)
            self.model_dropdown.setCurrentIndex(0)
            self.model_dropdown.blockSignals(False)
            self.model_selected(0)
        else:
            self.model_selected(-1)

    def load_model(self):
        self.set_view(0)
        if not self.llamacpp_dir: QMessageBox.warning(self, "Warning",
                                                      "Please set the Llama.cpp directory first."); return
        command_str = self.reconstruct_command()
        if not command_str: QMessageBox.warning(self, "Warning", "Cannot load model, command is empty."); return
        if not self.webui_checkbox.isChecked():
            if '--no-webui' not in command_str: command_str += ' --no-webui'
        else:
            command_str = re.sub(r'\s+--no-webui\b', '', command_str)
        self.output_viewer.clear()
        self.output_viewer.append(f"Working Directory: {self.llamacpp_dir}\n")
        self.output_viewer.append(f"Executing: {command_str}\n\n" + "=" * 80 + "\n")
        try:
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False, encoding='utf-8')
            self.temp_batch_file = temp_file.name
            temp_file.write(f'@echo off\n{command_str}');
            temp_file.close()
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Could not create temp batch file:\n{e}"); return
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.process_finished)
        self.process.setWorkingDirectory(self.llamacpp_dir)
        self.process.start(self.temp_batch_file)
        self.set_status('loading');
        self.update_button_states()

    def handle_stdout(self):
        try:
            data = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
            self.output_buffer += data
            if not self.output_update_timer.isActive(): self.output_update_timer.start()
        except Exception as e:
            self.output_buffer += f"\n--- Error reading process output: {e} ---\n"

    def flush_output_buffer(self):
        if not self.output_buffer: self.output_update_timer.stop(); return
        text_to_append = self.output_buffer;
        self.output_buffer = ""
        self.output_viewer.append(text_to_append)
        self.output_viewer.verticalScrollBar().setValue(self.output_viewer.verticalScrollBar().maximum())
        success_phrases = ["server is listening on", "server listening at", "http server listening at"]
        if self.status_label.text() == 'Status: Loading...' and any(
                p in text_to_append.lower() for p in success_phrases):
            self.set_status('loaded')
            if self.open_on_load_checkbox.isChecked():
                try:
                    webbrowser.open('http://localhost:8080/'); self.open_on_load_checkbox.setChecked(False)
                except Exception as e:
                    self.output_viewer.append(f"\n--- Could not open web browser: {e} ---")

    def unload_model(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            subprocess.run(f'taskkill /F /T /PID {self.process.processId()}', shell=True, capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            self.process.waitForFinished(3000)

    def process_finished(self):
        self.flush_output_buffer()
        self.output_viewer.append("\n" + "=" * 80 + f"\n--- Process Finished ---")
        self.output_viewer.verticalScrollBar().setValue(self.output_viewer.verticalScrollBar().maximum())
        if self.temp_batch_file and os.path.exists(self.temp_batch_file):
            try:
                os.remove(self.temp_batch_file); self.temp_batch_file = ''
            except OSError as e:
                self.output_viewer.append(f"\n--- Warning: Could not delete temp file: {e} ---")
        self.set_status('error' if 'Loading...' in self.status_label.text() else 'unloaded')
        self.process = None;
        self.update_button_states()

    def save_config(self):
        config = configparser.ConfigParser()
        config['Paths'] = {'LlamaCppDir': self.llamacpp_dir, 'ModelsFile': self.models_file}
        with open(self.config_file, 'w') as cf: config.write(cf)

    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            config.read(self.config_file)
            if 'Paths' in config:
                self.llamacpp_dir = config['Paths'].get('LlamaCppDir', '')
                self.models_file = config['Paths'].get('ModelsFile', '')
        self.update_path_labels()

    def update_path_labels(self):
        error_style = "color: #F44336; font-weight: bold;"
        if not self.llamacpp_dir:
            self.llamacpp_dir_label.setText('Llama.cpp Directory: Not Set'); self.llamacpp_dir_label.setStyleSheet("")
        elif not os.path.isdir(self.llamacpp_dir):
            self.llamacpp_dir_label.setText('Llama.cpp Directory: NOT FOUND'); self.llamacpp_dir_label.setStyleSheet(
                error_style)
        else:
            self.llamacpp_dir_label.setText(
                f'Llama.cpp Directory: {self.llamacpp_dir}'); self.llamacpp_dir_label.setStyleSheet("")
        if not self.models_file:
            self.models_file_label.setText('Models File: Not Set'); self.models_file_label.setStyleSheet("")
        elif not os.path.isfile(self.models_file):
            self.models_file_label.setText('Models File: NOT FOUND'); self.models_file_label.setStyleSheet(error_style)
        else:
            self.models_file_label.setText(f'Models File: {self.models_file}'); self.models_file_label.setStyleSheet("")

    def closeEvent(self, event):
        if self.is_dirty:
            reply = QMessageBox.question(self, 'Unsaved Changes',
                                         "You have unsaved changes. Do you want to save them before exiting?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)

            if reply == QMessageBox.StandardButton.Save:
                self.save_parameters()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        self.unload_model()
        event.accept()

    def browse_for_model_file(self, line_edit_widget):
        file, _ = QFileDialog.getOpenFileName(self, "Select Model File", "", "GGUF Files (*.gguf);;All Files (*)")
        if file:
            line_edit_widget.setText(file)

    def browse_for_mmproj_file(self, line_edit_widget):
        file, _ = QFileDialog.getOpenFileName(self, "Select MMPROJ File", "", "GGUF Files (*.gguf);;All Files (*)")
        if file:
            line_edit_widget.setText(file)

    def duplicate_model(self):
        if self.is_dirty and QMessageBox.question(self, 'Unsaved Changes', "Save unsaved changes first?",
                                                  QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Save:
            self.save_parameters();
            return
        current_name = self.model_dropdown.currentText()
        if not current_name: QMessageBox.warning(self, "Action Failed", "Please select a model to duplicate."); return
        base_name, new_name, count = f"{current_name} (Copy)", f"{current_name} (Copy)", 1
        while new_name in self.models: count += 1; new_name = f"{base_name} {count}"
        self.is_editing_new_model = True
        self.model_dropdown.blockSignals(True);
        self.model_dropdown.setCurrentIndex(-1);
        self.model_dropdown.blockSignals(False)
        self.model_name_input.blockSignals(True)
        try:
            self.model_name_input.setText(new_name)
        finally:
            self.model_name_input.blockSignals(False)
        self.populate_editor_panel();
        self.mark_as_dirty()

    def mark_as_dirty(self):
        if self.is_dirty: return
        self.is_dirty = True
        current_text = self.model_name_input.text()
        if not current_text.endswith(' (*)'):
            self.model_name_input.setText(f"{current_text} (*)")

    def clear_dirty_state(self):
        if not self.is_dirty: return
        self.is_dirty = False
        self.model_name_input.blockSignals(True)
        try:
            self.model_name_input.setText(self.model_name_input.text().replace(' (*)', ''))
        finally:
            self.model_name_input.blockSignals(False)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53));
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25));
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white);
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white);
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white);
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218));
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(dark_palette)
    ex = LlamaCppGUI()
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
    
