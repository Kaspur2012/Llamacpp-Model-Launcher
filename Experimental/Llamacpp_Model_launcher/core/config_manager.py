# core/config_manager.py

import configparser
import os


class ConfigManager:
    """Manages loading and saving of the application configuration file (config.ini)."""

    def __init__(self, config_file='config.ini'):
        self.config_file = config_file

    def load_config(self):
        """
        Loads the Llama.cpp directory and models file path from config.ini.
        Returns:
            A tuple (llamacpp_dir, models_file).
        """
        config = configparser.ConfigParser()
        llamacpp_dir = ''
        models_file = ''
        if os.path.exists(self.config_file):
            config.read(self.config_file)
            if 'Paths' in config:
                llamacpp_dir = config['Paths'].get('LlamaCppDir', '')
                models_file = config['Paths'].get('ModelsFile', '')
        return llamacpp_dir, models_file

    def save_config(self, llamacpp_dir, models_file):
        """
        Saves the given paths to the configuration file.
        Args:
            llamacpp_dir (str): Path to the Llama.cpp directory.
            models_file (str): Path to the models command file.
        """
        config = configparser.ConfigParser()
        config['Paths'] = {'LlamaCppDir': llamacpp_dir, 'ModelsFile': models_file}
        with open(self.config_file, 'w') as cf:
            config.write(cf)
