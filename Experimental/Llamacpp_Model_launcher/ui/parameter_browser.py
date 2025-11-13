# ui/parameter_browser.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QScrollArea, QFrame,
                             QPushButton, QHBoxLayout, QLabel, QCheckBox, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from Llamacpp_Model_launcher.parameters_db import LLAMA_CPP_PARAMETERS
from styles import PARAMETER_BROWSER_STYLES


class ParameterBrowser(QWidget):
    """A widget for browsing and adding llama.cpp parameters."""
    # Signal emits the parameter data (dict) and the input widget itself
    parameter_add_requested = pyqtSignal(dict, QWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser_param_rows = []
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(PARAMETER_BROWSER_STYLES["main_bg"])
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Search for a parameter...")
        search_bar.setClearButtonEnabled(True)
        search_bar.setStyleSheet(PARAMETER_BROWSER_STYLES["search_bar"])
        search_bar.textChanged.connect(self.filter_parameters)
        main_layout.addWidget(search_bar)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(PARAMETER_BROWSER_STYLES["scroll_area"])
        main_layout.addWidget(scroll_area)

        scroll_content = QWidget()
        self.browser_layout = QVBoxLayout(scroll_content)
        self.browser_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.browser_layout.setContentsMargins(0, 0, 5, 0)
        self.browser_layout.setSpacing(0)
        scroll_area.setWidget(scroll_content)

        self.browser_param_rows.clear()
        for group in LLAMA_CPP_PARAMETERS:
            self._create_group_box(group)

    def _create_group_box(self, group_data):
        group_box = QFrame()
        group_box.setStyleSheet(PARAMETER_BROWSER_STYLES["group_box"])
        group_layout = QVBoxLayout(group_box)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)

        header_button = QPushButton(f"►  {group_data['name']}")
        header_button.setProperty("is_collapsible", True)
        group_layout.addWidget(header_button)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        for param in group_data['parameters']:
            param_frame = self._create_param_row(param)
            content_layout.addWidget(param_frame)
            self.browser_param_rows.append({'frame': param_frame, 'group': group_box, 'data': param})

        content_widget.setLayout(content_layout)
        group_layout.addWidget(content_widget)
        self.browser_layout.addWidget(group_box)

        # Connect signal after all elements are created
        style_template = PARAMETER_BROWSER_STYLES["header_button_template"]
        header_button.clicked.connect(
            lambda chk=False, w=content_widget, b=header_button, s=style_template: self.toggle_group_box(w, b, s))

        content_widget.setVisible(False)
        header_button.setStyleSheet(style_template.format(radius="border-radius: 4px;"))

    def _create_param_row(self, param_data):
        param_frame = QFrame()
        param_frame.setStyleSheet(PARAMETER_BROWSER_STYLES["param_frame"])
        param_layout = QHBoxLayout(param_frame)
        param_layout.setSpacing(15)

        # Text part
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setSpacing(4)
        name_label = QLabel(f"{param_data['name']} ({param_data['prefix']})")
        name_label.setStyleSheet(PARAMETER_BROWSER_STYLES["param_name_label"])
        desc_label = QLabel(param_data['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(PARAMETER_BROWSER_STYLES["param_desc_label"])
        text_layout.addWidget(name_label)
        text_layout.addWidget(desc_label)
        param_layout.addWidget(text_widget, 3)

        # Input part
        input_widget_container = QWidget()
        input_layout = QVBoxLayout(input_widget_container)
        input_layout.setSpacing(5)
        input_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        param_input = None
        if param_data['type'] == 'checkbox':
            param_input = QCheckBox()
        elif param_data['type'] == 'select':
            param_input = QComboBox()
            param_input.addItems(param_data['options'])
            param_input.setStyleSheet(PARAMETER_BROWSER_STYLES["combo_box"])
            param_input.setMinimumWidth(120)
        else:  # number, text
            param_input = QLineEdit(str(param_data['default']))
            param_input.setStyleSheet(PARAMETER_BROWSER_STYLES["line_edit"])

        add_button = QPushButton("Add")
        add_button.setStyleSheet(PARAMETER_BROWSER_STYLES["add_button"])
        add_button.clicked.connect(
            lambda chk=False, p=param_data, inp=param_input: self.parameter_add_requested.emit(p, inp))

        input_layout.addWidget(param_input)
        input_layout.addWidget(add_button)
        param_layout.addWidget(input_widget_container, 1)

        return param_frame

    def toggle_group_box(self, widget, button, style_template):
        is_visible = widget.isVisible()
        widget.setVisible(not is_visible)
        if is_visible:
            button.setText(button.text().replace("▼", "►"))
            radius_style = "border-radius: 4px;"
        else:
            button.setText(button.text().replace("►", "▼"))
            radius_style = "border-top-left-radius: 4px; border-top-right-radius: 4px;"
        button.setStyleSheet(style_template.format(radius=radius_style))

    def filter_parameters(self, text):
        search_term = text.lower().strip()
        visible_groups = set()
        for row in self.browser_param_rows:
            is_match = (search_term in row['data']['name'].lower() or
                        search_term in row['data']['description'].lower() or
                        search_term in row['data']['prefix'].lower())
            row['frame'].setVisible(is_match)
            if is_match:
                visible_groups.add(row['group'])

        for row in self.browser_param_rows:
            row['group'].setVisible(row['group'] in visible_groups)