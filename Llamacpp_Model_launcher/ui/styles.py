# ui/styles.py

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def get_dark_palette():
    """Creates and returns the dark theme palette for the application."""
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    return dark_palette

# Styles extracted from the original create_parameter_browser method
PARAMETER_BROWSER_STYLES = {
    "main_bg": "background-color: #2D323B;",
    "search_bar": "QLineEdit { background-color: #3C424C; border: 1px solid #505660; border-radius: 4px; padding: 5px 8px; font-size: 10pt; } QLineEdit:focus { border: 1px solid #4D90E2; }",
    "scroll_area": "border: none;",
    "group_box": "QFrame { background-color: #353A44; border: 1px solid #40454E; border-radius: 5px; margin-bottom: 8px; }",
    "header_button_template": "QPushButton {{ background-color: #3C424C; color: #E0E0E0; border: none; padding: 8px 10px; text-align: left; font-weight: bold; font-size: 11pt; {radius} }} QPushButton:hover {{ background-color: #454B56; }}",
    "param_frame": "QFrame { border: none; border-top: 1px solid #40454E; padding: 10px; }",
    "param_name_label": "font-weight: bold; color: #D1D1D1; font-size: 10pt;",
    "param_desc_label": "color: #A0A0A0; font-size: 9pt;",
    "add_button": "QPushButton { background-color: #4A85C9; color: white; border: none; border-radius: 4px; padding: 5px 12px; font-weight: bold; } QPushButton:hover { background-color: #5A95DA; } QPushButton:pressed { background-color: #3A75B9; }",
    "line_edit": "QLineEdit { background-color: #252930; border: 1px solid #505660; border-radius: 4px; padding: 4px; } QLineEdit:focus { border: 1px solid #4D90E2; }",
    "combo_box": "QComboBox { background-color: #252930; border: 1px solid #505660; border-radius: 4px; padding: 4px; padding-left: 6px; } QComboBox:hover { border: 1px solid #60656F; } QComboBox:on { border: 1px solid #4D90E2; } QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left-width: 1px; border-left-color: #505660; border-left-style: solid; border-top-right-radius: 3px; border-bottom-right-radius: 3px; } QComboBox::down-arrow { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #E0E0E0; margin: 0 auto; } QComboBox QAbstractItemView { background-color: #3C424C; color: #E0E0E0; border: 1px solid #505660; selection-background-color: #4A85C9; }"
}