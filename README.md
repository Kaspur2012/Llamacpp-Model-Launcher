Llamacpp-Model-Launcher

The Llamacpp-Model-Launcher is a desktop application designed to simplify the process of managing and running your language models. It replaces the need for typing lengthy and complex commands into a terminal with an intuitive, point-and-click interface. You can easily manage, edit, delete, duplicate, and run all your language models.

Please Note: This application was developed for Windows and has not been tested on other operating systems.

![alt text](https://github.com/Kaspur2012/Llamacpp-Model-Launcher/blob/main/Main_UI.PNG)

Features
<details>
<summary><strong>✅ Core Functionality & Model Management</strong></summary>


Graphical Front-End: A robust and intuitive GUI for managing and launching llama-server.exe instances.

One-Click Model Loading: Load and unload models with a single click, eliminating manual command-line work.

Centralized Dashboard: Manage all your model configurations from a single, organized interface.

Add, Duplicate, Delete: Easily create new configurations from a template, duplicate existing ones to experiment, or delete them safely with a confirmation prompt.

Save to File: All changes are saved to your models.txt file, keeping your configurations portable and easy to back up.

Reset Changes: Instantly discard any unsaved modifications and revert to the last saved state.

</details>

<details>
<summary><strong>⚙️ Powerful Parameter Editing & Discovery</strong></summary>


Interactive Parameter Browser: A built-in, searchable library of Llama.cpp parameters, complete with descriptions and organized into collapsible categories (e.g., Sampling, GPU, Context).

One-Click Parameter Addition: Add parameters from the browser to your model with a single click.

Live Search & Filtering: Instantly find parameters by name, description, or command-line flag (e.g., --top-k).

Dynamic Parameter Editor: The editor automatically provides the right tool for each parameter, including text fields, checkboxes, and dropdown menus.

Integrated File Browsers: Convenient "Browse..." buttons for path-based parameters like --model and --mmproj.

Smart Duplicate Handling: The app intelligently handles parameters that can be used multiple times (like -ot) by asking for confirmation first.

</details>

<details>
<summary><strong>🖥️ Process Management & User Experience</strong></summary>


Responsive, Non-Blocking UI: The application remains fully responsive while models are loading or running.

Real-Time Server Output: View the live, scrolling output from the llama-server.exe process directly within the app.

Clear Status Indicator: A color-coded status indicator shows the server's state at a glance (Loaded, Unloaded, Loading, or Error).

Auto-Open Web UI: Optionally, automatically launch the Llama.cpp web interface in your browser once the server is ready.

Unsaved Changes Prompts: Prevents accidental data loss by prompting you to save changes before switching models or exiting.

Persistent Path Configuration: Your Llama.cpp directory and models file paths are saved and loaded automatically on startup.

Path Validation: The UI gives instant visual feedback if configured paths are invalid.

Clean and Modern UI: A dark-themed, user-friendly interface designed for clarity and ease of use.

</details>



## Running the Application

There are two primary ways to run this application:

#### Method 1: Run from Python Source

This method is ideal for developers or users who have Python installed and are comfortable with a code editor.

1.  **Install Dependencies**: The application requires the PyQt6 library. Install it using pip:
    ```bash
    pip install PyQt6
    ```
2.  **Run the Script**: Save the application code as a Python file (e.g., `launcher.py`) and run it from your terminal or preferred code editor.

#### Method 2: Compile to a Standalone Executable (.exe)
I have uploaded the latest exe file but it is highly recommended you build it yourself.

This method packages the application into a single `.exe` file that can be run on any Windows machine without needing Python installed.

1.  **Install PyInstaller**: This module handles the compilation process. Install it using pip:
    ```bash
    pip install pyinstaller
    ```
2.  **Run the Command**: Open a terminal in the directory where you saved the Python script. Run the following command:
    ```bash
    pyinstaller --onefile --windowed --icon=C:\path\to\your\icon.ico your_script_name.py
    ```
    *   `--onefile`: Packages everything into a single executable file.
    *   `--windowed`: Prevents a console window from appearing when you run the app.
    *   `--icon`: (Optional) Sets a custom icon for the executable. You can omit this flag if you don't have an `.ico` file.

After the command completes, you will find your standalone `.exe` file inside a new `dist` folder.


## File Structure
*   all files must in the same directory.
