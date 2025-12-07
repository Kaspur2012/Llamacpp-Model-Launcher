# core/model_manager.py

import os
from collections import OrderedDict, defaultdict


class ModelManager:
    """Handles parsing, loading, and saving model configurations to a text file."""

    def __init__(self, models_file_path):
        self.models_file_path = models_file_path
        self.models = OrderedDict()

    def set_models_file(self, file_path):
        """Updates the path to the models file."""
        self.models_file_path = file_path

    def load_models(self):
        """
        Parses the models file and loads the configurations into memory.
        Returns:
            An OrderedDict of model names to their command strings.
        """
        self.models.clear()
        if not self.models_file_path or not os.path.exists(self.models_file_path):
            return self.models

        try:
            with open(self.models_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            # Propagate error or handle it
            return self.models

        grouped_models = defaultdict(list)
        current_model_name = ""

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('-----'):
                continue

            # A line is considered a model name if it's not a command
            is_command = line.lower().startswith('llama-server.exe')

            if not is_command:
                # And the next line *is* a command
                if (i + 1 < len(lines)) and lines[i + 1].strip().lower().startswith('llama-server.exe'):
                    current_model_name = line
            else:  # It is a command line
                if current_model_name:
                    grouped_models[current_model_name].append(line)

        # Process grouped models to handle potential duplicate names
        temp_models = {}
        for name, commands in grouped_models.items():
            if len(commands) == 1:
                temp_models[name] = commands[0]
            else:
                # If a name has multiple commands, append a suffix
                base_name = name.split(' - ')[0].strip()
                for i, cmd in enumerate(commands, 1):
                    temp_models[f"{base_name} - Config {i}"] = cmd

        # Sort by name and store in an OrderedDict
        self.models = OrderedDict(sorted(temp_models.items()))
        return self.models

    def save_model(self, old_name, new_name, new_command, is_new):
        """
        Saves a new or updated model configuration to the models file.

        Args:
            old_name (str): The original name of the model, if editing.
            new_name (str): The new name for the model.
            new_command (str): The full command string for the model.
            is_new (bool): True if this is a new model, False if it's an edit.

        Returns:
            Tuple (bool, str): Success status and a message.
        """
        if not new_name:
            return False, "Model name cannot be empty."

        # Prevent overwriting an existing model with a different name
        if new_name != old_name and new_name in self.models:
            return False, f"A model named '{new_name}' already exists."

        if is_new:
            try:
                # --- FIX: Changed file mode from 'a' to 'a+' to allow reading ---
                with open(self.models_file_path, 'a+', encoding='utf-8') as f:
                    # Ensure there's a newline before adding the new entry
                    if f.tell() > 0:
                        f.seek(f.tell() - 1)
                        if f.read(1) != '\n':
                            f.write('\n')
                    f.write(f"\n{new_name}\n{new_command}\n")
                return True, f"New model '{new_name}' saved."
            except Exception as e:
                return False, f"Failed to save new model to file:\n{e}"
        else:
            try:
                with open(self.models_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                found = False
                for i, line in enumerate(lines):
                    if line.strip() == old_name:
                        lines[i] = new_name + '\n'
                        lines[i + 1] = new_command + '\n'
                        found = True
                        break

                if not found:
                    return False, f"Could not find original model '{old_name}' to update."

                with open(self.models_file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True, f"Configuration for '{new_name}' updated."
            except Exception as e:
                return False, f"Failed to update file:\n{e}"

    def delete_model(self, model_name_to_delete):
        """
        Deletes a model configuration from the file.

        Args:
            model_name_to_delete (str): The name of the model to delete.

        Returns:
            Tuple (bool, str): Success status and a message.
        """
        if not model_name_to_delete:
            return False, "No model selected to delete."

        try:
            with open(self.models_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            output_lines = []
            skip_next_line = False
            found = False
            for line in lines:
                if skip_next_line:
                    skip_next_line = False
                    continue
                if line.strip() == model_name_to_delete:
                    skip_next_line = True
                    found = True
                    continue
                output_lines.append(line)

            if not found:
                return False, f"Model '{model_name_to_delete}' not found in file."

            with open(self.models_file_path, 'w', encoding='utf-8') as f:
                f.writelines(output_lines)

            return True, f"'{model_name_to_delete}' was deleted."
        except Exception as e:
            return False, f"Failed to delete model from file:\n{e}"