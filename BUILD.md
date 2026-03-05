# Building HSR-Scanner

This project uses **PyInstaller** to package the Python source code into a standalone Windows executable.

## Prerequisites

1.  **Windows OS:** Compilation must be performed on a Windows machine.
2.  **Python 3.10+:** Ensure Python is installed and added to your PATH.
3.  **Tesseract:** The build process bundles the `tesseract.exe` found in `src/assets/tesseract/`.

## Build Steps

1.  **Open a terminal** (PowerShell or CMD) in the project root directory.
2.  **Install dependencies:**
    ```powershell
    pip install -r requirements.txt
    pip install pyinstaller
    ```
3.  **Run the build:**
    ```powershell
    pyinstaller --noconfirm HSR-Scanner.spec
    ```

## Output

-   The compiled executable `HSR-Scanner.exe` will be generated in the `dist/` folder.
-   The application is configured to requested Administrator privileges (`uac_admin=True`), which is necessary for simulating mouse and keyboard inputs in-game.

## Troubleshooting

-   **Missing DLLs:** If the app fails to start, ensure the `src/assets/vgamepad/ViGEmClient.dll` is present, as it is required for controller emulation.
-   **Anti-virus:** PyInstaller executables are sometimes flagged as false positives. You may need to add the `dist/` folder to your exclusion list.
