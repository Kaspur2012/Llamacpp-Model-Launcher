# Llamacpp_Model_launcher/ui/summary_panel.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
                             QFormLayout, QRadioButton, QCheckBox, QButtonGroup, QSpinBox)
from PyQt6.QtCore import pyqtSignal, Qt
from .styles import PARAMETER_BROWSER_STYLES

# Custom stylesheet for better visual feedback on selections
WIDGET_STYLESHEET = """
QRadioButton, QCheckBox {
    color: #A0A0A0; /* Dimmer color for unselected text */
    background: transparent;
}
QRadioButton:checked, QCheckBox:checked {
    color: #E0E0A0; /* Brighter color for selected text */
    font-weight: bold;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QRadioButton::indicator::unchecked, QCheckBox::indicator::unchecked {
    border: 1px solid #777;
    border-radius: 8px;
    background-color: #3C424C;
}
QRadioButton::indicator::checked, QCheckBox::indicator::checked {
    border: 1px solid #4A85C9;
    border-radius: 8px;
    background-color: #4A85C9; /* Highlight color */
    image: url(Resources/check.png); /* A visual cue like a check or dot */
}
QCheckBox::indicator::checked {
    border-radius: 4px; /* Checkboxes are often square */
}
QRadioButton:disabled, QCheckBox:disabled {
    color: #666; /* Even dimmer for disabled options */
}
"""


