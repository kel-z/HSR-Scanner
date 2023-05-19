from ui.hsr_scanner import Ui_MainWindow
from PyQt6 import QtCore, QtGui, QtWidgets
from scanner import HSRScanner


class HSRScannerUI(Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self._scanner = HSRScanner()

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.buttonStartScan.clicked.connect(self.startScan)

    def startScan(self):
        self._scanner.scan_light_cones = self.checkBoxScanLightCones.isChecked()
        self._scanner.scan_relics = self.checkBoxScanRelics.isChecked()
        self._scanner.scan_characters = self.checkBoxScanChars.isChecked()

        try:
            self._scanner.scan()
        except Exception as e:
            print(e)

    def setupButtonStartScan(self):
        self.buttonStartScan.clicked.connect(self.startScan)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = HSRScannerUI()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
