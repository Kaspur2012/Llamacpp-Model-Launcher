# ui/main_window.py

import os
import subprocess
import tempfile
import webbrowser
import re
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QSplitter, QFileDialog,
                             QMessageBox, QCheckBox, QComboBox, QLineEdit, QApplication)
from PyQt6.QtCore import QProcess, Qt, QTimer, QObject, QThread, pyqtSignal

from Llamacpp_Model_launcher.core.status import ServerStatus
from Llamacpp_Model_launcher.core.config_manager import ConfigManager
from Llamacpp_Model_launcher.core.model_manager import ModelManager
from Llamacpp_Model_launcher.core.command_builder import CommandBuilder, Parameter

from Llamacpp_Model_launcher.system_analyzer import SystemAnalyzer
from Llamacpp_Model_launcher.tuning_wizard import TuningWizard

# Child UI components are now imported
from left_panel import LeftPanel
from right_panel import RightPanel


# Worker classes remain for now
class ApiRequestWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, wizard_instance):
        super().__init__()
        self.wizard = wizard_instance

    def run(self):
        self.wizard.run_api_benchmark_requests()
        self.finished.emit()


class StabilityRequestWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, wizard_instance):
        super().__init__()
        self.wizard = wizard_instance

    def run(self):
        self.wizard.run_stability_api_request()
        self.finished.emit()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.process = None
        self.config_file = 'config.ini'
        self.llamacpp_dir = ''
        self.models_file = ''
        self.temp_batch_file = ''
        self.is_editing_new_model = False
        self.is_dirty = False
        self.previous_model_index = -1

        self.config_manager = ConfigManager(self.config_file)
        self.model_manager = ModelManager(self.models_file)
        self.command_builder = CommandBuilder()

        # Wizard and process-related attributes remain here for now
        self.wizard_confirm_each_step = False
        self.analysis_results = None
        # ... (all other wizard and regex attributes are unchanged)
        self.wizard_generator = None
        self.wizard_timer = QTimer(self)
        self.wizard_is_benchmarking = False
        self.output_buffer = ""
        self.output_update_timer = QTimer(self)
        self.tps_regex = re.compile(
            r"^\s*eval time\s*=\s*[\d.]+\s*ms\s*/\s*\d+\s*tokens\s*\([\s\d.]+\s*ms per token,\s*([\d.]+)\s*tokens per second\)",
            re.MULTILINE
        )
        self.idle_regex = re.compile(r"all slots are idle", re.IGNORECASE)
        self.layer_count_regex = re.compile(r"n_layer\s*=\s*(\d+)", re.IGNORECASE)
        self.cuda_oom_regex_alloc = re.compile(
            r"allocating\s+([\d.]+)\s+MiB\s+on\s+device\s+(\d+):\s+cudaMalloc\s+failed:\s+out\s+of\s+memory",
            re.IGNORECASE
        )
        self.cuda_oom_regex_generic = re.compile(r"CUDA error: out of memory\s+current device: (\d+)", re.IGNORECASE)
        self.cuda_oom_regex_resource = re.compile(
            r"CUDA error:\s+the\s+resource\s+allocation\s+failed\s+current\s+device:\s+(\d+)",
            re.IGNORECASE
        )
        self.cuda_device_regex = re.compile(r"Device\s+(\d+):\s+([^,]+),", re.IGNORECASE)
        self.soft_failure_regex = re.compile(r"eval time\s*=\s*0\.00\s*ms\s*/\s*1\s*tokens", re.IGNORECASE)
        self.wizard_found_layers = None
        self.wizard_error_details = None
        self.wizard_found_gpus = []
        self.wizard_tps_results = []
        self.benchmark_timeout_timer = None
        self.wizard = None
        self.wizard_current_is_viability_check = False
        self.wizard_awaiting_idle_signal = False
        self.wizard_idle_signal_received = False
        self.wizard_saw_soft_failure_artifact = False
        self.best_params_snapshot = ""

        self._init_ui()
        self._connect_signals()

        # Initial load
        self.load_config()
        self.populate_model_dropdown()

    def _init_ui(self):
        self.setWindowTitle('Llama.cpp Model Launcher')
        self.setGeometry(100, 100, 1450, 900)
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Instantiate the panels
        self.left_panel = LeftPanel()
        self.right_panel = RightPanel()

        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([1050, 400])

        self.wizard_timer.timeout.connect(self._process_next_wizard_step)
        self.output_update_timer.setInterval(100)
        self.output_update_timer.timeout.connect(self.flush_output_buffer)

    def _connect_signals(self):
        # Left Panel Signals
        self.left_panel.dir_browse_clicked.connect(self.browse_llamacpp_directory)
        self.left_panel.file_browse_clicked.connect(self.browse_models_file)
        self.left_panel.model_selected.connect(self.model_selected)
        self.left_panel.load_model_clicked.connect(self.load_model)
        self.left_panel.unload_model_clicked.connect(self.unload_model)
        self.left_panel.tune_model_clicked.connect(self.start_tuning_wizard)
        self.left_panel.exit_clicked.connect(self.close)
        self.left_panel.webui_toggled.connect(self.update_auto_open_visibility)
        self.left_panel.parameter_browser.parameter_add_requested.connect(self.add_parameter_from_browser)

        # Right Panel Signals
        self.right_panel.save_clicked.connect(self.save_parameters)
        self.right_panel.delete_clicked.connect(self.delete_model)
        self.right_panel.add_new_clicked.connect(self.add_new_model)
        self.right_panel.duplicate_clicked.connect(self.duplicate_model)
        self.right_panel.reset_clicked.connect(self._reset_current_model)
        self.right_panel.dirty_state_changed.connect(lambda is_dirty: setattr(self, 'is_dirty', is_dirty))

    # --- Core Logic Methods (previously in LlamaCppGUI) ---

    def _reload_editor_for_model(self, index):
        if index == -1:
            self.right_panel.populate([], "")
            return

        self.is_editing_new_model = False
        current_name = self.left_panel.model_dropdown.itemText(index)
        if not current_name:
            self.right_panel.populate([], "")
            return

        command_str = self.model_manager.models.get(current_name, "")
        command_parts = self.command_builder.parse(command_str)
        self.right_panel.populate(command_parts, current_name)

    def model_selected(self, index):
        self.analysis_results = None
        if index == -1 or index == self.previous_model_index: return

        if self.is_dirty:
            reply = QMessageBox.question(self, 'Unsaved Changes', "Save unsaved changes before switching?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                self.save_parameters()
                return
            elif reply == QMessageBox.StandardButton.Cancel:
                self.left_panel.set_dropdown_index(self.previous_model_index)
                return

        self._reload_editor_for_model(index)
        self.previous_model_index = index

    def _reset_current_model(self):
        """Handler for the reset button click."""
        self._reload_editor_for_model(self.left_panel.model_dropdown.currentIndex())

    def add_parameter_from_browser(self, param_data, input_widget):
        value = None
        if isinstance(input_widget, QCheckBox):
            if not input_widget.isChecked(): return
            value = None
        elif isinstance(input_widget, QComboBox):
            value = input_widget.currentText()
        elif isinstance(input_widget, QLineEdit):
            value = input_widget.text().strip()

        self.right_panel.add_parameter_row(param_data['prefix'], value)

    def add_new_model(self):
        if self.is_dirty and QMessageBox.question(self, 'Unsaved Changes', "Save unsaved changes first?",
                                                  QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Save:
            self.save_parameters()
            return

        self.is_editing_new_model = True
        base_name, new_name, count = "New Model", "New Model", 1
        while new_name in self.model_manager.models:
            count += 1
            new_name = f"{base_name} {count}"

        default_params = [
            Parameter('Executable', 'llama-server.exe'), Parameter('-m', 'D:\\path_to_your_model.gguf'),
            Parameter('-c', '4096'), Parameter('--jinja', None), Parameter('--temp', '0.7'),
            Parameter('--top-k', '40'), Parameter('--top-p', '0.95'), Parameter('--min-p', '0.05'),
        ]

        self.left_panel.set_dropdown_index(-1)
        self.right_panel.populate(default_params, new_name)
        QMessageBox.information(self, "Pro Tip",
                                "For best output quality, find recommended sampling parameters from the model's creator.")

    def delete_model(self):
        model_to_delete = self.left_panel.model_dropdown.currentText()
        if not model_to_delete:
            QMessageBox.warning(self, "Warning", "No model selected.")
            return

        reply = QMessageBox.question(self, 'Confirm Deletion', f"Permanently delete '{model_to_delete}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.model_manager.delete_model(model_to_delete)
            if success:
                QMessageBox.information(self, "Success", message)
                self.populate_model_dropdown()
            else:
                QMessageBox.critical(self, "File Error", message)

    def save_parameters(self):
        new_name = self.right_panel.get_model_name()
        if not new_name:
            QMessageBox.warning(self, "Input Error", "Model name cannot be empty.")
            return

        params_from_editor = self.right_panel.get_parameters()
        new_command = self.command_builder.build(params_from_editor)

        old_name = ""
        if not self.is_editing_new_model and self.previous_model_index != -1:
            old_name = self.left_panel.model_dropdown.itemText(self.previous_model_index)

        success, message = self.model_manager.save_model(old_name, new_name, new_command, self.is_editing_new_model)

        if success:
            QMessageBox.information(self, "Success", message)
            self.is_editing_new_model = False

            self.right_panel.clear_dirty_state()

            current_selection = self.populate_model_dropdown()
            if new_name in current_selection:
                self.left_panel.model_dropdown.setCurrentText(new_name)
            self.previous_model_index = self.left_panel.model_dropdown.currentIndex()
        else:
            QMessageBox.critical(self, "Error", message)

    def duplicate_model(self):
        if self.is_dirty and QMessageBox.question(self, 'Unsaved Changes', "Save changes first?",
                                                  QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Save:
            self.save_parameters()
            return

        current_name = self.left_panel.model_dropdown.currentText()
        if not current_name:
            QMessageBox.warning(self, "Action Failed", "Please select a model to duplicate.")
            return

        base_name, new_name, count = f"{current_name} (Copy)", f"{current_name} (Copy)", 1
        while new_name in self.model_manager.models:
            count += 1
            new_name = f"{base_name} {count}"

        self.is_editing_new_model = True
        self.left_panel.set_dropdown_index(-1)
        current_params = self.right_panel.get_parameters()
        self.right_panel.populate(current_params, new_name)

    def update_auto_open_visibility(self):
        is_webui_enabled = self.left_panel.webui_checkbox.isChecked()
        self.left_panel.open_on_load_checkbox.setVisible(is_webui_enabled)
        if not is_webui_enabled:
            self.left_panel.open_on_load_checkbox.setChecked(False)

    def update_button_states(self):
        is_running = self.process is not None and self.process.state() == QProcess.ProcessState.Running
        can_load = not is_running and bool(self.llamacpp_dir) and bool(self.model_manager.models)
        self.left_panel.update_button_states(can_load, is_running)

    def browse_llamacpp_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Llama.cpp Directory")
        if directory:
            self.llamacpp_dir = directory
            self.config_manager.save_config(self.llamacpp_dir, self.models_file)
            self.update_path_labels()
            self.update_button_states()

    def browse_models_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Models Command File", "", "Text Files (*.txt)")
        if file:
            self.models_file = file
            self.config_manager.save_config(self.llamacpp_dir, self.models_file)
            self.model_manager.set_models_file(file)
            self.populate_model_dropdown()
            self.update_path_labels()

    def populate_model_dropdown(self):
        self.previous_model_index = -1
        models = self.model_manager.load_models()
        model_names = list(models.keys())
        self.left_panel.populate_dropdown(model_names)
        self.update_button_states()

        if self.left_panel.model_dropdown.count() > 0:
            self.left_panel.set_dropdown_index(0)
            self.model_selected(0)
        else:
            self.model_selected(-1)
        return model_names

    def load_config(self):
        self.llamacpp_dir, self.models_file = self.config_manager.load_config()
        self.model_manager.set_models_file(self.models_file)
        self.update_path_labels()

    def update_path_labels(self):
        dir_valid = os.path.isdir(self.llamacpp_dir)
        models_valid = os.path.isfile(self.models_file)
        self.left_panel.update_path_labels(self.llamacpp_dir, self.models_file, dir_valid, models_valid)

    def closeEvent(self, event):
        if self.is_dirty:
            reply = QMessageBox.question(self, 'Unsaved Changes', "Save unsaved changes before exiting?",
                                         QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Save:
                self.save_parameters()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        self.unload_model()
        event.accept()

    def get_server_address_from_command(self):
        host, port = 'localhost', '8080'
        params_from_editor = self.right_panel.get_parameters()
        params_dict = {p.key: p.value for p in params_from_editor}
        host = params_dict.get('--host', '127.0.0.1')
        if host == '127.0.0.1': host = 'localhost'
        port = params_dict.get('--port', '8080')
        return host, port

    # --- Process Management & Wizard Logic remains below (unchanged for Phase 4) ---
    # ... (load_model, unload_model, handle_stdout, flush_output_buffer, process_finished, start_tuning_wizard, etc.)
    def load_model(self):
        self.left_panel.show_output_view()
        if not self.llamacpp_dir: QMessageBox.warning(self, "Warning", "Set the Llama.cpp directory first."); return

        params_from_editor = self.right_panel.get_parameters()
        command_str = self.command_builder.build(params_from_editor)
        if not command_str: QMessageBox.warning(self, "Warning", "Command is empty."); return

        log_msg = f"Working Dir: {self.llamacpp_dir}\nExecuting Command: {command_str}\n\n" + "=" * 80 + "\n"
        self.left_panel.clear_output()
        self.left_panel.append_output(log_msg)
        print(f"\n[DIAGNOSTICS] LAUNCHING SERVER\n[DIAGNOSTICS] > {command_str}\n")

        if not self.left_panel.webui_checkbox.isChecked() and '--no-webui' not in command_str:
            command_str += ' --no-webui'
        else:
            command_str = re.sub(r'\s+--no-webui\b', '', command_str)

        try:
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False, encoding='utf-8')
            self.temp_batch_file = temp_file.name
            temp_file.write(f'@echo off\n{command_str}')
            temp_file.close()
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Could not create temp batch file:\n{e}");
            return

        self.process = QProcess();
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_stdout);
        self.process.finished.connect(self.process_finished)
        self.process.setWorkingDirectory(self.llamacpp_dir);
        self.process.start(self.temp_batch_file)
        self.left_panel.set_status(ServerStatus.LOADING);
        self.update_button_states()

    def handle_stdout(self):
        try:
            data = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore');
            self.output_buffer += data
            if not self.output_update_timer.isActive(): self.output_update_timer.start()

            if self.wizard_is_benchmarking and self.wizard_current_is_viability_check == "layer_extraction":
                layer_match = self.layer_count_regex.search(self.output_buffer)
                if layer_match:
                    try:
                        layer_count = int(layer_match.group(1))
                        if self.wizard_found_layers is None:
                            self.wizard_found_layers = layer_count
                            print(f"[DIAGNOSTICS] Found layer count: {layer_count}.")
                            self.left_panel.append_output(f"[WIZARD] Found n_layer = {layer_count}")
                    except (ValueError, IndexError):
                        pass

                gpu_matches = self.cuda_device_regex.finditer(self.output_buffer)
                for match in gpu_matches:
                    try:
                        gpu_id = int(match.group(1))
                        gpu_name = match.group(2).strip()
                        if not any(g['id'] == gpu_id for g in self.wizard_found_gpus):
                            self.wizard_found_gpus.append({'id': gpu_id, 'name': gpu_name})
                            print(f"[DIAGNOSTICS] Found GPU Device {gpu_id}: {gpu_name}")
                    except (ValueError, IndexError):
                        pass

                if self.wizard_found_layers is not None and len(self.wizard_found_gpus) > 0:
                    self.unload_model()

            if self.wizard_is_benchmarking and self.wizard_current_is_viability_check:
                oom_match_alloc = self.cuda_oom_regex_alloc.search(self.output_buffer)
                oom_match_generic = self.cuda_oom_regex_generic.search(self.output_buffer)
                oom_match_resource = self.cuda_oom_regex_resource.search(self.output_buffer)
                oom_match = oom_match_alloc or oom_match_generic or oom_match_resource

                if oom_match:
                    size_mib, device_id = 0.0, -1
                    if oom_match == oom_match_alloc:
                        size_mib = float(oom_match.group(1))
                        device_id = int(oom_match.group(2))
                    else:
                        size_mib = 0.0
                        device_id = int(oom_match.group(1))

                    self.wizard_error_details = {
                        'type': 'oom',
                        'size_mib': size_mib,
                        'device_id': device_id
                    }
                    print(f"[DIAGNOSTICS] Captured OOM error: {self.wizard_error_details}")

        except Exception as e:
            self.output_buffer += f"\n--- Error reading output: {e} ---\n"

    def flush_output_buffer(self):
        if not self.output_buffer: self.output_update_timer.stop(); return
        text_to_append = self.output_buffer;
        self.output_buffer = ""
        self.left_panel.append_output(text_to_append)

        if self.wizard_is_benchmarking and self.wizard_current_is_viability_check == "ngl_testing":
            if self.soft_failure_regex.search(text_to_append):
                print("[DIAGNOSTICS] Soft failure artifact detected. Flagging for failure.")
                self.left_panel.append_output("[WIZARD] **Detected unstable server signature (soft failure).**")
                self.wizard_saw_soft_failure_artifact = True

        if self.wizard_is_benchmarking and not self.wizard_current_is_viability_check and len(
                self.wizard_tps_results) < 3:
            matches = self.tps_regex.findall(text_to_append)
            for match in matches:
                try:
                    tps_value = float(match)
                    if tps_value > 5000:
                        print(f"[DIAGNOSTICS] Discarding unrealistic TPS value: {tps_value}")
                        continue

                    self.wizard_tps_results.append(tps_value)
                    log_msg = f"[WIZARD] Found TPS value: {tps_value:.2f}. ({len(self.wizard_tps_results)}/3)"
                    self.left_panel.append_output(log_msg)
                    print(f"[DIAGNOSTICS] Regex matched: {tps_value:.2f} t/s.")

                    if len(self.wizard_tps_results) >= 3:
                        if self.benchmark_timeout_timer and self.benchmark_timeout_timer.isActive():
                            self.benchmark_timeout_timer.stop()
                        self.left_panel.append_output("[WIZARD] Collected 3 TPS values. Finalizing benchmark.")
                        print("[DIAGNOSTICS] Collected 3/3 TPS values. Calculating average.")
                        avg_tps = sum(self.wizard_tps_results) / len(self.wizard_tps_results)
                        result = {'success': True, 'avg_tps': avg_tps, 'error': ''}

                        current_params_list = [p._asdict() for p in self.right_panel.get_parameters()]
                        result['params_used'] = dict(current_params_list)

                        self._handle_benchmark_result(result)
                        break
                except (ValueError, IndexError):
                    pass

        if self.wizard_awaiting_idle_signal and self.idle_regex.search(text_to_append):
            print("[DIAGNOSTICS] 'all slots are idle' signal detected. Asking for user confirmation.")
            self.wizard_awaiting_idle_signal = False
            self._ask_for_stability_confirmation()

        is_loading = "Loading..." in self.left_panel.status_label.text()
        if is_loading and "model loaded" in text_to_append.lower():
            self.left_panel.set_status(ServerStatus.LOADED)
            log_msg = "\n[INFO] Model is fully loaded."
            self.left_panel.append_output(log_msg)
            print(f"[DIAGNOSTICS] Detected 'model loaded' string.")

            if self.wizard_is_benchmarking and self.wizard_current_is_viability_check == "ngl_testing":
                self._run_inference_stability_test()

            elif self.wizard_is_benchmarking:
                print("[DIAGNOSTICS] Calling _continue_wizard_benchmark().")
                self._continue_wizard_benchmark()
            elif self.left_panel.open_on_load_checkbox.isChecked():
                try:
                    host, port = self.get_server_address_from_command()
                    url_to_open = f'http://{host}:{port}/'
                    webbrowser.open(url_to_open);
                    self.left_panel.open_on_load_checkbox.setChecked(False)
                except Exception as e:
                    self.left_panel.append_output(f"\n--- Could not open web browser: {e} ---")

    def _ask_for_stability_confirmation(self):
        self.wizard_timer.stop()

        user_confirmed = False
        if self.wizard_confirm_each_step:
            reply = QMessageBox.question(self, 'Stability Test Passed',
                                         "The current configuration appears stable.\n\n"
                                         "Do you want to accept this result and continue tuning?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                user_confirmed = True
        else:
            print("[DIAGNOSTICS] Auto-confirming stability test.")
            user_confirmed = True

        if user_confirmed:
            print("[DIAGNOSTICS] User confirmed stability test. Proceeding to unload.")
            self.wizard_idle_signal_received = True
            self.unload_model()
        else:
            print("[DIAGNOSTICS] User rejected stability test. Aborting wizard.")
            self.left_panel.append_output("[WIZARD] Tuning aborted by user.")
            self.unload_model()
            self._finish_tuning_wizard()

    def _run_inference_stability_test(self):
        if self.wizard_awaiting_idle_signal: return

        self.left_panel.append_output("[WIZARD] Model loaded. Performing inference stability test...")
        print("[DIAGNOSTICS] Starting StabilityRequestWorker thread.")

        self.wizard_awaiting_idle_signal = True
        self.stability_thread = QThread()
        self.stability_worker = StabilityRequestWorker(self.wizard)
        self.stability_worker.moveToThread(self.stability_thread)
        self.stability_thread.started.connect(self.stability_worker.run)
        self.stability_worker.finished.connect(self.stability_thread.quit)
        self.stability_worker.finished.connect(self.stability_worker.deleteLater)
        self.stability_thread.finished.connect(self.stability_thread.deleteLater)
        self.stability_thread.start()

    def unload_model(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            print("[DIAGNOSTICS] Unloading model via taskkill.")
            subprocess.run(f'taskkill /F /T /PID {self.process.processId()}', shell=True, capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)

    def process_finished(self):
        self.handle_stdout()
        self.flush_output_buffer()

        original_status_label = self.left_panel.status_label.text()
        log_msg = "\n" + "=" * 80 + f"\n--- Process Finished ---"
        self.left_panel.append_output(log_msg)
        print(f"[DIAGNOSTICS] QProcess finished signal received. Original status: {original_status_label}")
        if self.temp_batch_file and os.path.exists(self.temp_batch_file):
            try:
                os.remove(self.temp_batch_file);
                self.temp_batch_file = ''
            except OSError:
                pass

        is_error = 'Loading...' in original_status_label
        self.left_panel.set_status(ServerStatus.ERROR if is_error else ServerStatus.UNLOADED)
        self.process = None;
        self.update_button_states()

        if self.wizard_is_benchmarking:
            if self.benchmark_timeout_timer and self.benchmark_timeout_timer.isActive():
                self.benchmark_timeout_timer.stop()

            if self.wizard_current_is_viability_check:
                if self.wizard_current_is_viability_check == "layer_extraction":
                    result = {
                        'success': self.wizard_found_layers is not None,
                        'layers': self.wizard_found_layers,
                        'gpus': self.wizard_found_gpus,
                        'error': '' if self.wizard_found_layers is not None else 'Could not find n_layer'
                    }
                    print(f"[DIAGNOSTICS] Layer extraction finished. Result: {result}")
                    self.wizard_generator.send(result)
                    self.wizard_timer.start(100)

                elif self.wizard_current_is_viability_check == "ngl_testing":
                    was_successful = self.wizard_idle_signal_received and (not is_error) and (
                        not self.wizard_saw_soft_failure_artifact)

                    if was_successful:
                        print("[DIAGNOSTICS] Viability test PASSED: Idle signal received, no crash, no soft failure.")
                        self.left_panel.append_output("[WIZARD] Inference stability test PASSED.")
                    else:
                        print(
                            f"[DIAGNOSTICS] Viability test FAILED: Idle received: {self.wizard_idle_signal_received}, "
                            f"Server crashed: {is_error}, Soft Failure: {self.wizard_saw_soft_failure_artifact}")
                        self.left_panel.append_output("[WIZARD] Inference stability test FAILED.")

                    self.wizard_awaiting_idle_signal = False
                    self.wizard_idle_signal_received = False
                    self.wizard_saw_soft_failure_artifact = False

                    result = {'success': was_successful, 'error_details': self.wizard_error_details}
                    self.wizard_generator.send(result)
                    self.wizard_timer.start(100)

            elif is_error:
                self.wizard_is_benchmarking = False
                result = {'success': False, 'error': 'Server crashed during load'}

                current_params_list = [p._asdict() for p in self.right_panel.get_parameters()]
                result['params_used'] = dict(current_params_list)

                log_msg = f"[WIZARD CRITICAL] Server crashed during load. Aborting this step."
                self.left_panel.append_output(log_msg)
                print(f"[DIAGNOSTICS] Server crashed. Sending failure result to wizard generator.")
                self.wizard_generator.send(result)
                self.wizard_timer.start(100)

    def start_tuning_wizard(self):
        self.left_panel.show_output_view()
        self.left_panel.clear_output()
        self.left_panel.append_output("=" * 30 + " Starting System Analysis " + "=" * 30)
        self.analysis_results = None

        current_params = {p.key: p.value for p in self.right_panel.get_parameters()}
        model_path = current_params.get('-m', current_params.get('--model'))

        if "Executable" not in current_params or not model_path:
            QMessageBox.critical(self, "Prerequisite Missing",
                                 "Tuning requires the 'Executable' and a model path ('-m') to be set in the editor.")
            return

        if "--jinja" not in current_params:
            self.left_panel.append_output("[INFO] --jinja flag not found. It will be added for the tuning process.")
            self.right_panel.add_parameter_row("--jinja", None)

        QApplication.processEvents()

        analyzer = SystemAnalyzer()
        analysis_generator = analyzer.run_analysis(model_path)
        final_results = {}
        try:
            while True:
                self.left_panel.append_output(next(analysis_generator))
                QApplication.processEvents()
        except StopIteration as e:
            final_results = e.value

        if not final_results:
            self.left_panel.append_output("\n[CRITICAL] System analysis failed. Cannot proceed with tuning.")
            return

        self.analysis_results = final_results
        summary = "\n" + "-" * 25 + " System & Model Summary " + "-" * 25
        summary += f"\nCPU Cores: {final_results.get('cpu_physical_cores', 'N/A')}"
        # ... (rest of summary generation is the same)
        ram_info = final_results.get('ram', {})
        if ram_info:
            summary += f"\nTotal RAM:   {ram_info.get('used_gb', 'N/A')}/{ram_info.get('total_gb', 'N/A')} GB ({ram_info.get('free_gb', 'N/A')} GB Free)"
        else:
            summary += f"\nTotal RAM:   N/A"

        if final_results.get("gpus"):
            for gpu in final_results["gpus"]:
                vram_info = gpu.get('vram', {})
                if vram_info:
                    summary += f"\nGPU {gpu['id']}: {gpu['name']} ({vram_info.get('used_gb', 'N/A')}/{vram_info.get('total_gb', 'N/A')} GB VRAM ({vram_info.get('free_gb', 'N/A')} GB Free))"
                else:
                    summary += f"\nGPU {gpu['id']}: {gpu['name']} (VRAM info not available)"
        else:
            summary += "\nGPUs: No compatible GPUs detected"

        summary += f"\nModel Size: {final_results.get('model_size_gb', 'N/A')} GB"
        summary += f"\nModel Arch: {final_results.get('model_architecture', 'N/A')}"
        summary += "\n" + "-" * 72
        self.left_panel.append_output(summary)
        QApplication.processEvents()

        self.left_panel.tuning_wizard_button.setEnabled(False)
        self.left_panel.load_button.setEnabled(False)

        if self.analysis_results.get('model_architecture') == 'Dense':
            current_params_dict = {p.key: p.value for p in self.right_panel.get_parameters()}
            if '-md' not in current_params_dict and '--model-draft' not in current_params_dict:
                if QMessageBox.question(self, "Speculative Decoding", "Do you have a compatible draft model?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                    draft_file, _ = QFileDialog.getOpenFileName(self, "Select Draft Model File", "",
                                                                "GGUF Files (*.gguf)")
                    if draft_file:
                        self._update_editor_params({'-md': draft_file})

        final_params_list = self.right_panel.get_parameters()
        final_params_dict = {p.key: p.value for p in final_params_list}

        self.wizard = TuningWizard(self.analysis_results, final_params_dict)
        self.wizard_generator = self.wizard.run_tuning_wizard()
        self.wizard_timer.start(100)

    def _process_next_wizard_step(self):
        try:
            if self.wizard_generator is None:
                self.wizard_timer.stop()
                return

            action = next(self.wizard_generator)
            print(f"[DIAGNOSTICS] Wizard action received: {action}")

            if action.get('action') == 'log':
                self.left_panel.append_output(f"[WIZARD] {action['message']}")
                self.wizard_timer.start(100)
            elif action.get('action') == 'update_params':
                self.left_panel.append_output(f"[WIZARD] Applying new parameters: {action['params']}")
                self._update_editor_params(action['params'])
                self.wizard_timer.start(100)
            elif action.get('action') == 'save_best_params':
                self.left_panel.append_output(f"[WIZARD] Saving current configuration as the best so far.")
                current_params = self.right_panel.get_parameters()
                self.best_params_snapshot = self.command_builder.build(current_params)
                self.wizard_timer.start(100)
            elif action.get('action') == 'restore_best_params':
                self.left_panel.append_output(f"[WIZARD] Restoring the best known configuration.")
                self._restore_params_from_snapshot()
                self.wizard_timer.start(100)
            # ... (rest of wizard step processing is the same)
            elif action.get('action') == 'confirm_warning':
                self.wizard_timer.stop()
                reply = QMessageBox.question(self, action['title'], action['message'],
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)
                user_proceeded = (reply == QMessageBox.StandardButton.Yes)
                try:
                    self.wizard_generator.send(user_proceeded)
                except StopIteration:
                    self._finish_tuning_wizard()
                    return
                self.wizard_timer.start(100)
            elif action.get('action') == 'confirm_context_tradeoff':
                self.wizard_timer.stop()
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setWindowTitle(action['title'])
                msg_box.setText(action['message'])
                multi_gpu_button = msg_box.addButton("Use Multiple GPUs", QMessageBox.ButtonRole.YesRole)
                msg_box.addButton("Abort & Adjust Manually", QMessageBox.ButtonRole.NoRole)
                msg_box.exec()

                user_proceeded = (msg_box.clickedButton() == multi_gpu_button)

                if not user_proceeded:
                    self.left_panel.append_output("[WIZARD] User chose to abort and adjust context size manually.")

                try:
                    self.wizard_generator.send(user_proceeded)
                except StopIteration:
                    self._finish_tuning_wizard()
                    return
                self.wizard_timer.start(100)
            elif action.get('action') == 'extract_layer_count':
                self.wizard_timer.stop()
                self.wizard_is_benchmarking = True
                self.wizard_current_is_viability_check = "layer_extraction"
                self.wizard_found_layers = None
                self.wizard_found_gpus = []
                self.load_model()
                self._setup_benchmark_timer()
                self.benchmark_timeout_timer.start(30000)
            elif action.get('action') == 'test_ngl_value':
                self.wizard_timer.stop()
                self.wizard_is_benchmarking = True
                self.wizard_current_is_viability_check = "ngl_testing"
                self.wizard_error_details = None
                self.wizard_awaiting_idle_signal = False
                self.wizard_idle_signal_received = False
                self.wizard_saw_soft_failure_artifact = False
                self.load_model()
                self._setup_benchmark_timer()
                self.benchmark_timeout_timer.start(120000)
            elif action.get('action') == 'confirm_benchmark':
                self.wizard_timer.stop()
                user_proceeded = False
                if self.wizard_confirm_each_step:
                    params = self.right_panel.get_parameters()
                    command_to_run = self.command_builder.build(params)
                    reply = QMessageBox.question(self, 'Confirm Benchmark',
                                                 f"The wizard proposes the following parameters for the next test. Do you want to proceed?\n\nCommand:\n{command_to_run}",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                 QMessageBox.StandardButton.Yes)
                    if reply == QMessageBox.StandardButton.Yes: user_proceeded = True
                else:
                    user_proceeded = True

                if not user_proceeded:
                    self.left_panel.append_output("[WIZARD] Tuning aborted by user.")
                    self._finish_tuning_wizard()
                    return
                try:
                    next_action = self.wizard_generator.send(True)
                    if next_action.get('action') == 'load_and_benchmark':
                        self.wizard_current_is_viability_check = False
                        self.wizard_is_benchmarking = True
                        self.load_model()
                    else:
                        self.wizard_timer.start(100)
                except StopIteration:
                    self._finish_tuning_wizard()
            elif action.get('action') == 'load_and_benchmark':
                self.wizard_current_is_viability_check = False
                self.wizard_is_benchmarking = True
                self.wizard_timer.stop()
                self.load_model()
            QApplication.processEvents()
        except StopIteration:
            self._finish_tuning_wizard()

    def _setup_benchmark_timer(self):
        if self.benchmark_timeout_timer is None:
            self.benchmark_timeout_timer = QTimer(self)
            self.benchmark_timeout_timer.setSingleShot(True)
            self.benchmark_timeout_timer.timeout.connect(self._check_benchmark_timeout)

    def _continue_wizard_benchmark(self):
        self.wizard_timer.stop()
        self.left_panel.append_output("[WIZARD] Triggering 3 API requests for benchmarking...")
        print("[DIAGNOSTICS] Starting ApiRequestWorker thread.")
        self.wizard_tps_results.clear()
        self.thread = QThread()
        self.worker = ApiRequestWorker(self.wizard)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self._setup_benchmark_timer()
        self.benchmark_timeout_timer.start(300000)

    def _check_benchmark_timeout(self):
        if self.wizard_is_benchmarking:
            self.benchmark_timeout_timer.stop()
            if self.wizard_current_is_viability_check == "layer_extraction":
                log_msg = "[WIZARD ERROR] Timed out waiting for model metadata."
                self.unload_model()
            elif self.wizard_current_is_viability_check == "ngl_testing":
                log_msg = "[WIZARD INFO] NGL test timed out, assuming load failure."
                self.unload_model()
            elif len(self.wizard_tps_results) < 3:
                log_msg = "[WIZARD ERROR] Benchmark timed out."
                self._handle_benchmark_result({'success': False, 'error': 'Benchmark timed out'})
            self.left_panel.append_output(log_msg)

    def _handle_benchmark_result(self, result):
        if self.benchmark_timeout_timer and self.benchmark_timeout_timer.isActive():
            self.benchmark_timeout_timer.stop()

        log_msg = f"[WIZARD] Benchmark step finished. Average TPS: {result.get('avg_tps', 0.0):.2f}"
        self.left_panel.append_output(log_msg)
        self.unload_model()
        unload_timer = QTimer(self)

        def on_unload_complete():
            self.wizard_is_benchmarking = False
            try:
                if self.wizard_generator:
                    self.wizard_generator.send(result)
                    self.wizard_timer.start(100)
            except StopIteration:
                self._finish_tuning_wizard()
            unload_timer.stop()

        unload_timer.timeout.connect(lambda: None if self.process is not None else on_unload_complete())
        unload_timer.start(250)

    def _finish_tuning_wizard(self):
        print("[DIAGNOSTICS] Wizard generator finished. Cleaning up.")
        self.wizard_timer.stop()
        self.wizard_generator = None
        self.wizard_is_benchmarking = False
        self.update_button_states()
        if self.best_params_snapshot:
            if QMessageBox.question(self, "Tuning Complete", "Keep the optimal parameters found by the wizard?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.Yes) == QMessageBox.StandardButton.Yes:
                self._restore_params_from_snapshot()
                # --- FIX: Re-apply the dirty state after the wizard restores the parameters ---
                self.right_panel._mark_as_dirty()

    def _update_editor_params(self, params_to_update):
        current_params_list = self.right_panel.get_parameters()
        params_dict = {p.key: p.value for p in current_params_list}

        for param, value in params_to_update.items():
            if value == 'REMOVE':
                if param in params_dict: del params_dict[param]
            else:
                params_dict[param] = value

        updated_params_list = [Parameter(k, v) for k, v in params_dict.items()]
        # Repopulate the editor without changing the model name
        self.right_panel.populate(updated_params_list, self.right_panel.get_model_name())
        QApplication.processEvents()

    def _restore_params_from_snapshot(self):
        if not self.best_params_snapshot: return
        command_parts = self.command_builder.parse(self.best_params_snapshot)
        self.right_panel.populate(command_parts, self.right_panel.get_model_name())