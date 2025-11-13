# parameters_db.py


# --- NEW: Help documentation is now stored here and imported by the main app ---
HELP_DOCUMENTATION = """
## Llama.cpp Model Launcher: User Guide

### 1. Introduction

Welcome to the Llama.cpp Model Launcher! This application provides a clean, powerful, and user-friendly graphical interface (GUI) for the `llama-server.exe` tool from the Llama.cpp project.

Its purpose is to replace the tedious and error-prone process of typing long commands into a terminal. With this launcher, you can manage, edit, delete, duplicate and run all your language models with the point-and-click simplicity of a modern desktop application.

### 2. First-Time Setup

Before you can launch a model, you need to tell the application where to find two key items. This is a one-time setup, and your choices will be saved for future sessions.

1.  **Set the Llama.cpp Directory**:
    *   Click the **Browse...** button next to the "Llama.cpp Directory" label.
    *   Navigate to and select the folder that contains your `llama-server.exe` file.
    *   The application will verify that `llama-server.exe` exists in the selected folder.

2.  **Set the Models File**:
    *   Click the **Browse...** button next to the "Models File" label.
    *   Select the `.txt` file that contains your model launch commands.
    *   **File Format**: This text file must be structured with a model name on one line, followed immediately by its full launch command on the next line. For example:
        ```        Llama-3-8B-Instruct-Q6_K
        llama-server.exe -m D:\\models\\Llama-3-8B-Instruct-Q6_K.gguf -c 4096 -ngl 99 -fa on

        Mistral-7B-Instruct-v0.2-Q5_K_M
        llama-server.exe -m D:\\models\\mistral-7b-instruct-v0.2.Q5_K_M.gguf -c 4096 -ngl 99
        ```

Once both paths are set, the **Model Selection** dropdown menu will automatically populate with the names from your text file.

### 3. The Main Interface

The application is divided into two main panels.

#### Left Panel: Main Control & Display
This is where you select and control the model server.

*   **Model Selection Dropdown**: Choose the model configuration you wish to load.
*   **Web UI Options**:
    *   `Enable Web UI`: Keep this checked to run the standard web server. Unchecking it adds the `--no-webui` flag to the command.
    *   `Auto-Open Web UI`: If checked, your web browser will automatically open to the server's page (`http://localhost:8080`) a single time after the model successfully loads.
*   **Process Control Buttons**:
    *   **Load Model**: Builds the final command from the editor and starts the `llama-server.exe` process.
    *   **Unload Model**: Forcefully stops the server process.
    *   **Exit**: Stops any running server and closes the application.
*   **Status Indicator**: A colored dot gives you an at-a-glance view of the server's state:
    *   **Red (Unloaded)**: The server is not running.
    *   **Yellow (Loading...)**: The server is loading the model into memory.
    *   **Green (Loaded)**: The model is successfully loaded and ready.
    *   **Red (Error)**: The server process terminated unexpectedly.
*   **Output / Commands / Help View**:
    *   The main text area shows the **live output** from the server by default.
    *   Click the **Commands** button to switch to the **Parameter Browser**. This interactive UI allows you to search for and discover all available Llama.cpp parameters. Each parameter has a description and an "Add" button to add it directly to your model's configuration.
    *   Click the **Help** button to view this user guide at any time.
    *   Click **Show Output** to return to the live log from either the Commands or Help view.

#### Right Panel: Configuration Editor
This is where you can view and modify all aspects of the selected model's configuration.

*   **Model Name**: An editable field for the display name that appears in the dropdown.
*   **Parameter Editor**: A dynamic list of all parameters for the selected command. Flags (like `--no-mmap`) are shown as **checkboxes**, and parameters with values (like `-c 4096`) are shown as **text fields**.
*   **Add New Parameter**: Allows you to manually add any valid Llama.cpp parameter to the current configuration. For a guided experience, use the **Parameter Browser** on the left.
*   **Action Buttons**:
    *   **Add**: Prepares the editor for a new model configuration using a default template.
    *   **Duplicate**: Creates a copy of the currently selected configuration for easy modification.
    *   **Delete**: Deletes the currently selected model from your `.txt` file.
    *   **Reset**: Discards any unsaved changes in the editor.
    *   **Save to File**: Permanently saves all changes (name and parameters) to your `.txt` file.

### 4. Common Issue

**When I click "Load Model," nothing happens.**
This almost always means the Llama.cpp Directory path is incorrect, often after updating Llama.cpp to a new version. Simply click the **Browse...** button and point the application to the new folder containing your updated `llama-server.exe`.
"""


# This file contains the structured database of all Llama.cpp parameters.
# The 'options' for select types with numeric values have been converted
# to a list of strings to ensure compatibility with the Python GUI application.

# thanks https://x.com/unmortan for the info you see below
# https://www.reddit.com/r/LocalLLaMA/comments/1opx9k2/comment/nnf2gr9/?context=1

