# core/status.py

from enum import Enum


class ServerStatus(Enum):
    """Enumeration for the server's state."""
    UNLOADED = ("unloaded", "Status: Unloaded", "#F44336")
    LOADING = ("loading", "Status: Loading...", "#FFEB3B")
    LOADED = ("loaded", "Status: Loaded", "#4CAF50")
    ERROR = ("error", "Status: Error", "#F44336")

    def __init__(self, key, label, color):
        self.key = key
        self.label = label
        self.color = color
