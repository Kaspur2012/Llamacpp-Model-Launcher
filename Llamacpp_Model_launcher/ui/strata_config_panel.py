# ui/strata_config_panel.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QScrollArea, QFrame, QPushButton, QCheckBox)
from Llamacpp_Model_launcher.core.strata_config import (ConfigSections, Row,
                                                        load_config, split_config,
                                                        merge_config)

_TITLE_QSS = "font-weight: bold; color: #D1D1D1; font-size: 10pt; background: transparent;"
_HINT_QSS = "color: #808080; font-size: 8pt; background: transparent;"
_FRAME_QSS = ("QFrame { background-color: #2D323B; border: 1px solid #40454E; "
              "border-radius: 4px; }")

SECTIONS = (
    ('args', 'Engine Args', 'The strata.exe command line — the main tuning surface (context, KV, spec/MTP, expert cache...)'),
    ('sampling', 'Sampling', 'Defaults for clients that send no sampling fields. Removing all rows = greedy decoding.'),
    ('settings', 'Config Settings', 'exe, cwd, gpu, port, reasoning_effort, log and every other top-level key.'),
    ('vision', 'Vision', 'The strata-vision encoder block (mmproj, model, device, max_tokens...).'),
    ('env', 'Engine Environment', 'Environment variables passed to the engine (KEY=value).'),
)