LLAMA_CPP_PARAMETERS = [
    {
        "name": "File Paths",
        "collapsed": False,
        "parameters": [
            {'name': 'Server Path', 'id': 'server-path', 'type': 'text', 'default': '', 'description': 'Path to llama-server.exe file without quotes. Example: D:\\NEURAL\\LlamaCpp\\CUDA\\llama-server', 'required': True, 'prefix': ''},
            {'name': 'Model Path', 'id': 'model-path', 'type': 'text', 'default': '', 'description': 'Path to model GGUF file without quotes. Example: D:\\NEURAL\\models\\Qwen3-30B-A3B-Instruct-2507-Q6_K\\Qwen3-30B-A3B-Instruct-2507-Q6_K.gguf', 'required': True, 'prefix': '-m'},
        ]
    },
    {
        "name": "Common Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Help', 'id': 'help', 'type': 'checkbox', 'default': False, 'description': 'Print usage information and exit', 'prefix': '-h'},
            {'name': 'Version', 'id': 'version', 'type': 'checkbox', 'default': False, 'description': 'Show version and build information', 'prefix': '--version'},
            {'name': 'Completion Bash', 'id': 'completion-bash', 'type': 'checkbox', 'default': False, 'description': 'Print source-able bash completion script for llama.cpp', 'prefix': '--completion-bash'},
            {'name': 'Verbose Prompt', 'id': 'verbose-prompt', 'type': 'checkbox', 'default': False, 'description': 'Print a verbose prompt before generation (default: false)', 'prefix': '--verbose-prompt'},
        ]
    },
    {
        "name": "Threading & CPU Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Threads', 'id': 'threads', 'type': 'number', 'default': '-1', 'description': 'Number of threads to use during generation (default: -1). Environment variable: LLAMA_ARG_THREADS', 'prefix': '-t'},
            {'name': 'Threads Batch', 'id': 'threads-batch', 'type': 'number', 'default': '-1', 'description': 'Number of threads to use during batch and prompt processing (default: same as --threads)', 'prefix': '-tb'},
            {'name': 'CPU Mask', 'id': 'cpu-mask', 'type': 'text', 'default': '', 'description': 'CPU affinity mask: arbitrarily long hex. Complements cpu-range (default: "")', 'prefix': '-C'},
            {'name': 'CPU Range', 'id': 'cpu-range', 'type': 'text', 'default': '', 'description': 'Range of CPUs for affinity. Complements --cpu-mask. Format: lo-hi', 'prefix': '-Cr'},
            {'name': 'CPU Strict', 'id': 'cpu-strict', 'type': 'select', 'default': '0', 'options': ['0', '1'], 'description': 'Use strict CPU placement (0: Disabled, 1: Enabled)', 'prefix': '--cpu-strict'},
            {'name': 'Priority', 'id': 'priority', 'type': 'select', 'default': '0', 'options': ['-1', '0', '1', '2', '3'], 'description': 'Set process/thread priority (-1: Low, 0: Normal, 1: Medium, 2: High, 3: Realtime)', 'prefix': '--prio'},
            {'name': 'Poll', 'id': 'poll', 'type': 'number', 'default': '50', 'min': '0', 'max': '100', 'description': 'Use polling level to wait for work (0 - no polling, default: 50)', 'prefix': '--poll'},
            {'name': 'CPU Mask Batch', 'id': 'cpu-mask-batch', 'type': 'text', 'default': '', 'description': 'CPU affinity mask for batch processing (default: same as --cpu-mask)', 'prefix': '-Cb'},
            {'name': 'CPU Range Batch', 'id': 'cpu-range-batch', 'type': 'text', 'default': '', 'description': 'Ranges of CPUs for batch affinity. Complements --cpu-mask-batch', 'prefix': '-Crb'},
            {'name': 'CPU Strict Batch', 'id': 'cpu-strict-batch', 'type': 'select', 'default': '0', 'options': ['0', '1'], 'description': 'Use strict CPU placement for batch operations (0: Disabled, 1: Enabled)', 'prefix': '--cpu-strict-batch'},
            {'name': 'Priority Batch', 'id': 'priority-batch', 'type': 'number', 'default': '0', 'description': 'Set batch process/thread priority (default: 0)', 'prefix': '--prio-batch'},
            {'name': 'Poll Batch', 'id': 'poll-batch', 'type': 'select', 'default': '0', 'options': ['0', '1'], 'description': 'Use polling to wait for batch work (0: Disabled, 1: Enabled)', 'prefix': '--poll-batch'},
        ]
    },
    {
        "name": "Context & Prediction Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Context Size', 'id': 'ctx-size', 'type': 'number', 'default': '4096', 'description': 'Size of the prompt context (default: 4096, 0 = loaded from model). Environment variable: LLAMA_ARG_CTX_SIZE', 'prefix': '-c'},
            {'name': 'Predict Tokens', 'id': 'n-predict', 'type': 'number', 'default': '-1', 'description': 'Number of tokens to predict (default: -1, -1 = infinity). Environment variable: LLAMA_ARG_N_PREDICT', 'prefix': '-n'},
            {'name': 'Batch Size', 'id': 'batch-size', 'type': 'number', 'default': '2048', 'description': 'Logical maximum batch size (default: 2048). Environment variable: LLAMA_ARG_BATCH', 'prefix': '-b'},
            {'name': 'UBatch Size', 'id': 'ubatch-size', 'type': 'number', 'default': '512', 'description': 'Physical maximum batch size (default: 512). Environment variable: LLAMA_ARG_UBATCH', 'prefix': '-ub'},
            {'name': 'Keep Tokens', 'id': 'keep', 'type': 'number', 'default': '0', 'description': 'Number of tokens to keep from the initial prompt (default: 0, -1 = all)', 'prefix': '--keep'},
        ]
    },
    {
        "name": "Attention & Cache Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'SWA Full', 'id': 'swa-full', 'type': 'checkbox', 'default': False,
             'description': 'Use full-size SWA cache (default: false). Environment variable: LLAMA_ARG_SWA_FULL',
             'prefix': '--swa-full'},
            {'name': 'KV Unified', 'id': 'kv-unified', 'type': 'checkbox', 'default': False,
             'description': 'Use single unified KV buffer for the KV cache of all sequences (default: false). Environment variable: LLAMA_ARG_KV_SPLIT',
             'prefix': '-kvu'},

            # --- FIX: Changed from 'checkbox' to 'select' and added options ---
            {'name': 'Flash Attention', 'id': 'flash-attn', 'type': 'select', 'default': 'on', 'options': ['on', 'off'],
             'description': 'Enable or disable Flash Attention (default: off). Environment variable: LLAMA_ARG_FLASH_ATTN',
             'prefix': '--flash-attn'},

            {'name': 'No Performance', 'id': 'no-perf', 'type': 'checkbox', 'default': False,
             'description': 'Disable internal libllama performance timings (default: false). Environment variable: LLAMA_ARG_NO_PERF',
             'prefix': '--no-perf'},
            {'name': 'No KV Offload', 'id': 'no-kv-offload', 'type': 'checkbox', 'default': False,
             'description': 'Disable KV offload. Environment variable: LLAMA_ARG_NO_KV_OFFLOAD', 'prefix': '-nkvo'},
            {'name': 'No Repack', 'id': 'no-repack', 'type': 'checkbox', 'default': False,
             'description': 'Disable weight repacking. Environment variable: LLAMA_ARG_NO_REPACK', 'prefix': '-nr'},
            {'name': 'Cache Type K', 'id': 'cache-type-k', 'type': 'select', 'default': 'f16',
             'options': ['f32', 'f16', 'bf16', 'q8_0', 'q4_0', 'q4_1', 'iq4_nl', 'q5_0', 'q5_1'],
             'description': 'KV cache data type for K (default: f16). Environment variable: LLAMA_ARG_CACHE_TYPE_K',
             'prefix': '--cache-type-k'},
            {'name': 'Cache Type V', 'id': 'cache-type-v', 'type': 'select', 'default': 'f16',
             'options': ['f32', 'f16', 'bf16', 'q8_0', 'q4_0', 'q4_1', 'iq4_nl', 'q5_0', 'q5_1'],
             'description': 'KV cache data type for V (default: f16). Environment variable: LLAMA_ARG_CACHE_TYPE_V',
             'prefix': '--cache-type-v'},
            {'name': 'Parallel', 'id': 'parallel', 'type': 'number', 'default': '1',
             'description': 'Number of parallel sequences to decode (default: 1). Environment variable: LLAMA_ARG_N_PARALLEL',
             'prefix': '-np'},
        ]
    },
    {
        "name": "Memory & System Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'MLock', 'id': 'mlock', 'type': 'checkbox', 'default': False, 'description': 'Force system to keep model in RAM rather than swapping or compressing. Environment variable: LLAMA_ARG_MLOCK', 'prefix': '--mlock'},
            {'name': 'No MMap', 'id': 'no-mmap', 'type': 'checkbox', 'default': False, 'description': 'Do not memory-map model (slower load but may reduce pageouts if not using mlock). Environment variable: LLAMA_ARG_NO_MMAP', 'prefix': '--no-mmap'},
            {'name': 'NUMA', 'id': 'numa', 'type': 'select', 'default': '', 'options': ['', 'distribute', 'isolate', 'numactl'], 'description': 'Attempt optimizations that help on some NUMA systems. Environment variable: LLAMA_ARG_NUMA', 'prefix': '--numa'},
            {'name': 'Device', 'id': 'device', 'type': 'text', 'default': '', 'description': "Comma-separated list of devices to use for offloading (none = don't offload). Use --list-devices to see available devices. Environment variable: LLAMA_ARG_DEVICE", 'prefix': '-dev'},
            {'name': 'List Devices', 'id': 'list-devices', 'type': 'checkbox', 'default': False, 'description': 'Print list of available devices and exit', 'prefix': '--list-devices'},
            {'name': 'Override Tensor', 'id': 'override-tensor', 'type': 'text', 'default': '', 'description': 'Override tensor buffer type with pattern: <tensor name pattern>=<buffer type>', 'prefix': '-ot'},
            {'name': 'CPU MoE', 'id': 'cpu-moe', 'type': 'checkbox', 'default': False, 'description': 'Keep all Mixture of Experts (MoE) weights in the CPU. Environment variable: LLAMA_ARG_CPU_MOE', 'prefix': '-cmoe'},
            {'name': 'N CPU MoE', 'id': 'n-cpu-moe', 'type': 'number', 'default': '0', 'description': 'Keep the Mixture of Experts (MoE) weights of the first N layers in the CPU. Environment variable: LLAMA_ARG_N_CPU_MOE', 'prefix': '-ncmoe'},
        ]
    },
    {
        "name": "GPU Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'GPU Layers', 'id': 'gpu-layers', 'type': 'number', 'default': '0', 'description': 'Number of layers to store in VRAM. Environment variable: LLAMA_ARG_N_GPU_LAYERS', 'prefix': '-ngl'},
            {'name': 'Split Mode', 'id': 'split-mode', 'type': 'select', 'default': 'layer', 'options': ['none', 'layer', 'row'], 'description': 'How to split the model across multiple GPUs. none: use one GPU only, layer (default): split layers and KV across GPUs, row: split rows across GPUs. Environment variable: LLAMA_ARG_SPLIT_MODE', 'prefix': '-sm'},
            {'name': 'Tensor Split', 'id': 'tensor-split', 'type': 'text', 'default': '', 'description': 'Fraction of the model to offload to each GPU. Comma-separated list of proportions, e.g. 3,1. Environment variable: LLAMA_ARG_TENSOR_SPLIT', 'prefix': '-ts'},
            {'name': 'Main GPU', 'id': 'main-gpu', 'type': 'number', 'default': '0', 'description': 'The GPU to use for the model (with split-mode = none), or for intermediate results and KV (with split-mode = row) (default: 0). Environment variable: LLAMA_ARG_MAIN_GPU', 'prefix': '-mg'},
        ]
    },
    {
        "name": "Model & Adapter Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Check Tensors', 'id': 'check-tensors', 'type': 'checkbox', 'default': False, 'description': 'Check model tensor data for invalid values (default: false)', 'prefix': '--check-tensors'},
            {'name': 'Override KV', 'id': 'override-kv', 'type': 'text', 'default': '', 'description': 'Advanced option to override model metadata by key. May be specified multiple times. Types: int, float, bool, str. Example: --override-kv tokenizer.ggml.add_bos_token=bool:false', 'prefix': '--override-kv'},
            {'name': 'No Op Offload', 'id': 'no-op-offload', 'type': 'checkbox', 'default': False, 'description': 'Disable offloading host tensor operations to device (default: false)', 'prefix': '--no-op-offload'},
            {'name': 'LoRA', 'id': 'lora', 'type': 'text', 'default': '', 'description': 'Path to LoRA adapter (can be repeated to use multiple adapters)', 'prefix': '--lora'},
            {'name': 'LoRA Scaled', 'id': 'lora-scaled', 'type': 'text', 'default': '', 'description': 'Path to LoRA adapter with user defined scaling (can be repeated). Format: FNAME SCALE', 'prefix': '--lora-scaled'},
            {'name': 'Control Vector', 'id': 'control-vector', 'type': 'text', 'default': '', 'description': 'Add a control vector (can be repeated to add multiple control vectors)', 'prefix': '--control-vector'},
            {'name': 'Control Vector Scaled', 'id': 'control-vector-scaled', 'type': 'text', 'default': '', 'description': 'Add a control vector with user defined scaling SCALE. Format: FNAME SCALE', 'prefix': '--control-vector-scaled'},
            {'name': 'Control Vector Layer Range', 'id': 'control-vector-layer-range', 'type': 'text', 'default': '', 'description': 'Layer range to apply the control vector(s) to, start and end inclusive. Format: START END', 'prefix': '--control-vector-layer-range'},
        ]
    },
    {
        "name": "Model Loading Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Model URL', 'id': 'model-url', 'type': 'text', 'default': '', 'description': 'Model download url (default: unused). Environment variable: LLAMA_ARG_MODEL_URL', 'prefix': '-mu'},
            {'name': 'HF Repo', 'id': 'hf-repo', 'type': 'text', 'default': '', 'description': 'Hugging Face model repository; quant is optional, case-insensitive, default to Q4_K_M. Example: unsloth/phi-4-GGUF:q4_k_m. Environment variable: LLAMA_ARG_HF_REPO', 'prefix': '-hf'},
            {'name': 'HF Repo Draft', 'id': 'hf-repo-draft', 'type': 'text', 'default': '', 'description': 'Same as --hf-repo, but for the draft model. Environment variable: LLAMA_ARG_HFD_REPO', 'prefix': '-hfd'},
            {'name': 'HF File', 'id': 'hf-file', 'type': 'text', 'default': '', 'description': 'Hugging Face model file. Overrides the quant in --hf-repo. Environment variable: LLAMA_ARG_HF_FILE', 'prefix': '-hff'},
            {'name': 'HF Token', 'id': 'hf-token', 'type': 'text', 'default': '', 'description': 'Hugging Face access token (default: value from HF_TOKEN environment variable). Environment variable: HF_TOKEN', 'prefix': '-hft'},
        ]
    },
    {
        "name": "Logging & Debug Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Log Disable', 'id': 'log-disable', 'type': 'checkbox', 'default': False, 'description': 'Disable logging', 'prefix': '--log-disable'},
            {'name': 'Log File', 'id': 'log-file', 'type': 'text', 'default': '', 'description': 'Log to file', 'prefix': '--log-file'},
            {'name': 'Log Colors', 'id': 'log-colors', 'type': 'checkbox', 'default': False, 'description': 'Enable colored logging. Environment variable: LLAMA_LOG_COLORS', 'prefix': '--log-colors'},
            {'name': 'Verbose', 'id': 'verbose', 'type': 'checkbox', 'default': False, 'description': 'Set verbosity level to infinity (log all messages, useful for debugging)', 'prefix': '-v'},
            {'name': 'Offline', 'id': 'offline', 'type': 'checkbox', 'default': False, 'description': 'Offline mode: forces use of cache, prevents network access. Environment variable: LLAMA_OFFLINE', 'prefix': '--offline'},
            {'name': 'Verbosity', 'id': 'verbosity', 'type': 'number', 'default': '0', 'description': 'Set the verbosity threshold. Messages with higher verbosity will be ignored. Environment variable: LLAMA_LOG_VERBOSITY', 'prefix': '-lv'},
            {'name': 'Log Prefix', 'id': 'log-prefix', 'type': 'checkbox', 'default': False, 'description': 'Enable prefix in log messages. Environment variable: LLAMA_LOG_PREFIX', 'prefix': '--log-prefix'},
            {'name': 'Log Timestamps', 'id': 'log-timestamps', 'type': 'checkbox', 'default': False, 'description': 'Enable timestamps in log messages. Environment variable: LLAMA_LOG_TIMESTAMPS', 'prefix': '--log-timestamps'},
        ]
    },
    {
        "name": "ROPE & Context Scaling Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Escape', 'id': 'escape', 'type': 'select', 'default': 'true', 'options': ['true', 'false'], 'description': "Process escapes sequences (\\n, \\r, \\t, ', \", \\) (default: true)", 'prefix': '-e'},
            {'name': 'ROPE Scaling', 'id': 'rope-scaling', 'type': 'select', 'default': '', 'options': ['', 'none', 'linear', 'yarn'], 'description': 'RoPE frequency scaling method, defaults to linear unless specified by the model. Environment variable: LLAMA_ARG_ROPE_SCALING_TYPE', 'prefix': '--rope-scaling'},
            {'name': 'ROPE Scale', 'id': 'rope-scale', 'type': 'number', 'default': '1.0', 'description': 'RoPE context scaling factor, expands context by a factor of N. Environment variable: LLAMA_ARG_ROPE_SCALE', 'prefix': '--rope-scale'},
            {'name': 'ROPE Freq Base', 'id': 'rope-freq-base', 'type': 'number', 'default': '0', 'description': 'RoPE base frequency, used by NTK-aware scaling (default: loaded from model). Environment variable: LLAMA_ARG_ROPE_FREQ_BASE', 'prefix': '--rope-freq-base'},
            {'name': 'ROPE Freq Scale', 'id': 'rope-freq-scale', 'type': 'number', 'default': '1.0', 'description': 'RoPE frequency scaling factor, expands context by a factor of 1/N. Environment variable: LLAMA_ARG_ROPE_FREQ_SCALE', 'prefix': '--rope-freq-scale'},
            {'name': 'YARN Orig Ctx', 'id': 'yarn-orig-ctx', 'type': 'number', 'default': '0', 'description': 'YaRN: original context size of model (default: 0 = model training context size). Environment variable: LLAMA_ARG_YARN_ORIG_CTX', 'prefix': '--yarn-orig-ctx'},
            {'name': 'YARN Ext Factor', 'id': 'yarn-ext-factor', 'type': 'number', 'default': '-1.0', 'description': 'YaRN: extrapolation mix factor (default: -1.0, 0.0 = full interpolation). Environment variable: LLAMA_ARG_YARN_EXT_FACTOR', 'prefix': '--yarn-ext-factor'},
            {'name': 'YARN Attn Factor', 'id': 'yarn-attn-factor', 'type': 'number', 'default': '1.0', 'description': 'YaRN: scale sqrt(t) or attention magnitude (default: 1.0). Environment variable: LLAMA_ARG_YARN_ATTN_FACTOR', 'prefix': '--yarn-attn-factor'},
            {'name': 'YARN Beta Slow', 'id': 'yarn-beta-slow', 'type': 'number', 'default': '1.0', 'description': 'YaRN: high correction dim or alpha (default: 1.0). Environment variable: LLAMA_ARG_YARN_BETA_SLOW', 'prefix': '--yarn-beta-slow'},
            {'name': 'YARN Beta Fast', 'id': 'yarn-beta-fast', 'type': 'number', 'default': '32.0', 'description': 'YaRN: low correction dim or beta (default: 32.0). Environment variable: LLAMA_ARG_YARN_BETA_FAST', 'prefix': '--yarn-beta-fast'},
        ]
    },
    {
        "name": "Sampling Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Samplers', 'id': 'samplers', 'type': 'text', 'default': 'penalties;dry;top_n_sigma;top_k;typ_p;top_p;min_p;xtc;temperature', 'description': "Samplers that will be used for generation in the order, separated by ';' (default: penalties;dry;top_n_sigma;top_k;typ_p;top_p;min_p;xtc;temperature)", 'prefix': '--samplers'},
            {'name': 'Seed', 'id': 'seed', 'type': 'number', 'default': '-1', 'description': 'RNG seed (default: -1, use random seed for -1)', 'prefix': '-s'},
            {'name': 'Sampling Seq', 'id': 'sampling-seq', 'type': 'text', 'default': 'edskypmxt', 'description': 'Simplified sequence for samplers that will be used (default: edskypmxt)', 'prefix': '--sampling-seq'},
            {'name': 'Ignore EOS', 'id': 'ignore-eos', 'type': 'checkbox', 'default': False, 'description': 'Ignore end of stream token and continue generating (implies --logit-bias EOS-inf)', 'prefix': '--ignore-eos'},
            {'name': 'Temperature', 'id': 'temp', 'type': 'number', 'default': '0.8', 'description': 'Temperature (default: 0.8)', 'prefix': '--temp'},
            {'name': 'Top K', 'id': 'top-k', 'type': 'number', 'default': '40', 'description': 'Top-k sampling (default: 40, 0 = disabled)', 'prefix': '--top-k'},
            {'name': 'Top P', 'id': 'top-p', 'type': 'number', 'default': '0.9', 'description': 'Top-p sampling (default: 0.9, 1.0 = disabled)', 'prefix': '--top-p'},
            {'name': 'Min P', 'id': 'min-p', 'type': 'number', 'default': '0.1', 'description': 'Min-p sampling (default: 0.1, 0.0 = disabled)', 'prefix': '--min-p'},
            {'name': 'Top N Sigma', 'id': 'top-nsigma', 'type': 'number', 'default': '-1.0', 'description': 'Top-n-sigma sampling (default: -1.0, -1.0 = disabled)', 'prefix': '--top-nsigma'},
            {'name': 'XTC Probability', 'id': 'xtc-probability', 'type': 'number', 'default': '0.0', 'description': 'XTC probability (default: 0.0, 0.0 = disabled)', 'prefix': '--xtc-probability'},
            {'name': 'XTC Threshold', 'id': 'xtc-threshold', 'type': 'number', 'default': '0.1', 'description': 'XTC threshold (default: 0.1, 1.0 = disabled)', 'prefix': '--xtc-threshold'},
            {'name': 'Typical', 'id': 'typical', 'type': 'number', 'default': '1.0', 'description': 'Locally typical sampling, parameter p (default: 1.0, 1.0 = disabled)', 'prefix': '--typical'},
            {'name': 'Repeat Last N', 'id': 'repeat-last-n', 'type': 'number', 'default': '64', 'description': 'Last n tokens to consider for penalize (default: 64, 0 = disabled, -1 = ctx_size)', 'prefix': '--repeat-last-n'},
            {'name': 'Repeat Penalty', 'id': 'repeat-penalty', 'type': 'number', 'default': '1.0', 'description': 'Penalize repeat sequence of tokens (default: 1.0, 1.0 = disabled)', 'prefix': '--repeat-penalty'},
            {'name': 'Presence Penalty', 'id': 'presence-penalty', 'type': 'number', 'default': '0.0', 'description': 'Repeat alpha presence penalty (default: 0.0, 0.0 = disabled)', 'prefix': '--presence-penalty'},
            {'name': 'Frequency Penalty', 'id': 'frequency-penalty', 'type': 'number', 'default': '0.0', 'description': 'Repeat alpha frequency penalty (default: 0.0, 0.0 = disabled)', 'prefix': '--frequency-penalty'},
            {'name': 'DRY Multiplier', 'id': 'dry-multiplier', 'type': 'number', 'default': '0.0', 'description': 'Set DRY sampling multiplier (default: 0.0, 0.0 = disabled)', 'prefix': '--dry-multiplier'},
            {'name': 'DRY Base', 'id': 'dry-base', 'type': 'number', 'default': '1.75', 'description': 'Set DRY sampling base value (default: 1.75)', 'prefix': '--dry-base'},
            {'name': 'DRY Allowed Length', 'id': 'dry-allowed-length', 'type': 'number', 'default': '2', 'description': 'Set allowed length for DRY sampling (default: 2)', 'prefix': '--dry-allowed-length'},
            {'name': 'DRY Penalty Last N', 'id': 'dry-penalty-last-n', 'type': 'number', 'default': '-1', 'description': 'Set DRY penalty for the last n tokens (default: -1, 0 = disable, -1 = context size)', 'prefix': '--dry-penalty-last-n'},
            {'name': 'DRY Sequence Breaker', 'id': 'dry-sequence-breaker', 'type': 'text', 'default': '', 'description': "Add sequence breaker for DRY sampling, clearing out default breakers ('\\n', ':', '\"', '*')", 'prefix': '--dry-sequence-breaker'},
            {'name': 'Dynatemp Range', 'id': 'dynatemp-range', 'type': 'number', 'default': '0.0', 'description': 'Dynamic temperature range (default: 0.0, 0.0 = disabled)', 'prefix': '--dynatemp-range'},
            {'name': 'Dynatemp Exp', 'id': 'dynatemp-exp', 'type': 'number', 'default': '1.0', 'description': 'Dynamic temperature exponent (default: 1.0)', 'prefix': '--dynatemp-exp'},
            {'name': 'Mirostat', 'id': 'mirostat', 'type': 'number', 'default': '0', 'description': 'Use Mirostat sampling (Top K, Nucleus and Locally Typical samplers are ignored if used) (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0)', 'prefix': '--mirostat'},
            {'name': 'Mirostat LR', 'id': 'mirostat-lr', 'type': 'number', 'default': '0.1', 'description': 'Mirostat learning rate, parameter eta (default: 0.1)', 'prefix': '--mirostat-lr'},
            {'name': 'Mirostat Ent', 'id': 'mirostat-ent', 'type': 'number', 'default': '5.0', 'description': 'Mirostat target entropy, parameter tau (default: 5.0)', 'prefix': '--mirostat-ent'},
            {'name': 'Logit Bias', 'id': 'logit-bias', 'type': 'text', 'default': '', 'description': "Modifies the likelihood of token appearing in the completion. Example: --logit-bias 15043+1 to increase likelihood of token ' Hello', --logit-bias 15043-1 to decrease likelihood of token ' Hello'", 'prefix': '-l'},
            {'name': 'Grammar', 'id': 'grammar', 'type': 'text', 'default': '', 'description': "BNF-like grammar to constrain generations (see samples in grammars/ dir) (default: '')", 'prefix': '--grammar'},
            {'name': 'Grammar File', 'id': 'grammar-file', 'type': 'text', 'default': '', 'description': 'File to read grammar from', 'prefix': '--grammar-file'},
            {'name': 'JSON Schema', 'id': 'json-schema', 'type': 'text', 'default': '', 'description': 'JSON schema to constrain generations (https://json-schema.org/). Example: {} for any JSON object. For schemas w/ external $refs, use --grammar + example/json_schema_to_grammar.py instead', 'prefix': '-j'},
            {'name': 'JSON Schema File', 'id': 'json-schema-file', 'type': 'text', 'default': '', 'description': 'File containing a JSON schema to constrain generations. For schemas w/ external $refs, use --grammar + example/json_schema_to_grammar.py instead', 'prefix': '-jf'},
        ]
    },
    {
        "name": "Inference & Text Generation",
        "collapsed": True,
        "parameters": [
            {'name': 'SWA Checkpoints', 'id': 'swa-checkpoints', 'type': 'number', 'default': '3', 'description': 'Max number of SWA checkpoints per slot to create (default: 3). Environment variable: LLAMA_ARG_SWA_CHECKPOINTS', 'prefix': '--swa-checkpoints'},
            {'name': 'Context Shift', 'id': 'context-shift', 'type': 'select', 'default': 'disabled', 'options': ['enabled', 'disabled'], 'description': 'Enables context shift on infinite text generation (default: enabled). Environment variable: LLAMA_ARG_CONTEXT_SHIFT', 'prefix': '--context-shift'},
            {'name': 'Reverse Prompt', 'id': 'reverse-prompt', 'type': 'text', 'default': '', 'description': 'Halt generation at PROMPT, return control in interactive mode', 'prefix': '-r'},
            {'name': 'Special', 'id': 'special', 'type': 'checkbox', 'default': False, 'description': 'Special tokens output enabled (default: false)', 'prefix': '-sp'},
            {'name': 'No Warmup', 'id': 'no-warmup', 'type': 'checkbox', 'default': False, 'description': 'Skip warming up the model with an empty run', 'prefix': '--no-warmup'},
            {'name': 'SPM Infill', 'id': 'spm-infill', 'type': 'checkbox', 'default': False, 'description': 'Use Suffix/Prefix/Middle pattern for infill (instead of Prefix/Suffix/Middle) (default: disabled)', 'prefix': '--spm-infill'},
            {'name': 'Pooling', 'id': 'pooling', 'type': 'select', 'default': '', 'options': ['', 'none', 'mean', 'cls', 'last', 'rank'], 'description': 'Pooling type for embeddings, use model default if unspecified. Environment variable: LLAMA_ARG_POOLING', 'prefix': '--pooling'},
            {'name': 'Cont Batching', 'id': 'cont-batching', 'type': 'select', 'default': 'enabled', 'options': ['enabled', 'disabled'], 'description': 'Enable continuous batching (a.k.a dynamic batching) (default: enabled). Environment variable: LLAMA_ARG_CONT_BATCHING', 'prefix': '-cb'},
        ]
    },
    {
        "name": "Multimodal Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'MMProj', 'id': 'mmproj', 'type': 'text', 'default': '', 'description': 'Path to a multimodal projector file. see tools/mtmd/README.md. Note: if -hf is used, this argument can be omitted. Environment variable: LLAMA_ARG_MMPROJ', 'prefix': '--mmproj'},
            {'name': 'MMProj URL', 'id': 'mmproj-url', 'type': 'text', 'default': '', 'description': 'URL to a multimodal projector file. Environment variable: LLAMA_ARG_MMPROJ_URL', 'prefix': '--mmproj-url'},
            {'name': 'No MMProj', 'id': 'no-mmproj', 'type': 'checkbox', 'default': False, 'description': 'Explicitly disable multimodal projector, useful when using -hf. Environment variable: LLAMA_ARG_NO_MMPROJ', 'prefix': '--no-mmproj'},
            {'name': 'No MMProj Offload', 'id': 'no-mmproj-offload', 'type': 'checkbox', 'default': False, 'description': 'Do not offload multimodal projector to GPU. Environment variable: LLAMA_ARG_NO_MMPROJ_OFFLOAD', 'prefix': '--no-mmproj-offload'},
            {'name': 'HF Repo V', 'id': 'hf-repo-v', 'type': 'text', 'default': '', 'description': 'Hugging Face model repository for the vocoder model. Environment variable: LLAMA_ARG_HF_REPO_V', 'prefix': '-hfv'},
            {'name': 'HF File V', 'id': 'hf-file-v', 'type': 'text', 'default': '', 'description': 'Hugging Face model file for the vocoder model. Environment variable: LLAMA_ARG_HF_FILE_V', 'prefix': '-hffv'},
            {'name': 'Model Vocoder', 'id': 'model-vocoder', 'type': 'text', 'default': '', 'description': 'Vocoder model for audio generation (default: unused)', 'prefix': '-mv'},
            {'name': 'TTS Use Guide Tokens', 'id': 'tts-use-guide-tokens', 'type': 'checkbox', 'default': False, 'description': 'Use guide tokens to improve TTS word recall', 'prefix': '--tts-use-guide-tokens'},
        ]
    },
    {
        "name": "Speculative Decoding Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Override Tensor Draft', 'id': 'override-tensor-draft', 'type': 'text', 'default': '', 'description': 'Override tensor buffer type for draft model', 'prefix': '-otd'},
            {'name': 'CPU MoE Draft', 'id': 'cpu-moe-draft', 'type': 'checkbox', 'default': False, 'description': 'Keep all Mixture of Experts (MoE) weights in the CPU for the draft model. Environment variable: LLAMA_ARG_CPU_MOE_DRAFT', 'prefix': '-cmoed'},
            {'name': 'N CPU MoE Draft', 'id': 'n-cpu-moe-draft', 'type': 'number', 'default': '0', 'description': 'Keep the Mixture of Experts (MoE) weights of the first N layers in the CPU for the draft model. Environment variable: LLAMA_ARG_N_CPU_MOE_DRAFT', 'prefix': '-ncmoed'},
            {'name': 'Threads Draft', 'id': 'threads-draft', 'type': 'number', 'default': '-1', 'description': 'Number of threads to use during generation (default: same as --threads)', 'prefix': '-td'},
            {'name': 'Threads Batch Draft', 'id': 'threads-batch-draft', 'type': 'number', 'default': '-1', 'description': 'Number of threads to use during batch and prompt processing (default: same as --threads-draft)', 'prefix': '-tbd'},
            {'name': 'Draft Max', 'id': 'draft-max', 'type': 'number', 'default': '16', 'description': 'Number of tokens to draft for speculative decoding (default: 16). Environment variable: LLAMA_ARG_DRAFT_MAX', 'prefix': '--draft'},
            {'name': 'Draft Min', 'id': 'draft-min', 'type': 'number', 'default': '0', 'description': 'Minimum number of draft tokens to use for speculative decoding (default: 0). Environment variable: LLAMA_ARG_DRAFT_MIN', 'prefix': '--draft-min'},
            {'name': 'Draft P Min', 'id': 'draft-p-min', 'type': 'number', 'default': '0.8', 'description': 'Minimum speculative decoding probability (greedy) (default: 0.8). Environment variable: LLAMA_ARG_DRAFT_P_MIN', 'prefix': '--draft-p-min'},
            {'name': 'Context Size Draft', 'id': 'ctx-size-draft', 'type': 'number', 'default': '0', 'description': 'Size of the prompt context for the draft model (default: 0, 0 = loaded from model). Environment variable: LLAMA_ARG_CTX_SIZE_DRAFT', 'prefix': '-cd'},
            {'name': 'Device Draft', 'id': 'device-draft', 'type': 'text', 'default': '', 'description': 'Comma-separated list of devices to use for offloading the draft model. Use --list-devices to see a list of available devices', 'prefix': '-devd'},
            {'name': 'GPU Layers Draft', 'id': 'gpu-layers-draft', 'type': 'number', 'default': '0', 'description': 'Number of layers to store in VRAM for the draft model. Environment variable: LLAMA_ARG_N_GPU_LAYERS_DRAFT', 'prefix': '-ngld'},
            {'name': 'Model Draft', 'id': 'model-draft', 'type': 'text', 'default': '', 'description': 'Draft model for speculative decoding (default: unused). Environment variable: LLAMA_ARG_MODEL_DRAFT', 'prefix': '-md'},
            {'name': 'Spec Replace', 'id': 'spec-replace', 'type': 'text', 'default': '', 'description': 'Translate the string in TARGET into DRAFT if the draft model and main model are not compatible. Format: TARGET DRAFT', 'prefix': '--spec-replace'},
            {'name': 'Cache Type K Draft', 'id': 'cache-type-k-draft', 'type': 'select', 'default': 'f16', 'options': ['f32', 'f16', 'bf16', 'q8_0', 'q4_0', 'q4_1', 'iq4_nl', 'q5_0', 'q5_1'], 'description': 'KV cache data type for K for the draft model (default: f16). Environment variable: LLAMA_ARG_CACHE_TYPE_K_DRAFT', 'prefix': '-ctkd'},
            {'name': 'Cache Type V Draft', 'id': 'cache-type-v-draft', 'type': 'select', 'default': 'f16', 'options': ['f32', 'f16', 'bf16', 'q8_0', 'q4_0', 'q4_1', 'iq4_nl', 'q5_0', 'q5_1'], 'description': 'KV cache data type for V for the draft model (default: f16). Environment variable: LLAMA_ARG_CACHE_TYPE_V_DRAFT', 'prefix': '-ctvd'},
        ]
    },
    {
        "name": "Server Parameters",
        "collapsed": True,
        "parameters": [
            {'name': 'Alias', 'id': 'alias', 'type': 'text', 'default': '', 'description': 'Set alias for model name (to be used by REST API). Environment variable: LLAMA_ARG_ALIAS', 'prefix': '-a'},
            {'name': 'Host', 'id': 'host', 'type': 'text', 'default': '127.0.0.1', 'description': 'IP address to listen, or bind to an UNIX socket if the address ends with .sock (default: 127.0.0.1). Environment variable: LLAMA_ARG_HOST', 'prefix': '--host'},
            {'name': 'Port', 'id': 'port', 'type': 'number', 'default': '8080', 'description': 'Port to listen (default: 8080). Environment variable: LLAMA_ARG_PORT', 'prefix': '--port'},
            {'name': 'Path', 'id': 'path', 'type': 'text', 'default': '', 'description': 'Path to serve static files from (default: ). Environment variable: LLAMA_ARG_STATIC_PATH', 'prefix': '--path'},
            {'name': 'API Prefix', 'id': 'api-prefix', 'type': 'text', 'default': '', 'description': 'Prefix path the server serves from, without the trailing slash (default: ). Environment variable: LLAMA_ARG_API_PREFIX', 'prefix': '--api-prefix'},
            {'name': 'No WebUI', 'id': 'no-webui', 'type': 'checkbox', 'default': False, 'description': 'Disable the Web UI (default: enabled). Environment variable: LLAMA_ARG_NO_WEBUI', 'prefix': '--no-webui'},
            {'name': 'Embeddings', 'id': 'embeddings', 'type': 'checkbox', 'default': False, 'description': 'Restrict to only support embedding use case; use only with dedicated embedding models (default: disabled). Environment variable: LLAMA_ARG_EMBEDDINGS', 'prefix': '--embeddings'},
            {'name': 'Reranking', 'id': 'reranking', 'type': 'checkbox', 'default': False, 'description': 'Enable reranking endpoint on server (default: disabled). Environment variable: LLAMA_ARG_RERANKING', 'prefix': '--reranking'},
            {'name': 'API Key', 'id': 'api-key', 'type': 'text', 'default': '', 'description': 'API key to use for authentication (default: none). Environment variable: LLAMA_API_KEY', 'prefix': '--api-key'},
            {'name': 'API Key File', 'id': 'api-key-file', 'type': 'text', 'default': '', 'description': 'Path to file containing API keys (default: none)', 'prefix': '--api-key-file'},
            {'name': 'SSL Key File', 'id': 'ssl-key-file', 'type': 'text', 'default': '', 'description': 'Path to file a PEM-encoded SSL private key. Environment variable: LLAMA_ARG_SSL_KEY_FILE', 'prefix': '--ssl-key-file'},
            {'name': 'SSL Cert File', 'id': 'ssl-cert-file', 'type': 'text', 'default': '', 'description': 'Path to file a PEM-encoded SSL certificate. Environment variable: LLAMA_ARG_SSL_CERT_FILE', 'prefix': '--ssl-cert-file'},
            {'name': 'Chat Template Kwargs', 'id': 'chat-template-kwargs', 'type': 'text', 'default': '', 'description': 'Sets additional params for the json template parser. Environment variable: LLAMA_CHAT_TEMPLATE_KWARGS', 'prefix': '--chat-template-kwargs'},
            {'name': 'Timeout', 'id': 'timeout', 'type': 'number', 'default': '600', 'description': 'Server read/write timeout in seconds (default: 600). Environment variable: LLAMA_ARG_TIMEOUT', 'prefix': '-to'},
            {'name': 'Threads HTTP', 'id': 'threads-http', 'type': 'number', 'default': '-1', 'description': 'Number of threads used to process HTTP requests (default: -1). Environment variable: LLAMA_ARG_THREADS_HTTP', 'prefix': '--threads-http'},
            {'name': 'Cache Reuse', 'id': 'cache-reuse', 'type': 'number', 'default': '0', 'description': 'Min chunk size to attempt reusing from the cache via KV shifting (default: 0). Environment variable: LLAMA_ARG_CACHE_REUSE', 'prefix': '--cache-reuse'},
            {'name': 'Metrics', 'id': 'metrics', 'type': 'checkbox', 'default': False, 'description': 'Enable prometheus compatible metrics endpoint (default: disabled). Environment variable: LLAMA_ARG_ENDPOINT_METRICS', 'prefix': '--metrics'},
            {'name': 'Props', 'id': 'props', 'type': 'checkbox', 'default': False, 'description': 'Enable changing global properties via POST /props (default: disabled). Environment variable: LLAMA_ARG_ENDPOINT_PROPS', 'prefix': '--props'},
            {'name': 'Slots', 'id': 'slots', 'type': 'select', 'default': 'enabled', 'options': ['enabled', 'disabled'], 'description': 'Enable slots monitoring endpoint (default: enabled). Environment variable: LLAMA_ARG_ENDPOINT_SLOTS', 'prefix': '--slots'},
            {'name': 'Slot Save Path', 'id': 'slot-save-path', 'type': 'text', 'default': '', 'description': 'Path to save slot kv cache (default: disabled)', 'prefix': '--slot-save-path'},
            {'name': 'Jinja', 'id': 'jinja', 'type': 'checkbox', 'default': False, 'description': 'Use jinja template for chat (default: disabled). Environment variable: LLAMA_ARG_JINJA', 'prefix': '--jinja'},
            {'name': 'Reasoning Format', 'id': 'reasoning-format', 'type': 'select', 'default': 'deepseek', 'options': ['none', 'deepseek', 'deepseek-legacy'], 'description': 'Controls whether thought tags are allowed and/or extracted from the response. Options: none, deepseek, deepseek-legacy (default: deepseek). Environment variable: LLAMA_ARG_THINK', 'prefix': '--reasoning-format'},
            {'name': 'Reasoning Budget', 'id': 'reasoning-budget', 'type': 'number', 'default': '-1', 'description': 'Controls the amount of thinking allowed (-1 for unrestricted, 0 to disable) (default: -1). Environment variable: LLAMA_ARG_THINK_BUDGET', 'prefix': '--reasoning-budget'},
            {'name': 'Chat Template', 'id': 'chat-template', 'type': 'select', 'default': '', 'options': ['', 'bailing', 'chatglm3', 'chatglm4', 'chatml', 'command-r', 'deepseek', 'deepseek2', 'deepseek3', 'exaone3', 'exaone4', 'falcon3', 'gemma', 'gigachat', 'glmedge', 'gpt-oss', 'granite', 'hunyuan-dense', 'hunyuan-moe', 'kimi-k2', 'llama2', 'llama2-sys', 'llama2-sys-bos', 'llama2-sys-strip', 'llama3', 'llama4', 'megrez', 'minicpm', 'mistral-v1', 'mistral-v3', 'mistral-v3-tekken', 'mistral-v7', 'mistral-v7-tekken', 'monarch', 'openchat', 'orion', 'phi3', 'phi4', 'rwkv-world', 'seed_oss', 'smolvlm', 'vicuna', 'vicuna-orca', 'yandex', 'zephyr'], 'description': "Set custom jinja chat template (default: template taken from model's metadata). Environment variable: LLAMA_ARG_CHAT_TEMPLATE", 'prefix': '--chat-template'},
            {'name': 'Chat Template File', 'id': 'chat-template-file', 'type': 'text', 'default': '', 'description': "Set custom jinja chat template file (default: template taken from model's metadata). Same built-in templates as --chat-template. Environment variable: LLAMA_ARG_CHAT_TEMPLATE_FILE", 'prefix': '--chat-template-file'},
            {'name': 'No Prefill Assistant', 'id': 'no-prefill-assistant', 'type': 'checkbox', 'default': False, 'description': "Whether to prefill the assistant's response if the last message is an assistant message (default: prefill enabled). When set, if the last message is an assistant message then it will be treated as a full message and not prefilled. Environment variable: LLAMA_ARG_NO_PREFILL_ASSISTANT", 'prefix': '--no-prefill-assistant'},
            {'name': 'Slot Prompt Similarity', 'id': 'slot-prompt-similarity', 'type': 'number', 'default': '0.50', 'description': 'How much the prompt of a request must match the prompt of a slot to use that slot (default: 0.50, 0.0 = disabled)', 'prefix': '-sps'},
            {'name': 'LoRA Init Without Apply', 'id': 'lora-init-without-apply', 'type': 'checkbox', 'default': False, 'description': 'Load LoRA adapters without applying them (apply later via POST /lora-adapters) (default: disabled)', 'prefix': '--lora-init-without-apply'},
        ]
    },
    {
        "name": "Pre-configured Model Shortcuts",
        "collapsed": True,
        "parameters": [
            {'name': 'Embed BGE Small EN Default', 'id': 'embd-bge-small-en-default', 'type': 'checkbox', 'default': False, 'description': 'Use default bge-small-en-v1.5 model (note: can download weights from the internet)', 'prefix': '--embd-bge-small-en-default'},
            {'name': 'Embed E5 Small EN Default', 'id': 'embd-e5-small-en-default', 'type': 'checkbox', 'default': False, 'description': 'Use default e5-small-v2 model (note: can download weights from the internet)', 'prefix': '--embd-e5-small-en-default'},
            {'name': 'Embed GTE Small Default', 'id': 'embd-gte-small-default', 'type': 'checkbox', 'default': False, 'description': 'Use default gte-small model (note: can download weights from the internet)', 'prefix': '--embd-gte-small-default'},
            {'name': 'FIM Qwen 1.5B Default', 'id': 'fim-qwen-1.5b-default', 'type': 'checkbox', 'default': False, 'description': 'Use default Qwen 2.5 Coder 1.5B (note: can download weights from the internet)', 'prefix': '--fim-qwen-1.5b-default'},
            {'name': 'FIM Qwen 3B Default', 'id': 'fim-qwen-3b-default', 'type': 'checkbox', 'default': False, 'description': 'Use default Qwen 2.5 Coder 3B (note: can download weights from the internet)', 'prefix': '--fim-qwen-3b-default'},
            {'name': 'FIM Qwen 7B Default', 'id': 'fim-qwen-7b-default', 'type': 'checkbox', 'default': False, 'description': 'Use default Qwen 2.5 Coder 7B (note: can download weights from the internet)', 'prefix': '--fim-qwen-7b-default'},
            {'name': 'FIM Qwen 7B Spec', 'id': 'fim-qwen-7b-spec', 'type': 'checkbox', 'default': False, 'description': 'Use Qwen 2.5 Coder 7B + 0.5B draft for speculative decoding (note: can download weights from the internet)', 'prefix': '--fim-qwen-7b-spec'},
            {'name': 'FIM Qwen 14B Spec', 'id': 'fim-qwen-14b-spec', 'type': 'checkbox', 'default': False, 'description': 'Use Qwen 2.5 Coder 14B + 0.5B draft for speculative decoding (note: can download weights from the internet)', 'prefix': '--fim-qwen-14b-spec'},
            {'name': 'FIM Qwen 30B Default', 'id': 'fim-qwen-30b-default', 'type': 'checkbox', 'default': False, 'description': 'Use default Qwen 3 Coder 30B A3B Instruct (note: can download weights from the internet)', 'prefix': '--fim-qwen-30b-default'},
        ]
    }
]

