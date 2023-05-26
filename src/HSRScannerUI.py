import asyncio
from ui.hsr_scanner import Ui_MainWindow
from PyQt6 import QtCore, QtGui, QtWidgets
from scanner import HSRScanner
from enum import Enum
from pynput.keyboard import Key, Listener
from file_helpers import resource_path, save_to_json
import pytesseract
import sys


pytesseract.pytesseract.tesseract_cmd = resource_path(
    "./tesseract/tesseract.exe")


class ScanType(Enum):
    LIGHT_CONE = 0
    RELIC = 1
    CHARACTER = 2


class HSRScannerUI(QtWidgets.QMainWindow, Ui_MainWindow):
    is_scanning = False
    output_location = sys.path[0] + "\\StarRailData"

    def __init__(self):
        super().__init__()
        self._scanner_thread = None
        self._listener = InterruptListener()

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.pushButtonStartScan.clicked.connect(self.start_scan)
        self.lineEditOutputLocation.setText(self.output_location)
        self.pushButtonChangeLocation.clicked.connect(
            self.change_output_location)

    def change_output_location(self):
        new_output_location = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Output Location", self.output_location)
        if new_output_location:
            self.output_location = new_output_location
            self.lineEditOutputLocation.setText(self.output_location)

    def start_scan(self):
        self.disable_start_scan_button()
        self.labelLightConeCount.setText("0")
        self.labelRelicCount.setText("0")
        self.labelCharacterCount.setText("0")
        self.textEditLog.clear()

        scanner = HSRScanner(self.get_config())

        self._scanner_thread = ScannerThread(scanner)

        self._scanner_thread.log.connect(self.log)

        self._scanner_thread.update_progress.connect(self.increment_progress)

        # self._scanner_thread.result.connect(self.log)
        self._scanner_thread.result.connect(self.receive_scan_result)
        self._scanner_thread.result.connect(self._scanner_thread.deleteLater)
        self._scanner_thread.result.connect(self.enable_start_scan_button)
        self._scanner_thread.result.connect(self._listener.stop)

        self._scanner_thread.error.connect(self.log)
        self._scanner_thread.error.connect(self._scanner_thread.deleteLater)
        self._scanner_thread.error.connect(self.enable_start_scan_button)
        self._scanner_thread.error.connect(self._listener.stop)

        self._listener.interrupt.connect(self._scanner_thread.interrupt_scan)
        self._scanner_thread.start()
        self._listener.start()

    def get_config(self):
        config = {}
        config["scan_light_cones"] = self.checkBoxScanLightCones.isChecked()
        config["scan_relics"] = self.checkBoxScanRelics.isChecked()
        config["scan_characters"] = self.checkBoxScanChars.isChecked()
        config["inventory_key"] = self.lineEditInventoryKey.text().lower()
        config["character_key"] = self.lineEditCharacterKey.text().lower()
        return config

    def receive_scan_result(self, data):
        save_to_json(data, self.output_location)
        self.log("Scan complete. Data saved to " + self.output_location)

    def increment_progress(self, enum):
        if ScanType(enum) == ScanType.LIGHT_CONE:
            self.labelLightConeCount.setText(
                str(int(self.labelLightConeCount.text()) + 1))
        elif ScanType(enum) == ScanType.RELIC:
            self.labelRelicCount.setText(
                str(int(self.labelRelicCount.text()) + 1))
        elif ScanType(enum) == ScanType.CHARACTER:
            self.labelCharacterCount.setText(
                str(int(self.labelCharacterCount.text()) + 1))

    def disable_start_scan_button(self):
        self.is_scanning = True
        self.pushButtonStartScan.setText("Processing...")
        self.pushButtonStartScan.setEnabled(False)

    def enable_start_scan_button(self):
        self.is_scanning = False
        self.pushButtonStartScan.setText("Start Scan")
        self.pushButtonStartScan.setEnabled(True)

    def log(self, message):
        self.textEditLog.appendPlainText(str(message))

    def setupButtonStartScan(self):
        self.pushButtonStartScan.clicked.connect(self.start_scan)


class InterruptListener(QtCore.QThread):
    interrupt = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.listener = None

    def run(self):
        with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            self.listener = listener
            listener.join()

    def stop(self):
        if self.listener:
            self.listener.stop()

    def on_press(self, key):
        if key == Key.enter:
            self.interrupt.emit()

    def on_release(self, key):
        if key == Key.enter:
            return False


class ScannerThread(QtCore.QThread):
    update_progress = QtCore.pyqtSignal(int)
    result = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(object)
    log = QtCore.pyqtSignal(str)

    def __init__(self, scanner):
        super().__init__()
        self._scanner = scanner
        self._scanner.update_progress = self.update_progress.emit
        self._scanner.logger = self.log

        self._interrupt_requested = False

    def run(self):
        try:
            res = asyncio.run(self._scanner.start_scan())
            # print(res)
            if self._interrupt_requested:
                self.error.emit("Scan interrupted")
            else:
                self.result.emit(res)
        except Exception as e:
            self.error.emit(e)

    def interrupt_scan(self):
        self._interrupt_requested = True
        self._scanner.stop_scan()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = HSRScannerUI()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
