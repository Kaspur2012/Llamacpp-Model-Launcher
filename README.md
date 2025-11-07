# Llamacpp-Model-Launcher
Its purpose is to replace the tedious and error-prone process of typing long commands into a terminal. With this launcher, you can manage, edit, delete, duplicate and run all your language models with the point-and-click simplicity of a modern desktop application. 

Side panel allows you to remove/add/edit/duplicate model parameters and run them easily. 

Command button opens a powerful, interactive UI for exploring and adding Llama.cpp parameters.

![Main_UI](https://github.com/Kaspur2012/Llamacpp-Model-Launcher/blob/main/Main_UI.PNG)



## Changes Log:
Nov 6 2025:

thanks to https://x.com/unmortan for the code/frameworks

https://www.reddit.com/r/LocalLLaMA/comments/1opx9k2/comment/nnf2gr9/?context=1

**✨ Features**
*   **New Interactive Parameter Browser**:
    The "Commands" button now opens a powerful, interactive UI for exploring and adding Llama.cpp parameters, replacing the previous static text view.
    Organized & Discoverable: Parameters are grouped into collapsible categories (e.g., "Sampling," "GPU," "Context") for easy navigation and discovery.
    Live Search: Instantly filter all available parameters by name, description, or command-line flag (e.g., --top-k). The search bar also includes a clear button for convenience.
    One-Click Add: Each parameter in the browser has its own "Add" button to instantly add it (with its value) to your currently selected model configuration in the Parameter Editor.
    
*   **📈 Improvements**
    Improved Workflow: The UI now remains in the Parameter Browser after adding a parameter, allowing you to add multiple parameters in a single session without interruption.
    External Parameter Database: The extensive list of Llama.cpp parameters has been moved to a separate parameters_db.py file, making the main application code significantly cleaner and easier to manage.
    
**🐛 Bug Fixes**
*   Fixed a critical bug where deleting a parameter from a long, scrollable list (especially with duplicate parameter names like -ot) would remove the wrong entry.
    Resolved a startup issue where the Parameter Editor would be empty for the first model selected when the application launched.
    Fixed an issue where the --mmproj parameter incorrectly opened a directory browser instead of a file browser.
    Added a confirmation dialog for unsaved changes when exiting the application to prevent accidental data loss.

Nov 1 2025:
*   **updated model_commands_short.txt to have more model specially qwen3 vl models.**

*   **Added `--mmproj` Parameter Functionality**:
    *   The parameter editor now recognizes `--mmproj` and adds a "Browse..." button next to its text field.
    *   This button opens a file dialog to let you select the correct model projection file.

*   **Added Unsaved Changes Check on Exit**:
    *   If you have unsaved changes in the parameter editor and try to close the application, a popup will now appear asking if you want to save, discard, or cancel.

*   **Fixed Initial Model Loading Bug**:
    *   Corrected an issue where the parameter editor would be empty on startup for the first model in the list. The editor now correctly populates when the application first launches.

*   **Fixed Parameter Deletion Bug**:
    *   Resolved a critical bug where clicking the "X" button on a parameter in a long, scrollable list (especially with duplicate parameter names) would delete the wrong entry. Deleting a parameter now reliably removes the correct row.



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
parameters_db.py and models_commands.txt MUST be in the same directory as your Model file(eg. model_commands_short.txt) directory.
