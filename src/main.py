import asyncio
import datetime
import sys

import pytesseract
from pynput.keyboard import Key, Listener
from PyQt6 import QtCore, QtGui, QtWidgets

from enums.increment_type import IncrementType
from enums.scan_mode import ScanMode
from models.game_data import GameData
from services.scanner.scanner import HSRScanner
from ui.hsr_scanner import Ui_MainWindow
from utils.conversion import convert_to_sro
from utils.data import (create_debug_folder, executable_path, resource_path,
                        save_to_json)

pytesseract.pytesseract.tesseract_cmd = resource_path("assets/tesseract/tesseract.exe")


class HSRScannerUI(QtWidgets.QMainWindow, Ui_MainWindow):
    """HSRScannerUI handles the UI for the HSR Scanner application"""

    is_scanning = False

    def __init__(self) -> None:
        """Constructor"""
        super().__init__()
        self._scanner_thread = None
        self._listener = InterruptListener()
        self.settings = QtCore.QSettings("kel-z", "HSRScanner")

        # fetch game data
        self._fetch_game_data_thread = FetchGameDataThread()
        self._fetch_game_data_thread.result_signal.connect(self.handle_game_data)
        self._fetch_game_data_thread.error_signal.connect(self.handle_game_data_error)
        self._fetch_game_data_thread.start()

    def handle_game_data(self, game_data: GameData) -> None:
        """Handle on game data loaded

        :param game_data: The game data
        """
        self.game_data = game_data
        self.log("Loaded database version: " + self.game_data.version)

        try:
            self.pushButtonStartScan.clicked.disconnect()
            self.pushButtonStartScanRecentRelics.clicked.disconnect()
        except Exception:
            pass

        self.pushButtonStartScan.clicked.connect(self.start_scan)
        self.pushButtonStartScan.setEnabled(True)
        self.pushButtonStartScan.setText("Start Scan")

        self.pushButtonStartScanRecentRelics.clicked.connect(
            self.start_scan_recent_relics
        )
        self.pushButtonStartScanRecentRelics.setEnabled(True)
        self.pushButtonStartScanRecentRelics.setText("Scan")

        self._fetch_game_data_thread.deleteLater()

    def handle_game_data_error(self, e: Exception) -> None:
        """Handle on game data error

        :param e: The error
        """
        self.log(str(e))

        try:
            self.pushButtonStartScan.clicked.disconnect()
            self.pushButtonStartScanRecentRelics.clicked.disconnect()
        except Exception:
            pass

        self.pushButtonStartScan.clicked.connect(self._fetch_game_data_thread.start)
        self.pushButtonStartScan.setEnabled(True)
        self.pushButtonStartScan.setText("Retry")

        self.pushButtonStartScanRecentRelics.clicked.connect(
            self._fetch_game_data_thread.start
        )
        self.pushButtonStartScanRecentRelics.setEnabled(True)
        self.pushButtonStartScanRecentRelics.setText("Retry")

    def setup_ui(self, MainWindow: QtWidgets.QMainWindow) -> None:
        """Sets up the UI for the application

        :param MainWindow: The main window of the application
        """
        super().setupUi(MainWindow)

        self.pushButtonChangeLocation.clicked.connect(self.change_output_location)
        self.pushButtonOpenLocation.clicked.connect(self.open_output_location)
        self.pushButtonRestoreDefaults.clicked.connect(self.reset_settings)

        self.load_settings()

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

    def load_settings(self) -> None:
        """Loads the settings for the scan"""
        self.lineEditOutputLocation.setText(
            self.settings.value("output_location", executable_path("StarRailData"))
        )
        self.lineEditInventoryKey.setText(self.settings.value("inventory_key", "b"))
        self.lineEditCharactersKey.setText(self.settings.value("characters_key", "c"))
        self.spinBoxLightConeMinLevel.setValue(
            self.settings.value("min_light_cone_level", 1)
        )
        self.spinBoxLightConeMinRarity.setValue(
            self.settings.value("min_light_cone_rarity", 3)
        )
        self.spinBoxRelicMinLevel.setValue(self.settings.value("min_relic_level", 0))
        self.spinBoxRelicMinRarity.setValue(self.settings.value("min_relic_rarity", 2))
        self.checkBoxScanLightCones.setChecked(
            self.settings.value("scan_light_cones", False) == "true"
        )
        self.checkBoxScanRelics.setChecked(
            self.settings.value("scan_relics", False) == "true"
        )
        self.checkBoxScanChars.setChecked(
            self.settings.value("scan_characters", False) == "true"
        )
        self.checkBoxSroFormat.setChecked(
            self.settings.value("sro_format", False) == "true"
        )
        self.checkBoxDebugMode.setChecked(
            self.settings.value("debug_mode", False) == "true"
        )
        self.spinBoxNavDelay.setValue(self.settings.value("nav_delay", 0))
        self.spinBoxScanDelay.setValue(self.settings.value("scan_delay", 0))
        self.spinBoxRecentRelics.setValue(self.settings.value("recent_relics_num", 5))
        self.checkBoxRecentRelicsFiveStar.setChecked(
            self.settings.value("recent_relics_five_star", False) == "true"
        )
        self.checkBoxIncludeUid.setChecked(
            self.settings.value("include_uid", False) == "true"
        )

    def save_settings(self) -> None:
        """Saves the settings for the scan"""
        self.settings.setValue("output_location", self.lineEditOutputLocation.text())
        self.settings.setValue("inventory_key", self.lineEditInventoryKey.text())
        self.settings.setValue("characters_key", self.lineEditCharactersKey.text())
        self.settings.setValue(
            "min_light_cone_level", self.spinBoxLightConeMinLevel.value()
        )
        self.settings.setValue(
            "min_light_cone_rarity", self.spinBoxLightConeMinRarity.value()
        )
        self.settings.setValue("min_relic_level", self.spinBoxRelicMinLevel.value())
        self.settings.setValue("min_relic_rarity", self.spinBoxRelicMinRarity.value())
        self.settings.setValue(
            "scan_light_cones", self.checkBoxScanLightCones.isChecked()
        )
        self.settings.setValue("scan_relics", self.checkBoxScanRelics.isChecked())
        self.settings.setValue("scan_characters", self.checkBoxScanChars.isChecked())
        self.settings.setValue("sro_format", self.checkBoxSroFormat.isChecked())
        self.settings.setValue("debug_mode", self.checkBoxDebugMode.isChecked())
        self.settings.setValue("nav_delay", self.spinBoxNavDelay.value())
        self.settings.setValue("scan_delay", self.spinBoxScanDelay.value())
        self.settings.setValue("recent_relics_num", self.spinBoxRecentRelics.value())
        self.settings.setValue(
            "recent_relics_five_star", self.checkBoxRecentRelicsFiveStar.isChecked()
        )
        self.settings.setValue("include_uid", self.checkBoxIncludeUid.isChecked())

    def reset_settings(self) -> None:
        """Resets the settings for the scan"""
        self.settings.setValue("output_location", executable_path("StarRailData"))
        self.settings.setValue("inventory_key", "b")
        self.settings.setValue("characters_key", "c")
        self.settings.setValue("min_light_cone_level", 1)
        self.settings.setValue("min_light_cone_rarity", 3)
        self.settings.setValue("min_relic_level", 0)
        self.settings.setValue("min_relic_rarity", 2)
        self.settings.setValue("scan_light_cones", False)
        self.settings.setValue("scan_relics", False)
        self.settings.setValue("scan_characters", False)
        self.settings.setValue("sro_format", False)
        self.settings.setValue("nav_delay", 0)
        self.settings.setValue("scan_delay", 0)
        self.settings.setValue("recent_relics_num", 8)
        self.settings.setValue("recent_relics_five_star", True)
        self.settings.setValue("debug_mode", False)
        self.settings.setValue("include_uid", False)
        self.load_settings()

    def reset_fields(self) -> None:
        """Resets the fields on the UI"""
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

    def start_scan(self) -> None:
        """Starts the scan"""
        if self.is_scanning:
            return
        self.save_settings()
        self.reset_fields()

        config = self.get_config()

        # initialize scanner
        try:
            if not any(
                [
                    config["scan_light_cones"],
                    config["scan_relics"],
                    config["scan_characters"],
                ]
            ):
                raise Exception("No scan options selected. Please select at least one.")
            scanner = HSRScanner(config, self.game_data)
        except Exception as e:
            self.log(e)
            return

        self.log("Starting scan...")
        self.to_scanner_thread(scanner)

    def start_scan_recent_relics(self) -> None:
        """Starts the scan for recent relics"""
        if self.is_scanning:
            return
        self.save_settings()
        self.reset_fields()
        self.tabWidget.setCurrentIndex(0)

        config = self.get_config()
        config["scan_light_cones"] = False
        config["scan_characters"] = False
        config["scan_relics"] = True
        config["filters"] = {
            "relic": {
                "min_rarity": 5 if config["recent_relics_five_star"] else 0,
            }
        }

        # initialize scanner
        try:
            if config["recent_relics_num"] < 1:
                raise Exception("At least one relic must be scanned.")
            scanner = HSRScanner(
                config, self.game_data, scan_mode=ScanMode.RECENT_RELICS.value
            )
        except Exception as e:
            self.log(e)
            return

        self.log(
            f"Starting recent relics scan for {config['recent_relics_num']} relics..."
        )
        self.to_scanner_thread(scanner)

    def to_scanner_thread(self, scanner: HSRScanner) -> None:
        """Starts the scanner thread

        :param scanner: The HSRScanner class instance
        """
        self.disable_start_scan_button()

        # connect signals
        scanner.log_signal.connect(self.log)
        scanner.update_signal.connect(self.increment_progress)
        scanner.complete_signal.connect(self._listener.stop)

        # initialize thread
        self._scanner_thread = ScannerThread(scanner)
        self._scanner_thread.log_signal.connect(self.log)

        self._scanner_thread.result_signal.connect(self.handle_result)
        self._scanner_thread.result_signal.connect(self._scanner_thread.deleteLater)
        self._scanner_thread.result_signal.connect(self.enable_start_scan_button)

        self._scanner_thread.error_signal.connect(self.log)
        self._scanner_thread.error_signal.connect(self._scanner_thread.deleteLater)
        self._scanner_thread.error_signal.connect(self.enable_start_scan_button)
        self._scanner_thread.error_signal.connect(self._listener.stop)

        self._listener.interrupt_signal.connect(self._scanner_thread.interrupt_scan)

        # start thread
        self._scanner_thread.started.connect(self._listener.start)
        self._scanner_thread.start()

    def get_config(self) -> dict:
        """Gets the configuration for the scan

        :return: The configuration for the scan
        """
        # scan options
        config = {}
        config["include_uid"] = self.checkBoxIncludeUid.isChecked()
        config["scan_light_cones"] = self.checkBoxScanLightCones.isChecked()
        config["scan_relics"] = self.checkBoxScanRelics.isChecked()
        config["scan_characters"] = self.checkBoxScanChars.isChecked()

        # recent relics scan options
        config["recent_relics_num"] = self.spinBoxRecentRelics.value()
        config[
            "recent_relics_five_star"
        ] = self.checkBoxRecentRelicsFiveStar.isChecked()

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

        # delays
        config["nav_delay"] = self.spinBoxNavDelay.value() / 1000
        config["scan_delay"] = self.spinBoxScanDelay.value() / 1000

        # debug mode
        config["debug"] = self.checkBoxDebugMode.isChecked()
        config["debug_output_location"] = None

        if config["debug"]:
            config["debug_output_location"] = create_debug_folder(
                self.lineEditOutputLocation.text()
            )
            self.log(
                "[DEBUG] Debug mode enabled. Debug output will be saved to "
                + config["debug_output_location"]
            )

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

        if self.checkBoxSroFormat.isChecked():
            self.log("Creating accompanying export in SRO format...")
            try:
                file_name = f"HSRScanData_SRO_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                save_to_json(
                    convert_to_sro(data, self.game_data), output_location, file_name
                )
            except Exception as e:
                self.log("Failed to convert to SRO format: " + str(e))
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

        self.pushButtonStartScanRecentRelics.setText("Processing...")
        self.pushButtonStartScanRecentRelics.setEnabled(False)

    def enable_start_scan_button(self) -> None:
        """Enables the start scan button and sets the text to Start Scan"""
        self.is_scanning = False

        self.pushButtonStartScan.setText("Start Scan")
        self.pushButtonStartScan.setEnabled(True)

        self.pushButtonStartScanRecentRelics.setText("Scan")
        self.pushButtonStartScanRecentRelics.setEnabled(True)

    def log(self, message: str) -> None:
        """Logs a message to the log box

        :param message: The message to log
        """
        self.textEditLog.appendPlainText(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] > {str(message)}"
        )


