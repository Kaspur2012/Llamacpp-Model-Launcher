# ui/__init__.py

"""
This file marks the 'ui' directory as a Python package and exposes its key
classes for easier importing by other parts of the application.
"""

# Expose the primary UI components for convenient access.
from .main_window import MainWindow
from .left_panel import LeftPanel
from .right_panel import RightPanel
from .parameter_browser import ParameterBrowser
from .styles import get_dark_palette, PARAMETER_BROWSER_STYLES

# You can define what `from ui import *` would import, though it's
# often better to be explicit in your imports.
__all__ = [
    "MainWindow",
    "LeftPanel",
    "RightPanel",
    "ParameterBrowser",
    "get_dark_palette",
    "PARAMETER_BROWSER_STYLES",
]