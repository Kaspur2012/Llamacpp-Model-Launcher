# core/__init__.py

"""
This file marks the 'core' directory as a Python package.

The core package contains the fundamental business logic of the Llama.cpp
Model Launcher, completely decoupled from the user interface. It handles
configuration management, model file parsing, and command string manipulation.
"""

# Expose the primary logic components for convenient access.
from .config_manager import ConfigManager
from .model_manager import ModelManager
from .command_builder import CommandBuilder, Parameter
from .status import ServerStatus

# Defines the public API of the core package.
__all__ = [
    "ConfigManager",
    "ModelManager",
    "CommandBuilder",
    "Parameter",
    "ServerStatus",
]