class FetchGameDataThread(QtCore.QThread):
    """FetchGameDataThread class handles fetching the game data in a separate thread"""

    result_signal = QtCore.pyqtSignal(object)
    error_signal = QtCore.pyqtSignal(object)

    def __init__(self) -> None:
        """Constructor"""
        super().__init__()

    def run(self) -> None:
        """Runs the fetch game data"""
        try:
            self.result_signal.emit(GameData())
            self.quit()
        except Exception as e:
            self.error_signal.emit(e)


class InterruptListener(QtCore.QThread):
    """InterruptListener class listens for the enter key to interrupt the scan"""

    interrupt_signal = QtCore.pyqtSignal()

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
            self.interrupt_signal.emit()


class ScannerThread(QtCore.QThread):
    """ScannerThread class handles the scanning in a separate thread"""

    result_signal = QtCore.pyqtSignal(object)
    error_signal = QtCore.pyqtSignal(object)
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, scanner: HSRScanner) -> None:
        """Constructor

        :param scanner: The HSRScanner class instance
        """
        super().__init__()
        self._scanner = scanner
        self._interrupt_requested = False

    def run(self) -> None:
        """Runs the scan"""
        try:
            res = asyncio.run(self._scanner.start_scan())
            if self._interrupt_requested:
                self.error_signal.emit("Scan interrupted")
            else:
                self.result_signal.emit(res)
        except Exception as e:
            self.error_signal.emit(
                f"Scan aborted with error {e.__class__.__name__}: {e} (Try scanning with a different in-game background, window resolution, or fullscreen/windowed mode, or increasing nav/scan delay in scanner configuration.)"
            )

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
    ui.setup_ui(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
