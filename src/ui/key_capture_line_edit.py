from PyQt6 import QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit


class KeyCaptureLineEdit(QLineEdit):
    """KeyCaptureLineEdit is a QLineEdit that captures key presses and displays the key name in the QLineEdit"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.default_style = self.styleSheet()
        self.focused_style = "border: 2px solid blue;"

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        self.setStyleSheet(self.focused_style)
        super().focusInEvent(event)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self.setStyleSheet(self.default_style)
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.clearFocus()
            return
        if event.modifiers() != Qt.KeyboardModifier.NoModifier:
            return

        # disallowed keys
        if event.key() in [
            Qt.Key.Key_Meta,
            Qt.Key.Key_Tab,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
            Qt.Key.Key_PageUp,
            Qt.Key.Key_PageDown,
            Qt.Key.Key_Insert,
            Qt.Key.Key_Delete,
            Qt.Key.Key_ScrollLock,
            Qt.Key.Key_Pause,
            Qt.Key.Key_Print,
            Qt.Key.Key_Shift,
        ]:
            return

        if event.key() >= Qt.Key.Key_F1 and event.key() <= Qt.Key.Key_F24:
            key_name = self.get_function_key_name(event)
        # insert skull emoji here
        elif event.key() == Qt.Key.Key_Delete:
            key_name = "DELETE"
        elif event.key() == Qt.Key.Key_Backspace:
            key_name = "BACKSPACE"
        elif event.key() == Qt.Key.Key_Return:
            key_name = "ENTER"
        elif event.key() == Qt.Key.Key_Control:
            key_name = "CTRL"
        elif event.key() == Qt.Key.Key_Alt:
            key_name = "ALT"
        elif event.key() == Qt.Key.Key_Space:
            key_name = "SPACE"
        elif event.key() == Qt.Key.Key_Up:
            key_name = "UP"
        elif event.key() == Qt.Key.Key_Down:
            key_name = "DOWN"
        elif event.key() == Qt.Key.Key_Left:
            key_name = "LEFT"
        elif event.key() == Qt.Key.Key_Right:
            key_name = "RIGHT"
        elif event.key() == Qt.Key.Key_CapsLock:
            key_name = "CAPS_LOCK"
        else:
            key_name = event.text().upper()

        self.setText(key_name)
        self.clearFocus()
        super().keyPressEvent(event)

    def get_function_key_name(self, event):
        return f"F{event.key() - Qt.Key.Key_F1 + 1}"
