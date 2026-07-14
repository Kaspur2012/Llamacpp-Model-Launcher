# core/model_manager.py

import os
from collections import OrderedDict, defaultdict


DEFAULT_TEMPLATE = """gpt-oss-20b-MXFP4
llama-server.exe -m D:\\lm_studio\\lmstudio-community\\gpt-oss-20b-GGUF\\gpt-oss-20b-MXFP4.gguf --jinja -c 131000 -ngl 999 -fa on --temp 1.0 --top-k 100 --top-p 1.0 --min-p 0.05 --repeat-penalty 1.1 --no-mmap --split-mode none --main-gpu 0 --parallel 1 --ubatch-size 8192 --batch-size 8192 --seed 1 -np 1 -fit off --no-warmup --spec-type ngram-simple

Qwen3.6-35B-A3B-UD-Q4_K_XL
llama-server.exe -m D:/backup_models/llm/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf -c 160000 --jinja --temp 1.0 --top-k 20 --top-p 0.95 --min-p 0.0 --no-warmup -ngl 99 -np 1 -fit off --flash-attn on --no-mmap -mg 0 --split-mode none --presence-penalty 0.0 --repeat-penalty 1.0 -ctk q8_0 -ctv q8_0 --spec-type ngram-simple --spec-ngram-mod-n-max 64

Qwen3.6-27B-Q5_K_S_DFLASH
llama-server.exe -m D:/backup_models/llm/Qwen3.6-27B-Q5_K_S.gguf -c 200000 --jinja --temp 0.6 --top-k 20 --min-p 0.0 --spec-draft-model D:\\backup_models\\llm\\dflash-draft-3.6-q4_k_m.gguf --no-warmup -ngl 99 --spec-type dflash --spec-dflash-cross-ctx 1024 --kv-unified --spec-draft-ngl all -b 2048 -ub 256 --cache-type-k turbo4 --cache-type-v turbo3_tcq -np 1 -fit off --flash-attn on --no-mmap -mg 0 --split-mode none --cache-ram 0 --mlock --metrics --log-timestamps --log-prefix --log-colors off --mmproj D:\\backup_models\\llm\\mmproj-BF16.gguf
llamacppdir: D:/llamacpp/beellama-v0.3.1-bin-win-cuda-12.4-x64

Qwen3.6-27B-UD-Q5_K_XL_MTP
llama-server.exe -m D:/backup_models/llm/Qwen3.6-27B-UD-Q5_K_XL.gguf --jinja --temp 0.6 --top-k 20 --min-p 0.0 --no-warmup -ngl 99 --spec-type draft-mtp -np 1 -fit off --flash-attn on --no-mmap -mg 0 --split-mode none --spec-draft-n-max 3 -c 100000 --spec-default --mmproj D:\\backup_models\\llm\\mmproj-BF16.gguf --chat-template-file D:\\backup_models\\llm\\qwen36_chat_template.jinja --chat-template-kwargs "{\\"preserve_thinking\\": true}" -ctk q8_0 -ctv q8_0
env:MTMD_BACKEND_DEVICE=cuda1

gemma-4-31B-it-qat-UD-Q4_K_XL
llama-server.exe -m D:/backup_models/llm/gemma-4-31B-it-qat-UD-Q4_K_XL.gguf -c 50000 --jinja --temp 1 --top-k 64 --top-p 0.95 --min-p 0.05 --spec-draft-n-max 3 --spec-type draft-mtp --no-warmup -ngl 99 -md D:/backup_models/llm/gemma-4-31B-it-Q8_0-MTP.gguf --spec_default -fit off -mg 0 --split-mode none --cache-type-k q8_0 --cache-type-v q8_0 --mmproj D:/backup_models/llm/gemma4_31b_mmproj-F16.gguf

gemma-4-26B-A4B-it-qat-UD-Q4_K_XL_MTP
llama-server.exe -m D:/backup_models/llm/gemma_4_26b_a4b_qat/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf -c 100000 --jinja --temp 1 --top-k 64 --top-p 0.95 --min-p 0.05 --spec-draft-n-max 3 --spec-type draft-mtp --no-warmup -ngl 99 -md D:/backup_models/llm/gemma_4_26b_a4b_qat/gemma-4-26B-A4B-it-BF16-MTP.gguf --spec_default -fit off -mg 0 --split-mode none --cache-type-k q8_0 --cache-type-v q8_0 --mmproj D:/backup_models/llm/gemma_4_26b_a4b_qat/mmproj-BF16.gguf

Qwen3.6-27B-UD-Q4_K_XL_MTP
llama-server.exe -m D:/backup_models/llm/Qwen3.6-27B-UD-Q4_K_XL.gguf --jinja --temp 0.6 --top-k 20 --min-p 0.0 --no-warmup -ngl 99 --spec-type draft-mtp -np 1 -fit off --flash-attn on --no-mmap -mg 0 --split-mode none --spec-draft-n-max 3 -c 145000 --spec-default --mmproj D:\\backup_models\\llm\\mmproj-BF16.gguf --chat-template-file D:\\backup_models\\llm\\qwen36_chat_template.jinja --chat-template-kwargs "{\\"preserve_thinking\\": true}" -ctk q8_0 -ctv q8_0
env:MTMD_BACKEND_DEVICE=cuda1
"""


