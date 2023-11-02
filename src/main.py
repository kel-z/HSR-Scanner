import asyncio
import datetime
from ui.hsr_scanner import Ui_MainWindow
from PyQt6 import QtCore, QtGui, QtWidgets
from services.scanner.scanner import HSRScanner
from enums.increment_type import IncrementType
from pynput.keyboard import Key, Listener
from utils.helpers import resource_path, save_to_json, executable_path
from models.game_data import GameData
import pytesseract
import sys


pytesseract.pytesseract.tesseract_cmd = resource_path("assets/tesseract/tesseract.exe")


class HSRScannerUI(QtWidgets.QMainWindow, Ui_MainWindow):
    """HSRScannerUI handles the UI for the HSR Scanner application"""

    is_scanning = False

    def __init__(self) -> None:
        """Constructor"""
        super().__init__()
        self._scanner_thread = None
        self._listener = InterruptListener()

    def setupUi(self, MainWindow: QtWidgets.QMainWindow) -> None:
        """Sets up the UI for the application

        :param MainWindow: The main window of the application
        """
        super().setupUi(MainWindow)
        self.pushButtonStartScan.clicked.connect(self.start_scan)
        self.lineEditOutputLocation.setText(executable_path("StarRailData"))
        self.pushButtonChangeLocation.clicked.connect(self.change_output_location)
        self.pushButtonOpenLocation.clicked.connect(self.open_output_location)
        try:
            self.game_data = GameData()
            self.log("Loaded database version: " + self.game_data.version)
        except Exception as e:
            self.log("ERROR: " + str(e))
            self.pushButtonStartScan.setEnabled(False)
            self.pushButtonStartScan.setText("ERROR")

    def change_output_location(self) -> None:
        """Opens a dialog to change the output location of the scan"""
        new_output_location = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Output Location", self.lineEditOutputLocation.text()
        )
        if new_output_location:
            self.lineEditOutputLocation.setText(new_output_location)

    def open_output_location(self) -> None:
        """Opens the output location of the scan in the file explorer"""
        output_location = self.lineEditOutputLocation.text()
        if output_location:
            try:
                QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl.fromLocalFile(output_location)
                )
            except Exception as e:
                self.log(f"Error opening output location: {e}")

    def start_scan(self) -> None:
        """Starts the scan"""
        self.disable_start_scan_button()
        for label in [
            self.labelLightConeCount,
            self.labelRelicCount,
            self.labelCharacterCount,
            self.labelLightConeProcessed,
            self.labelRelicProcessed,
            self.labelCharacterProcessed,
        ]:
            label.setText("0")
        self.textEditLog.clear()

        try:
            scanner = HSRScanner(self.get_config(), self.game_data)
        except Exception as e:
            self.log(e)
            self.enable_start_scan_button()
            return

        self._scanner_thread = ScannerThread(scanner)

        self._scanner_thread.log.connect(self.log)

        self._scanner_thread.update_progress.connect(self.increment_progress)

        self._scanner_thread.complete.connect(self._listener.stop)

        # self._scanner_thread.result.connect(self.log)
        self._scanner_thread.result.connect(self.handle_result)
        self._scanner_thread.result.connect(self._scanner_thread.deleteLater)
        self._scanner_thread.result.connect(self.enable_start_scan_button)

        self._scanner_thread.error.connect(self.log)
        self._scanner_thread.error.connect(self._scanner_thread.deleteLater)
        self._scanner_thread.error.connect(self.enable_start_scan_button)
        self._scanner_thread.error.connect(self._listener.stop)

        self._listener.interrupt.connect(self._scanner_thread.interrupt_scan)
        self._scanner_thread.start()
        self._listener.start()

    def get_config(self) -> dict:
        """Gets the configuration for the scan

        :return: The configuration for the scan
        """
        # scan options
        config = {}
        config["scan_light_cones"] = self.checkBoxScanLightCones.isChecked()
        config["scan_relics"] = self.checkBoxScanRelics.isChecked()
        config["scan_characters"] = self.checkBoxScanChars.isChecked()
        if not any(
            [
                config["scan_light_cones"],
                config["scan_relics"],
                config["scan_characters"],
            ]
        ):
            raise Exception("No scan options selected. Please select at least one.")

        # filters
        config["filters"] = {
            "light_cone": {
                "min_level": self.spinBoxLightConeMinLevel.value(),
                "min_rarity": self.spinBoxLightConeMinRarity.value(),
            },
            "relic": {
                "min_level": self.spinBoxRelicMinLevel.value(),
                "min_rarity": self.spinBoxRelicMinRarity.value(),
            },
        }

        # hotkeys
        config["inventory_key"] = self.lineEditInventoryKey.text()
        config["characters_key"] = self.lineEditCharactersKey.text()
        if not config["inventory_key"]:
            raise Exception("Inventory key is not set.")
        if not config["characters_key"]:
            raise Exception("Characters key is not set.")

        return config

    def handle_result(self, data: dict) -> None:
        """Handles the result of the scan

        :param data: The data from the scan
        """
        output_location = self.lineEditOutputLocation.text()
        file_name = (
            f"HSRScanData_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        save_to_json(data, output_location, file_name)
        self.log("Scan complete. Data saved to " + output_location)

    def increment_progress(self, enum: IncrementType) -> None:
        """Increments the number on the UI based on the enum

        :param enum: The enum to increment the progress for
        """
        match IncrementType(enum):
            case IncrementType.LIGHT_CONE_ADD:
                self.labelLightConeCount.setText(
                    str(int(self.labelLightConeCount.text()) + 1)
                )
            case IncrementType.RELIC_ADD:
                self.labelRelicCount.setText(str(int(self.labelRelicCount.text()) + 1))
            case IncrementType.CHARACTER_ADD:
                self.labelCharacterCount.setText(
                    str(int(self.labelCharacterCount.text()) + 1)
                )
            case IncrementType.LIGHT_CONE_SUCCESS:
                self.labelLightConeProcessed.setText(
                    str(int(self.labelLightConeProcessed.text()) + 1)
                )
            case IncrementType.RELIC_SUCCESS:
                self.labelRelicProcessed.setText(
                    str(int(self.labelRelicProcessed.text()) + 1)
                )
            case IncrementType.CHARACTER_SUCCESS:
                self.labelCharacterProcessed.setText(
                    str(int(self.labelCharacterProcessed.text()) + 1)
                )

    def disable_start_scan_button(self) -> None:
        """Disables the start scan button and sets the text to Processing"""
        self.is_scanning = True
        self.pushButtonStartScan.setText("Processing...")
        self.pushButtonStartScan.setEnabled(False)

    def enable_start_scan_button(self) -> None:
        """Enables the start scan button and sets the text to Start Scan"""
        self.is_scanning = False
        self.pushButtonStartScan.setText("Start Scan")
        self.pushButtonStartScan.setEnabled(True)

    def log(self, message: str) -> None:
        """Logs a message to the log box

        :param message: The message to log
        """
        self.textEditLog.appendPlainText(str(message))


class InterruptListener(QtCore.QThread):
    """InterruptListener class listens for the enter key to interrupt the scan"""

    interrupt = QtCore.pyqtSignal()

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.listener = None

    def run(self):
        """Runs the listener"""
        with Listener(on_press=self.on_press) as listener:
            self.listener = listener
            listener.join()

    def stop(self):
        """Stops the listener"""
        if self.listener:
            self.listener.stop()

    def on_press(self, key: Key) -> None:
        """Handles the key press. If the key is enter, emit the interrupt signal

        :param key: The key that was pressed
        """

        if key == Key.enter:
            self.interrupt.emit()


class ScannerThread(QtCore.QThread):
    """ScannerThread class handles the scanning in a separate thread"""

    update_progress = QtCore.pyqtSignal(int)
    result = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(object)
    log = QtCore.pyqtSignal(str)
    complete = QtCore.pyqtSignal()

    def __init__(self, scanner: HSRScanner) -> None:
        """Constructor

        :param scanner: The HSRScanner class instance
        """
        super().__init__()
        self._scanner = scanner
        self._scanner.update_progress = self.update_progress
        self._scanner.logger = self.log
        self._scanner.complete = self.complete

        self._interrupt_requested = False

    def run(self) -> None:
        """Runs the scan"""
        try:
            res = asyncio.run(self._scanner.start_scan())
            # print(res)
            if self._interrupt_requested:
                self.error.emit("Scan interrupted")
            else:
                self.result.emit(res)
        except Exception as e:
            self.error.emit("Scan aborted with error: " + str(e))

    def interrupt_scan(self) -> None:
        """Interrupts the scan"""
        self._interrupt_requested = True
        self._scanner.stop_scan()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(resource_path("assets/images/app.ico")))
    MainWindow = QtWidgets.QMainWindow()
    ui = HSRScannerUI()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