class SummaryPanel(QWidget):
    """A redesigned, intelligent panel to display system analysis and get user input for tuning."""
    run_tuning = pyqtSignal(dict)
    tuning_cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(PARAMETER_BROWSER_STYLES["main_bg"])
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(15)

        main_container = QFrame(self)
        main_container.setStyleSheet(PARAMETER_BROWSER_STYLES["group_box"])
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(20, 15, 20, 15)
        container_layout.setSpacing(15)

        title = QLabel("Tuning Assistant")
        title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; padding-bottom: 5px; color: #E0E0E0; background: transparent;")
        container_layout.addWidget(title)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(25)
        summary_column_widget = self._create_summary_column()
        config_column_widget = self._create_config_column()
        columns_layout.addWidget(summary_column_widget, 1)
        columns_layout.addWidget(config_column_widget, 1)
        container_layout.addLayout(columns_layout)
        main_layout.addWidget(main_container)
        main_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(
            "QPushButton { background-color: #555; color: white; border: none; border-radius: 4px; padding: 8px 15px; font-weight: bold; } QPushButton:hover { background-color: #666; }")
        cancel_button.clicked.connect(self.tuning_cancelled.emit)
        run_button = QPushButton("Run Automated Tuning")
        run_button.setStyleSheet(PARAMETER_BROWSER_STYLES["add_button"] + " font-size: 11pt; padding: 8px 15px;")
        run_button.clicked.connect(self._on_run_tuning)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(run_button)
        main_layout.addLayout(button_layout)

    def _create_summary_column(self):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        system_section = self._create_section_widget("System Summary")
        self.system_summary_layout = system_section['layout']
        layout.addWidget(system_section['widget'])
        model_section = self._create_section_widget("Model Summary")
        self.model_summary_layout = model_section['layout']
        layout.addWidget(model_section['widget'])
        layout.addStretch()
        return container

    def _create_section_widget(self, title_text):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        title = QLabel(title_text)
        title.setStyleSheet(
            "font-size: 12pt; font-weight: bold; color: #D1D1D1; margin-bottom: 5px; background: transparent;")
        layout.addWidget(title)
        divider = QFrame();
        divider.setFrameShape(QFrame.Shape.HLine);
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("background-color: #40454E;")
        layout.addWidget(divider)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setContentsMargins(10, 5, 10, 5)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(8)
        layout.addLayout(form_layout)
        return {'widget': widget, 'layout': form_layout}

    def _create_config_column(self):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Tuning Configuration")
        title.setStyleSheet(
            "font-size: 12pt; font-weight: bold; color: #D1D1D1; margin-bottom: 5px; background: transparent;")
        layout.addWidget(title)
        divider = QFrame();
        divider.setFrameShape(QFrame.Shape.HLine);
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("background-color: #40454E;")
        layout.addWidget(divider)

        def create_heading(text, tooltip=""):
            label = QLabel(text)
            label.setStyleSheet("font-weight: bold; color: #C0C0C0; margin-top: 10px; background: transparent;")
            if tooltip:
                label.setToolTip(tooltip)
            return label

        layout.addWidget(create_heading("Primary Goal"))
        self.goal_perf_radio = QRadioButton("Optimize for Maximum Performance (Tokens/Second)")
        self.goal_group = QButtonGroup(self)
        self.goal_group.addButton(self.goal_perf_radio, 1)
        layout.addWidget(self.goal_perf_radio)

        gpu_tooltip = "The Primary GPU handles key calculations. The wizard defaults to the GPU with the most VRAM, but a newer GPU with a faster architecture might be a better choice."
        layout.addWidget(create_heading("Primary GPU Selection", gpu_tooltip))
        self.gpu_selection_layout = QVBoxLayout()
        self.gpu_button_group = QButtonGroup(self)
        layout.addLayout(self.gpu_selection_layout)

        layout.addWidget(create_heading("Offload Strategy"))
        self.offload_single_gpu_radio = QRadioButton("Single GPU Only")
        self.offload_multi_vram_radio = QRadioButton("Multi-GPU (VRAM Only)")
        self.offload_multi_cpu_radio = QRadioButton("Multi-GPU with CPU Offload")
        self.offload_group = QButtonGroup(self)
        self.offload_group.addButton(self.offload_single_gpu_radio, 1)
        self.offload_group.addButton(self.offload_multi_vram_radio, 2)
        self.offload_group.addButton(self.offload_multi_cpu_radio, 3)
        layout.addWidget(self.offload_single_gpu_radio)
        layout.addWidget(self.offload_multi_vram_radio)
        layout.addWidget(self.offload_multi_cpu_radio)

        layout.addWidget(
            create_heading("Core Optimizations", "Toggle recommended base parameters for the tuning process."))
        self.optimizations_layout = QVBoxLayout()
        layout.addLayout(self.optimizations_layout)

        layout.addWidget(create_heading("Additional Optimizations"))
        self.maximize_context_checkbox = QCheckBox("Maximize Context Size After Offload")
        self.maximize_context_checkbox.setToolTip(
            "Finds the largest possible context size (`-c`) that fits in your available memory for the chosen offload strategy.")
        self.maximize_context_checkbox.stateChanged.connect(self._toggle_context_input)
        layout.addWidget(self.maximize_context_checkbox)

        # --- Target Context Input ---
        self.context_input_layout = QHBoxLayout()
        self.context_input_layout.setContentsMargins(20, 0, 0, 0)

        target_label = QLabel("Target Limit:")
        target_label.setStyleSheet("color: #A0A0A0;")

        # New Checkbox for Auto
        self.auto_context_checkbox = QCheckBox("Auto (Max)")
        self.auto_context_checkbox.setChecked(True)
        self.auto_context_checkbox.setStyleSheet(WIDGET_STYLESHEET)
        self.auto_context_checkbox.stateChanged.connect(self._toggle_spinbox_enabled)

        self.target_context_spinbox = QSpinBox()
        self.target_context_spinbox.setRange(512, 1000000)
        self.target_context_spinbox.setSingleStep(1024)
        self.target_context_spinbox.setEnabled(False)  # Default to disabled (Auto is checked)
        self.target_context_spinbox.setStyleSheet("""
            QSpinBox { 
                background-color: #252930; 
                color: #E0E0E0; 
                border: 1px solid #505660; 
                border-radius: 4px; 
                padding: 4px; 
            }
            QSpinBox:disabled {
                color: #505050;
                border-color: #404040;
                background-color: #2e333b;
            }
        """)
        self.target_context_spinbox.setSuffix(" tokens")

        self.context_input_layout.addWidget(target_label)
        self.context_input_layout.addWidget(self.auto_context_checkbox)
        self.context_input_layout.addWidget(self.target_context_spinbox)
        self.context_input_layout.addStretch()

        self.context_input_widget = QWidget()
        self.context_input_widget.setLayout(self.context_input_layout)
        layout.addWidget(self.context_input_widget)
        # -----------------------------

        for widget in [self.goal_perf_radio, self.offload_single_gpu_radio, self.offload_multi_vram_radio,
                       self.offload_multi_cpu_radio, self.maximize_context_checkbox]:
            widget.setStyleSheet(WIDGET_STYLESHEET)

        layout.addStretch()
        return container

    def _toggle_context_input(self, state):
        # Master toggle for the whole context section (checkbox logic)
        # If Maximize is unchecked, we disable the target inputs entirely?
        # Or do we treat it as "Just use this target context"?
        # Current logic suggests the latter is useful.
        # But for now, let's just enable/disable the widget container.
        self.context_input_widget.setEnabled(state == 2)

    def _toggle_spinbox_enabled(self, state):
        # 2 is Checked (Auto), so Spinbox should be Disabled
        self.target_context_spinbox.setDisabled(state == 2)

    def populate(self, data):
        """Fills the summary panel and intelligently configures options based on analysis data."""
        for layout in [self.system_summary_layout, self.model_summary_layout]:
            while layout.rowCount() > 0:
                layout.removeRow(0)

        def add_row(layout, label_text, value_text):
            label = QLabel(f"{label_text}:");
            label.setStyleSheet("font-weight: bold; color: #D1D1D1; font-size: 9pt; background: transparent;")
            value = QLabel(str(value_text));
            value.setStyleSheet("color: #A0A0A0; font-size: 9pt; background: transparent;")
            value.setWordWrap(True)
            layout.addRow(label, value)

        ram = data.get('ram', {});
        add_row(self.system_summary_layout, "System RAM",
                f"{ram.get('total_gb', 'N/A')} GB ({ram.get('free_gb', 'N/A')} GB Free)")
        add_row(self.system_summary_layout, "CPU Cores", f"{data.get('cpu_physical_cores', 'N/A')} Physical")

        gpus = data.get("gpus", [])
        primary_gpu = None
        if gpus:
            while self.gpu_selection_layout.count():
                child = self.gpu_selection_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            recommended_gpu_id = max(gpus, key=lambda gpu: gpu.get('vram', {}).get('total_gb', 0))['id']

            for i, gpu in enumerate(gpus):
                if gpu['id'] == recommended_gpu_id:
                    primary_gpu = gpu
                vram = gpu.get('vram', {})
                vram_str = f"({vram.get('used_gb', 0.0):.1f}/{vram.get('total_gb', 0.0):.1f} GB VRAM)"
                add_row(self.system_summary_layout, f"GPU {gpu['id']}", f"{gpu['name']} {vram_str}")
                is_recommended = gpu['id'] == recommended_gpu_id
                radio_text = f"{gpu['name']} {vram_str}" + (" (Recommended)" if is_recommended else "")
                radio_button = QRadioButton(radio_text)
                radio_button.setProperty("gpu_id", gpu['id'])
                radio_button.setStyleSheet(WIDGET_STYLESHEET)
                if is_recommended:
                    radio_button.setChecked(True)
                self.gpu_button_group.addButton(radio_button)
                self.gpu_selection_layout.addWidget(radio_button)

        if not primary_gpu and gpus:
            primary_gpu = gpus[0]  # Fallback

        add_row(self.model_summary_layout, "Model Architecture", data.get('model_architecture', 'N/A'))
        add_row(self.model_summary_layout, "Model Size", f"{data.get('model_size_gb', 'N/A')} GB")
        add_row(self.model_summary_layout, "Model Layers", data.get('model_layers', 'N/A'))
        add_row(self.model_summary_layout, "Model Max Context", f"{data.get('model_max_context', 'N/A'):,}")

        # Update Spinbox Max to Model Max
        model_max = int(data.get('model_max_context', 32768))
        self.target_context_spinbox.setMaximum(model_max)
        self.target_context_spinbox.setValue(model_max)  # Default if unchecked

        # --- REVISED LOGIC for enabling/disabling and recommending strategies ---
        VRAM_BUFFER_GB = 1.5
        model_size = data.get('model_size_gb', 999)
        num_gpus = len(gpus)

        can_fit_primary_gpu_only = False
        if primary_gpu:
            primary_gpu_free_vram = primary_gpu.get('vram', {}).get('free_gb', 0)
            if (model_size + VRAM_BUFFER_GB) < primary_gpu_free_vram:
                can_fit_primary_gpu_only = True

        can_fit_multi_vram = False
        if num_gpus > 1:
            total_free_vram = sum(g.get('vram', {}).get('free_gb', 0) for g in gpus)
            if (model_size + VRAM_BUFFER_GB) < total_free_vram:
                can_fit_multi_vram = True

        # Reset labels and enable/disable options
        self.offload_single_gpu_radio.setText("Single GPU Only")
        self.offload_multi_vram_radio.setText("Multi-GPU (VRAM Only)")
        if num_gpus <= 1:
            self.offload_multi_cpu_radio.setText("Single GPU with CPU Offload")
        else:
            self.offload_multi_cpu_radio.setText("Multi-GPU with CPU Offload")

        self.offload_single_gpu_radio.setEnabled(can_fit_primary_gpu_only)
        self.offload_multi_vram_radio.setEnabled(can_fit_multi_vram)
        self.offload_multi_cpu_radio.setEnabled(True)  # Always enabled as a fallback

        # Apply recommendations based on the corrected priority
        if can_fit_primary_gpu_only:
            self.offload_single_gpu_radio.setText("Single GPU Only (Recommended)")
            self.offload_single_gpu_radio.setChecked(True)
        elif can_fit_multi_vram:
            self.offload_multi_vram_radio.setText("Multi-GPU (VRAM Only) (Recommended)")
            self.offload_multi_vram_radio.setChecked(True)
        else:
            current_text = self.offload_multi_cpu_radio.text()
            self.offload_multi_cpu_radio.setText(f"{current_text} (Recommended)")
            self.offload_multi_cpu_radio.setChecked(True)

        self.goal_perf_radio.setChecked(True)
        self.maximize_context_checkbox.setChecked(True)

        # Reset Auto Checkbox to Checked
        self.auto_context_checkbox.setChecked(True)

        while self.optimizations_layout.count():
            child = self.optimizations_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        proposed_opts = data.get('proposed_optimizations', [])
        for opt_data in proposed_opts:
            checkbox = QCheckBox(opt_data['label'])
            checkbox.setChecked(opt_data['checked'])
            checkbox.setProperty("param_data", opt_data['params'])
            checkbox.setStyleSheet(WIDGET_STYLESHEET)
            self.optimizations_layout.addWidget(checkbox)

    def _on_run_tuning(self):
        offload_map = {1: 'single_gpu', 2: 'multi_vram', 3: 'multi_cpu'}
        selected_gpu_button = self.gpu_button_group.checkedButton()

        selected_optimizations = {}
        for i in range(self.optimizations_layout.count()):
            checkbox = self.optimizations_layout.itemAt(i).widget()
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                param_data = checkbox.property("param_data")
                if param_data:
                    selected_optimizations.update(param_data)

        # Determine Context Target
        if self.auto_context_checkbox.isChecked():
            target_context = -1
        else:
            target_context = self.target_context_spinbox.value()

        choices = {
            'goal': 'performance',
            'offload_strategy': offload_map.get(self.offload_group.checkedId(), 'single_gpu'),
            'maximize_context': self.maximize_context_checkbox.isChecked(),
            'target_context': target_context,
            'primary_gpu_id': selected_gpu_button.property("gpu_id") if selected_gpu_button else 0,
            'selected_optimizations': selected_optimizations
        }
        self.run_tuning.emit(choices)