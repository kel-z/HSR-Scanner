# HSR Scanner UI

This module contains the UI files for HSR Scanner.

The UI is made using Qt Designer 5.11.1 and the `hsr_scanner.ui` file can be opened in Qt Designer for editing.

To build the UI code, run the `build_ui.bat` file which contains the following command:
`pyuic6 -o hsr_scanner.py hsr_scanner.ui`

This command generates the `hsr_scanner.py` file from the `hsr_scanner.ui` file, which can then be hooked to the app in `main.py`.
