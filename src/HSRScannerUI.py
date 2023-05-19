from ui.hsr_scanner import Ui_MainWindow
from PyQt6 import QtCore, QtGui, QtWidgets
from scanner import HSRScanner
import asyncio
from enum import Enum


class ScanType(Enum):
    LIGHT_CONE = 0
    RELIC = 1
    CHARACTER = 2


class HSRScannerUI(Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self._scanner = HSRScanner()

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.buttonStartScan.clicked.connect(self.startScan)

    def startScan(self):
        self.disable_start_scan_button()

        self._scanner.scan_light_cones = self.checkBoxScanLightCones.isChecked()
        self._scanner.scan_relics = self.checkBoxScanRelics.isChecked()
        self._scanner.scan_characters = self.checkBoxScanChars.isChecked()

        self._scanner_thread = ScannerThread(self._scanner)

        self._scanner_thread.update_progress.connect(self.increment_progress)

        self._scanner_thread.result.connect(self.log)
        self._scanner_thread.result.connect(self._scanner_thread.deleteLater)
        self._scanner_thread.result.connect(self.enable_start_scan_button)

        self._scanner_thread.error.connect(self.log)
        self._scanner_thread.error.connect(self._scanner_thread.deleteLater)
        self._scanner_thread.error.connect(self.enable_start_scan_button)

        self._scanner_thread.start()

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
        self.buttonStartScan.setText("Processing...")
        self.buttonStartScan.setEnabled(False)

    def enable_start_scan_button(self):
        self.buttonStartScan.setText("Start Scan")
        self.buttonStartScan.setEnabled(True)

    def log(self, message):
        self.textLog.appendPlainText(str(message))

    def setupButtonStartScan(self):
        self.buttonStartScan.clicked.connect(self.startScan)


class ScannerThread(QtCore.QThread):
    update_progress = QtCore.pyqtSignal(int)
    result = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(object)

    def __init__(self, scanner):
        super().__init__()
        self._scanner = scanner
        self._scanner.update_progress = self.update_progress.emit

    def run(self):
        try:
            asyncio.run(self._scanner.scan(self.result.emit))
        except Exception as e:
            self.error.emit(e)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = HSRScannerUI()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