BENCHMARK_PROMPT = '''
                **Task:**  
Create a ranked list of the provided LLM models from **fastest to slowest** based on their reported **tokens per second (t/s)**.  

**Persona:**  
You are an expert LLM performance analyst.  

**Output Format:**  
Present the results as a **markdown table** with the following columns, preserving **all characteristics** exactly as given:

| Rank | Model Name | Storage Size | CUDA Version | Context Length | Offload Type | CPU Thread Pool Size | Evaluation Batch Size | Offload KV Cache | Flash Attention | K‑Cache Quantized | V‑Cache Quantized | Tokens per Second |
|------|------------|--------------|--------------|----------------|--------------|----------------------|-----------------------|------------------|-----------------|-------------------|-------------------|--------------------|

- **Rank 1** should be the model with the highest t/s, **Rank N** the lowest.  
- If two models have identical t/s, order them alphabetically by model name.  
- For models lacking a specific attribute (e.g., K‑Cache or V‑Cache Quantized, Offload KV Cache), the corresponding table cell should be left blank.


**Constraints & Guidance:**  
- Include **every** model and **all** listed attributes; do not omit or modify any values.  
- Explicitly state “Verified: all entries sorted correctly by tokens per second.” at the end of the table.  
- If any required information is ambiguous or missing, note it in a separate “Assumptions / Issues” section below the table.  

---  

*Paste the raw model list (as in the original prompt) below this line before running the LLM.* 

```
mistral-small-3.2-24b-instruct-2506 Q6_K_XL - 22.54 GB - cuda 12 - 45k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 41t/s
Qwen3-32B-UD-Q4_K_XL - 20.02 GB - cuda 12 - 35k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 39t/s
Qwen3-Nemotron-32B-RLBFF.i1-Q4_K_M - 19.76 GB - cuda 12 - 30k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 30t/s
Qwen3-VL-32B-Instruct.Q4_K_M_TEXT - 20.96 GB - cuda 12 - 30k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 35t/s
Qwen3-VL-32B-Instruct.Q4_K_M_TEXT_DRAFT - 20.96 GB - cuda 12 - 30k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 50t/s
Qwen3-VL-32B-Thinking.Q4_K_M_TEXT_DRAFT - 20.96 GB - cuda 12 - 15k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 35t/s
Qwen3-VL-32B-Instruct.Q6_K_TEXT_DRAFT - 28.08 GB - cuda 12 - 15k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 37t/s
Qwen3-VL-32B-Instruct.Q4_K_M_VL - 20.96 GB - cuda 12 - 17k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 37t/s
Llama-3.3-70B-Instruct-UD-IQ3_XXS - 27.66 GB - cuda 12 - 10k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - speculative decoding 1b - 20t/s
gemma-3-27b-it-UD-Q6_K_XL - 25.41 GB - cuda - 130k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 25t/s
Qwen3-14B-128K-UD-Q8_K_XL - 18.75 GB - cuda 12 - 80k ctx - full offload - 8 - 2048 - offload kv checked - flash - kcache - vcache - 48t/s
nvidia_llama-3_3-nemotron-super-49b-v1_5 - 28.63 GB - cuda 12 - 31k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 21t/s
qwen3-30b-a3b-instruct-2507@q4_k_m - 18.56 GB - cuda 12 - 110k ctx - full offload - 8 - 2048 - offload kv checked - flash - 136t/s
GLM-Z1-32B-0414-Q4_K_M - 19.68 GB - cuda 12 - 32k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 40t/s
UIGEN-X-32B-0727.Q4_K_M - 19.76 GB - cuda 12 - 19k ctx - full offload - 8 - 512- offload kv checked - flash - 39t/s
gemma-3-27b-it-qat-UD-Q4_K_XL - 18.51 GB - cuda 12 - 131k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 42t/s
gpt-oss-20b-MXFP4 - 12.11 GB - cuda 12 - 131k ctx - full offload - 8 - 2048 - offload kv checked - flash -  170t/s
Devstral-Small-2507-Q6_K - 19.35 GB - cuda 12 - 64k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 39t/s
GLM-4.5-Air-UD-Q3_K_XL - 57.73 GB - cuda 12 - 27k ctx - 19/47 layer offload to gpu - 8 - 512 - flash - kcache - vcache - 7t/s
Qwen3-Coder-30B-A3B-Instruct-UD-Q6_K_XL - 26.34 GB - cuda 12 - 75k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache- 79t/s
Seed-OSS-36B-Instruct-UD-Q4_K_XL - 22.03 GB - cuda 12 - 21k ctx - full offload - 8 - 512 - offload kv checked - flash  - kcache - vcache - 35t/s
Magistral-Small-2509-UD-Q5_K_XL - 18.52 GB - cuda 12 - 85k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache - 42t/s
gpt-oss-120b-MXFP4 - 63.39 GB - cuda 12 - 45k ctx - 16/36 layer offload to gpu - 8 - 512 - flash - kcache - vcache - 9t/s
Qwen3-VL-30B-A3B-Instruct-UD-Q4_K_XL_TEXT - 19.87 GB - cuda 12 - 70k ctx - full offload - 8 - 512 - offload kv checked - flash - kcache - vcache- 133t/s
```
'''
