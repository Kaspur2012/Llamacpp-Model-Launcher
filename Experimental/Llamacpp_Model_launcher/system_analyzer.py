# system_analyzer.py

import os
import re
import subprocess
import platform

# --- Optional Dependencies ---
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pynvml
    PYNVML_AVAILABLE = True
    # --- FIX: REMOVED pynvml.nvmlInit() from module level ---
except ImportError:
    PYNVML_AVAILABLE = False
except Exception as e:
    # Handle cases where NVML might be present but fails to init (e.g., driver issues)
    print(f"[ANALYZER WARNING] pynvml could not be imported: {e}")
    PYNVML_AVAILABLE = False


# --- NEW: Centralized lifecycle management functions ---
def initialize_pynvml():
    """Initializes the NVML library. To be called once at app start."""
    global PYNVML_AVAILABLE
    if PYNVML_AVAILABLE:
        try:
            pynvml.nvmlInit()
            print("[HARDWARE] PYNVML Initialized successfully.")
        except Exception as e:
            print(f"[ANALYZER WARNING] pynvml initialization failed: {e}")
            PYNVML_AVAILABLE = False

def shutdown_pynvml():
    """Shuts down the NVML library. To be called once at app exit."""
    global PYNVML_AVAILABLE
    # Check if the module was imported and our flag is still true
    if 'pynvml' in globals() and PYNVML_AVAILABLE:
        try:
            pynvml.nvmlShutdown()
            print("[HARDWARE] PYNVML Shutdown successfully.")
        except Exception as e:
            print(f"[ANALYZER WARNING] pynvml shutdown failed: {e}")
# --- END NEW ---


