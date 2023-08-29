import cv2
import numpy as np
import win32gui
import pyautogui
import time
from pynput import mouse, keyboard


class Navigation:
    def __init__(self, hwnd):
        self._hwnd = hwnd
        self._width, self._height = win32gui.GetClientRect(self._hwnd)[2:]
        if self._width == 0 or self._height == 0:
            self.bring_window_to_foreground(9)
            self._width, self._height = win32gui.GetClientRect(self._hwnd)[2:]
        self._left, self._top = win32gui.ClientToScreen(self._hwnd, (0, 0))

        self._mouse = mouse.Controller()
        self._keyboard = keyboard.Controller()

    def bring_window_to_foreground(self, cmd_show=5):
        win32gui.ShowWindow(self._hwnd, cmd_show)
        win32gui.SetForegroundWindow(self._hwnd)

    def translate_percent_to_coords(self, x_percent, y_percent):
        x = self._left + int(self._width * x_percent)
        y = self._top + int(self._height * y_percent)

        return x, y

    def move_cursor_to(self, x_percent, y_percent):
        x, y = self.translate_percent_to_coords(x_percent, y_percent)

        self._mouse.position = (x, y)

    def move_cursor_to_image(self, haystack, needle):
        haystack = np.array(haystack)
        needle = np.array(needle)

        pos = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(pos)

        offset_x = 0.5 * needle.shape[1] / haystack.shape[1]
        offset_y = 0.5 * needle.shape[0] / haystack.shape[0]

        pos = (
            max_loc[0] / haystack.shape[1] + offset_x,
            max_loc[1] / haystack.shape[0] + offset_y,
        )

        self.move_cursor_to(*pos)

    def key_press(self, key):
        self._keyboard.tap(key)

    def key_hold(self, key):
        self._keyboard.press(key)

    def key_release(self, key):
        self._keyboard.release(key)

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
        right, bottom = win32gui.ClientToScreen(self._hwnd, (self._width, self._height))

        x_percent = (mouse_x - self._left) / (right - self._left)
        y_percent = (mouse_y - self._top) / (bottom - self._top)

        return x_percent, y_percent

    def get_aspect_ratio(self):
        x, y = self._width, self._height
        gcd = self.gcd(x, y)
        return f"{x // gcd}:{y // gcd}"

    def gcd(self, a, b):
        while b:
            a, b = b, a % b
        return a
