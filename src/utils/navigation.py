import win32gui
import pyautogui
import time
from pynput import mouse, keyboard


class Navigation:

    def __init__(self, hwnd):
        self._hwnd = hwnd
        self._width, self._height = win32gui.GetClientRect(self._hwnd)[2:]
        self._left, self._top = win32gui.ClientToScreen(self._hwnd, (0, 0))

        self._mouse = mouse.Controller()
        self._keyboard = keyboard.Controller()

    def bring_window_to_foreground(self):
        win32gui.ShowWindow(self._hwnd, 5)
        win32gui.SetForegroundWindow(self._hwnd)

    def move_cursor_to(self, x_percent, y_percent):
        x = self._left + int(self._width * x_percent)
        y = self._top + int(self._height * y_percent)

        self._mouse.position = (x, y)

    def send_key_press(self, key):
        self._keyboard.tap(key)

    def click(self):
        self._mouse.click(mouse.Button.left)

    def drag_scroll(self, x, start_y, end_y):
        x = self._left + int(self._width * x)
        start_y = self._top + int(self._height * start_y)
        end_y = self._top + int(self._height * end_y)

        pyautogui.moveTo(x, start_y)
        pyautogui.mouseDown()
        pyautogui.dragTo(x, end_y, duration=1, mouseDownUp=False)
        time.sleep(0.5)
        pyautogui.mouseUp()

    def print_mouse_position(self):
        x_percent, y_percent = self.get_mouse_position()

        print("x: " + str(x_percent) + ", y: " + str(y_percent))

    def get_mouse_position(self):
        mouse_x, mouse_y = self._mouse.position
        right, bottom = win32gui.ClientToScreen(
            self._hwnd, (self._width, self._height))

        x_percent = (mouse_x - self._left) / (right - self._left)
        y_percent = (mouse_y - self._top) / (bottom - self._top)

        return x_percent, y_percent

    def get_aspect_ratio(self):
        x, y = win32gui.GetClientRect(self._hwnd)[2:]
        gcd = self.gcd(x, y)
        return f"{x // gcd}:{y // gcd}"

    def gcd(self, a, b):
        while b:
            a, b = b, a % b
        return a
