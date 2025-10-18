# Llamacpp-Model-Launcher
Its purpose is to replace the tedious and error-prone process of typing long commands into a terminal. With this launcher, you can manage, edit, delete, duplicate and run all your language models with the point-and-click simplicity of a modern desktop application.

![Main_UI](https://github.com/Kaspur2012/Llamacpp-Model-Launcher/blob/main/Main_UI.PNG)



### Running the Application

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


### File Structure
models_commands.txt MUST be in the same directory as your model files(eg. model_commands_short.txt) directory.