class ModelManager:
    """Handles parsing, loading, and saving model configurations to a text file."""

    def __init__(self, models_file_path):
        self.models_file_path = models_file_path
        self.models = OrderedDict()
        self.model_env_vars = OrderedDict()  # model_name -> env_vars string
        self.model_llamacppdirs = OrderedDict()  # model_name -> llamacpp directory path

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
        self._model_env_vars = {}  # temp storage during parsing
        self._model_llamacppdirs = {}  # temp storage during parsing

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('-----'):
                continue

            # A line is considered a model name if it's not a command
            is_command = line.lower().startswith('llama-server')
            is_env_line = line.lower().startswith('env:')
            is_dir_line = line.lower().startswith('llamacppdir:')

            if not is_command and not is_env_line and not is_dir_line:
                # And the next line *is* a command
                if (i + 1 < len(lines)) and lines[i + 1].strip().lower().startswith('llama-server'):
                    current_model_name = line
            elif is_env_line and current_model_name:
                # Capture env vars line (line 3: env:KEY=value)
                self._model_env_vars[current_model_name] = line[4:].strip()  # strip 'env:' prefix
            elif is_dir_line and current_model_name:
                # Capture llama.cpp directory line (llamacppdir: D:\path)
                self._model_llamacppdirs[current_model_name] = line[len('llamacppdir:'):].strip()
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
        # Build env_vars dict (only for entries that had one)
        self.model_env_vars = OrderedDict(
            (name, self._model_env_vars.get(name, ""))
            for name in self.models
        )
        # Build llamacppdirs dict (only for entries that had one)
        self.model_llamacppdirs = OrderedDict(
            (name, self._model_llamacppdirs.get(name, ""))
            for name in self.models
        )
        return self.models

    @staticmethod
    def create_default_template(directory):
        """Create a default template models file in the given directory.
        Returns the full path of the created file, or None if creation failed."""
        filepath = os.path.join(directory, 'models.txt')
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(DEFAULT_TEMPLATE)
            return filepath
        except OSError:
            return None

    def _get_model_env_vars(self):
        """Returns a copy of the current env vars dict."""
        return dict(self.model_env_vars)

    def _get_model_llamacppdirs(self):
        """Returns a copy of the current llama.cpp directory dict."""
        return dict(self.model_llamacppdirs)

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
            env_vars_text = getattr(self, 'env_vars_to_save', '')
            try:
                # --- FIX: Changed file mode from 'a' to 'a+' to allow reading ---
                with open(self.models_file_path, 'a+', encoding='utf-8') as f:
                    # Ensure there's a newline before adding the new entry
                    if f.tell() > 0:
                        f.seek(f.tell() - 1)
                        if f.read(1) != '\n':
                            f.write('\n')
                    f.write(f"\n{new_name}\n{new_command}\n")
                    if env_vars_text:
                        f.write(f"env:{env_vars_text}\n")
                    llamacppdir_text = getattr(self, 'llamacppdir_to_save', '')
                    if llamacppdir_text:
                        f.write(f"llamacppdir: {llamacppdir_text}\n")
                return True, f"New model '{new_name}' saved."
            except Exception as e:
                return False, f"Failed to save new model to file:\n{e}"
        else:
            try:
                with open(self.models_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                env_vars_text = getattr(self, 'env_vars_to_save', '')
                llamacppdir_text = getattr(self, 'llamacppdir_to_save', '')
                found = False
                env_line_idx = None
                dir_line_idx = None
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped == old_name:
                        lines[i] = new_name + '\n'
                        lines[i + 1] = new_command + '\n'
                        found = True
                        # Check for existing env: and llamacppdir: lines after the command
                        for offset in range(2, 5):
                            if i + offset < len(lines):
                                check = lines[i + offset].strip().lower()
                                if check.startswith('env:'):
                                    env_line_idx = i + offset
                                elif check.startswith('llamacppdir:'):
                                    dir_line_idx = i + offset
                        break

                if not found:
                    return False, f"Could not find original model '{old_name}' to update."

                base_idx = lines.index(new_command + '\n') + 1

                # Update or add env vars line
                if env_vars_text:
                    if env_line_idx is not None:
                        lines[env_line_idx] = f"env:{env_vars_text}\n"
                    else:
                        lines.insert(base_idx, f"env:{env_vars_text}\n")
                        base_idx += 1
                        if dir_line_idx is not None:
                            dir_line_idx += 1
                elif env_line_idx is not None:
                    lines[env_line_idx] = ''  # Clear env line

                # Update or add llamacppdir line
                if llamacppdir_text:
                    if dir_line_idx is not None:
                        lines[dir_line_idx] = f"llamacppdir: {llamacppdir_text}\n"
                    else:
                        lines.insert(base_idx, f"llamacppdir: {llamacppdir_text}\n")
                elif dir_line_idx is not None:
                    lines[dir_line_idx] = ''  # Clear dir line

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