class SystemAnalyzer:
    """
    A class to probe the user's system for hardware specs and analyze a GGUF model file.
    Designed to be used as a generator to provide real-time feedback.
    """
    def __init__(self):
        self.results = {
            "cpu_physical_cores": None,
            "cpu_logical_cores": None,
            "ram": {},
            "gpus": [],
            "model_size_gb": None,
            "model_architecture": "Unknown",
        }

    def _get_cpu_info(self):
        """Gets CPU core count."""
        yield "[ANALYSIS] Probing for CPU and RAM details..."
        if PSUTIL_AVAILABLE:
            self.results["cpu_logical_cores"] = psutil.cpu_count(logical=True)
            self.results["cpu_physical_cores"] = psutil.cpu_count(logical=False)
            yield f"> Found {self.results['cpu_physical_cores']} physical and {self.results['cpu_logical_cores']} logical CPU cores."
        else:
            self.results["cpu_logical_cores"] = os.cpu_count()
            yield f"> Found {self.results['cpu_logical_cores']} logical CPU cores (psutil not installed, physical count unavailable)."

    def _get_ram_info(self):
        """Gets total, used, and free system RAM."""
        if PSUTIL_AVAILABLE:
            ram_info = psutil.virtual_memory()
            total_gb = round(ram_info.total / (1024 ** 3), 2)
            used_gb = round(ram_info.used / (1024 ** 3), 2)
            free_gb = round(ram_info.available / (1024 ** 3), 2)
            self.results["ram"] = {"total_gb": total_gb, "used_gb": used_gb, "free_gb": free_gb}
            yield f"> Found {total_gb} GB of system RAM ({free_gb} GB available)."
        else:
            yield "> Could not determine system RAM (psutil library not installed)."

    def _get_gpu_info_pynvml(self):
        """Gets GPU info using the pynvml library (preferred for NVIDIA)."""
        # --- FIX: Removed nvmlInit() call. It is now managed globally. ---
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count == 0:
            yield "> pynvml found 0 NVIDIA GPUs."
            return

        yield f"> pynvml found {device_count} NVIDIA GPU(s)."
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            total_gb = round(mem_info.total / (1024 ** 3), 2)
            used_gb = round(mem_info.used / (1024 ** 3), 2)
            free_gb = round(mem_info.free / (1024 ** 3), 2)
            vram_details = {"total_gb": total_gb, "used_gb": used_gb, "free_gb": free_gb}
            self.results["gpus"].append({"id": i, "name": name.strip(), "vram": vram_details})
            yield f"  - GPU {i}: {name.strip()} ({total_gb} GB VRAM, {free_gb} GB free)"

    def _get_gpu_info_fallback(self):
        """Fallback method using nvidia-smi if pynvml is unavailable."""
        try:
            command = ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"]
            process = subprocess.run(command, capture_output=True, text=True, check=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            output = process.stdout.strip().split('\n')
            if not output or not output[0]:
                yield "> nvidia-smi found 0 NVIDIA GPUs."
                return

            yield f"> nvidia-smi found {len(output)} NVIDIA GPU(s)."
            for i, line in enumerate(output):
                name, vram_total_mib, vram_used_mib = line.split(',')
                total_gb = round(int(vram_total_mib.strip()) / 1024, 2)
                used_gb = round(int(vram_used_mib.strip()) / 1024, 2)
                free_gb = round(total_gb - used_gb, 2)
                vram_details = {"total_gb": total_gb, "used_gb": used_gb, "free_gb": free_gb}
                self.results["gpus"].append({"id": i, "name": name.strip(), "vram": vram_details})
                yield f"  - GPU {i}: {name.strip()} ({total_gb} GB VRAM, {free_gb} GB free)"

        except (FileNotFoundError, subprocess.CalledProcessError):
            yield "> nvidia-smi not found. Could not detect NVIDIA GPUs."
        except Exception as e:
            yield f"> An error occurred while running nvidia-smi: {e}"

    def _get_gpu_info(self):
        """Detects GPU information, preferring pynvml."""
        yield "[ANALYSIS] Probing for available GPUs and VRAM..."
        if platform.system() != "Windows":
            yield "> GPU detection is currently only supported on Windows."
            return

        if PYNVML_AVAILABLE:
            try:
                yield from self._get_gpu_info_pynvml()
            except Exception as e:
                yield f"> pynvml failed with an error: {e}. Trying fallback..."
                self.results["gpus"] = []
                yield from self._get_gpu_info_fallback()
        else:
            yield "> pynvml library not installed. Falling back to nvidia-smi..."
            yield from self._get_gpu_info_fallback()

        if not self.results["gpus"]:
            yield "> No compatible GPUs detected on the system."

    def _get_model_info(self, model_path):
        """Gets model file size and architecture from the model's filename."""
        yield f"[ANALYSIS] Accessing model file at: {model_path}..."
        try:
            filename = os.path.basename(model_path)
            directory = os.path.dirname(model_path)

            multi_part_pattern = re.compile(r'-\d{5}-of-\d{5}\.gguf$', re.IGNORECASE)

            if multi_part_pattern.search(filename):
                yield "> Multi-part model pattern detected. Calculating total size..."
                base_name = multi_part_pattern.split(filename)[0]
                total_size_bytes = 0
                part_count = 0

                if not os.path.isdir(directory):
                    yield f"> ERROR: Model directory not found at '{directory}'."
                    self.results["model_architecture"] = "Directory Not Found"
                    return

                for part_filename in os.listdir(directory):
                    if part_filename.lower().startswith(base_name.lower()) and part_filename.lower().endswith('.gguf'):
                        part_path = os.path.join(directory, part_filename)
                        try:
                            size = os.path.getsize(part_path)
                            total_size_bytes += size
                            part_count += 1
                            yield f"  - Found part: {part_filename} ({round(size / (1024 ** 3), 2)} GB)"
                        except FileNotFoundError:
                            yield f"  - Warning: Could not access part {part_filename}"

                self.results["model_size_gb"] = round(total_size_bytes / (1024 ** 3), 2)
                yield f"> Found {part_count} parts. Total model size is {self.results['model_size_gb']} GB."

            else:
                yield "> Single-file model detected."
                file_size_bytes = os.path.getsize(model_path)
                self.results["model_size_gb"] = round(file_size_bytes / (1024 ** 3), 2)
                yield f"> Model file size is {self.results['model_size_gb']} GB."

            yield "[ANALYSIS] Determining architecture from filename..."
            lower_filename = filename.lower()

            if ('moe' in lower_filename or
                    'mixture' in lower_filename or
                    'gpt-oss' in lower_filename or
                    re.search(r'a\d+b', lower_filename)):
                self.results["model_architecture"] = "Mixture of Experts (MoE)"
            else:
                self.results["model_architecture"] = "Dense"

            yield f"> Model architecture identified as: {self.results['model_architecture']}."

        except FileNotFoundError:
            yield f"> ERROR: Model file not found at '{model_path}'."
            self.results["model_architecture"] = "File Not Found"
        except Exception as e:
            yield f"> ERROR: Could not read model file. Reason: {e}"
            self.results["model_architecture"] = "Read Error"

    def get_live_vram_usage(self):
        """
        Gets the current VRAM usage for all NVIDIA GPUs using pynvml.
        Returns a dictionary or None if pynvml is not available or fails.
        """
        if not PYNVML_AVAILABLE:
            return None

        try:
            # --- FIX: Removed nvmlInit() call. ---
            device_count = pynvml.nvmlDeviceGetCount()
            vram_stats = {}
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                vram_stats[i] = {
                    "used_gb": round(mem_info.used / (1024 ** 3), 2),
                    "total_gb": round(mem_info.total / (1024 ** 3), 2)
                }
            return vram_stats
        except Exception as e:
            print(f"[ANALYZER ERROR] Could not get live VRAM usage: {e}")
            return None

    def run_analysis(self, model_path):
        """
        Runs the full system and model analysis process.
        This is a generator that yields status strings for live UI updates.
        """
        yield "[ANALYSIS STARTED]"
        yield from self._get_cpu_info()
        yield from self._get_ram_info()
        yield from self._get_gpu_info()
        if model_path:
            yield from self._get_model_info(model_path)
        else:
            yield "[ANALYSIS] Skipped model analysis because no path was provided."

        yield "[ANALYSIS COMPLETE]"
        return self.results