class StrataConfigPanel(QWidget):
    """Editor for the Strata JSON config, shown under the command parameters
    for Strata profiles. Loads the live config (greedy files are regenerated
    from it at launch) and rebuilds the dict on demand for saving."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = None
        self._original = {}
        self._loaded = False
        self._rows = {}       # section -> list of (key, input_widget)
        self._inputs = {}     # section -> list of input widgets (for reading back)
        self.row_changed_callback = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet(_FRAME_QSS)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(8, 6, 8, 6)
        frame_layout.setSpacing(4)

        title = QLabel("Strata Config (JSON)")
        title.setStyleSheet("font-weight: bold; color: #E0E0E0; font-size: 11pt; background: transparent;")
        self.path_label = QLabel("")
        self.path_label.setStyleSheet(_HINT_QSS)
        self.path_label.setWordWrap(True)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #E06060; font-size: 9pt; background: transparent;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        frame_layout.addWidget(title)
        frame_layout.addWidget(self.path_label)
        frame_layout.addWidget(self.error_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 4, 0, 0)
        self._content_layout.setSpacing(8)
        scroll.setWidget(content)
        frame_layout.addWidget(scroll, 1)

        outer.addWidget(frame)

        # Build the section scaffolding once; rows are rebuilt on load()
        self._section_row_layouts = {}
        self._section_name_inputs = {}
        self._section_value_inputs = {}
        for key, label, hint in SECTIONS:
            block = QVBoxLayout()
            block.setSpacing(2)
            sec_title = QLabel(label)
            sec_title.setStyleSheet(_TITLE_QSS)
            sec_hint = QLabel(hint)
            sec_hint.setStyleSheet(_HINT_QSS)
            sec_hint.setWordWrap(True)
            block.addWidget(sec_title)
            block.addWidget(sec_hint)
            rows_layout = QVBoxLayout()
            rows_layout.setSpacing(2)
            block.addLayout(rows_layout)
            self._section_row_layouts[key] = rows_layout

            add_layout = QHBoxLayout()
            add_layout.setSpacing(4)
            name_input = QLineEdit()
            name_input.setPlaceholderText("--flag" if key == 'args' else "key")
            value_input = QLineEdit()
            value_input.setPlaceholderText("value (empty = flag)" if key == 'args' else "value")
            add_button = QPushButton("Add")
            add_button.setFixedWidth(50)
            add_button.clicked.connect(lambda _, k=key: self._add_row_from_inputs(k))
            add_layout.addWidget(name_input, 2)
            add_layout.addWidget(value_input, 3)
            add_layout.addWidget(add_button)
            block.addLayout(add_layout)
            self._section_name_inputs[key] = name_input
            self._section_value_inputs[key] = value_input

            self._content_layout.addLayout(block)
        self._content_layout.addStretch()

    # ------------------------------------------------------------------ load

    def load(self, path, note=""):
        """Loads the config at path. note is extra text for the path line."""
        self._loaded = False
        self._path = path
        self._original = {}
        self._clear_all_rows()
        if not path:
            self.path_label.setText("No --config parameter found in this profile.")
            self.error_label.setText("")
            self.error_label.hide()
            return
        data, err = load_config(path)
        if err:
            self.path_label.setText(path + (("  —  " + note) if note else ""))
            self.error_label.setText(f"Could not read config: {err}")
            self.error_label.show()
            return
        self.error_label.hide()
        self._original = data
        self.path_label.setText(f"Editing: {path}" + (("   —   " + note) if note else ""))
        sections = split_config(data)
        for key, rows in zip(('args', 'sampling', 'settings', 'vision', 'env'),
                             (sections.args, sections.sampling, sections.settings,
                              sections.vision, sections.env)):
            for row in rows:
                self._add_row(key, row.key, row.value)
        self._loaded = True

    def is_loaded(self):
        return self._loaded

    # ------------------------------------------------------------------ rows

    def _clear_all_rows(self):
        for key, layout in self._section_row_layouts.items():
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    sub = item.layout()
                    while sub.count():
                        sub_item = sub.takeAt(0)
                        if sub_item.widget():
                            sub_item.widget().deleteLater()
            self._rows[key] = []

    def _add_row(self, section, key, value):
        row_layout = QHBoxLayout()
        row_layout.setSpacing(4)
        key_label = QLabel(key if key else "(orphan)")
        key_label.setMinimumWidth(170)
        key_label.setStyleSheet("color: #B0B8C4; background: transparent;")
        if isinstance(value, bool):
            input_widget = QCheckBox()
            input_widget.setChecked(value)
        else:
            input_widget = QLineEdit("" if value is None else str(value))
            if section == 'args':
                input_widget.setPlaceholderText("(flag — leave empty)")
        if hasattr(self, 'row_changed_callback') and self.row_changed_callback:
            if isinstance(input_widget, QCheckBox):
                input_widget.stateChanged.connect(self.row_changed_callback)
            else:
                input_widget.textChanged.connect(self.row_changed_callback)
        remove_button = QPushButton("X")
        remove_button.setFixedWidth(26)
        remove_button.setToolTip(f"Remove {key}")
        remove_button.clicked.connect(lambda _, s=section, w=input_widget: self._remove_row(s, w))
        row_layout.addWidget(key_label)
        row_layout.addWidget(input_widget, 1)
        row_layout.addWidget(remove_button)
        self._section_row_layouts[section].addLayout(row_layout)
        self._rows.setdefault(section, []).append((key, input_widget))

    def _remove_row(self, section, input_widget):
        rows = self._rows.get(section, [])
        for i, (key, widget) in enumerate(rows):
            if widget is input_widget:
                rows.pop(i)
                break
        layout = self._section_row_layouts[section]
        for j in range(layout.count()):
            item = layout.itemAt(j)
            sub = item.layout() if item else None
            if not sub:
                continue
            widgets = [sub.itemAt(k).widget() for k in range(sub.count())]
            if input_widget in widgets:
                # Remove the whole row layout
                while sub.count():
                    sub_item = sub.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                layout.removeItem(item)
                break
        if self.row_changed_callback:
            self.row_changed_callback()

    def _add_row_from_inputs(self, section):
        key = self._section_name_inputs[section].text().strip()
        if not key:
            return
        value_text = self._section_value_inputs[section].text().strip()
        if section == 'args':
            value = None if value_text == '' else value_text
        else:
            value = value_text
        self._add_row(section, key, value)
        self._section_name_inputs[section].clear()
        self._section_value_inputs[section].clear()
        if self.row_changed_callback:
            self.row_changed_callback()

    def add_arg(self, flag, value):
        """Adds an Engine Args row (used by the parameter browser)."""
        self._add_row('args', flag, value)
        if self.row_changed_callback:
            self.row_changed_callback()

    # ------------------------------------------------------------------ read

    def _read_section(self, section):
        rows = []
        for key, widget in self._rows.get(section, []):
            if isinstance(widget, QCheckBox):
                rows.append(Row(key, widget.isChecked()))
            else:
                text = widget.text()
                if section == 'args' and text.strip() == '':
                    rows.append(Row(key, None))
                else:
                    rows.append(Row(key, text))
        return rows

    def get_sections(self):
        return ConfigSections(self._read_section('args'), self._read_section('sampling'),
                              self._read_section('settings'), self._read_section('vision'),
                              self._read_section('env'))

    def get_config(self):
        """Returns the rebuilt config dict, or None if no config is loaded."""
        if not self._loaded:
            return None
        return merge_config(self._original, self.get_sections())

    def config_path(self):
        return self._path
