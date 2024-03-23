import time

import cv2
import numpy as np
import pyautogui
import win32gui
from PIL.Image import Image
from pynput import keyboard, mouse

from utils.window import bring_window_to_foreground


class Navigation:
    """Navigation class for navigating the game window"""

    def __init__(self, hwnd: int) -> None:
        """Constructor

        :param hwnd: The window handle of the game window
        """
        self._hwnd = hwnd
        self._width, self._height = win32gui.GetClientRect(self._hwnd)[2:]
        if self._width == 0 or self._height == 0:
            bring_window_to_foreground(hwnd, 9)
            self._width, self._height = win32gui.GetClientRect(self._hwnd)[2:]
        self._left, self._top = win32gui.ClientToScreen(self._hwnd, (0, 0))

        self._mouse = mouse.Controller()
        self._keyboard = keyboard.Controller()

    def translate_percent_to_coords(
        self, x_percent: float, y_percent: float
    ) -> tuple[int, int]:
        """Translate percentage coordinates to pixel coordinates

        :param x_percent: The x percentage coordinate
        :param y_percent: The y percentage coordinate
        :return: The pixel coordinates
        """
        x = self._left + int(self._width * x_percent)
        y = self._top + int(self._height * y_percent)

        return x, y

    def move_cursor_to(self, x_percent: float, y_percent: float) -> None:
        """Move the cursor to the specified percentage coordinates

        :param x_percent: The x percentage coordinate
        :param y_percent: The y percentage coordinate
        """
        x, y = self.translate_percent_to_coords(x_percent, y_percent)

        self._mouse.position = (x, y)

    def move_cursor_to_image(self, haystack: Image, needle: Image) -> None:
        """Move the cursor to the center of the needle image in the haystack image

        :param haystack: The haystack image
        :param needle: The needle image
        """
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

    def key_tap(self, key: keyboard.Key | str) -> None:
        """Tap a key

        :param key: The key to tap
        """
        # already a Key, tap it
        if isinstance(key, keyboard.Key):
            self._keyboard.tap(key)
            return

        # key is a string
        key = key.lower()

        # if it's a special key, retrieve it from the keyboard module
        if len(key) > 1:
            self._keyboard.tap(getattr(keyboard.Key, key))
            return

        # otherwise just pass in the character string
        self._keyboard.tap(key)

    def key_hold(self, key: keyboard.Key) -> None:
        """Hold a key

        :param key: The key to hold
        """
        self._keyboard.press(key)

    def key_release(self, key: keyboard.Key) -> None:
        """Release a key

        :param key: The key to release
        """
        self._keyboard.release(key)

    def click(self) -> None:
        """Click the left mouse button"""
        self._mouse.click(mouse.Button.left)

    def drag_scroll(
        self, start_x: float, start_y: float, end_x: float, end_y: float
    ) -> None:
        """Drag scroll from start coordinates to end coordinates

        :param start_x: The start x percent coordinate
        :param start_y: The start y percent coordinate
        :param end_x: The end x percent coordinate
        :param end_y: The end y percent coordinate
        """
        start_x = self._left + int(self._width * start_x)
        start_y = self._top + int(self._height * start_y)
        end_x = self._left + int(self._width * end_x)
        end_y = self._top + int(self._height * end_y)

        pyautogui.moveTo(start_x, start_y)
        pyautogui.mouseDown()
        pyautogui.moveTo(end_x, end_y, duration=1)

        time.sleep(0.5)
        pyautogui.mouseUp()

    def scroll_page_down(self, times_scrolled) -> None:
        """Scroll down one inventory page

        For every 4 times scrolled, scroll up once to compensate for imprecision

        :param times_scrolled: The number of times scrolled
        """
        for _ in range(25):
            self._mouse.scroll(0, -1)
            time.sleep(0.01)

        if times_scrolled != 0 and times_scrolled % 4 == 0:
            self._mouse.scroll(0, 1)

    def print_mouse_position(self) -> None:
        """Print the current mouse position"""
        x_percent, y_percent = self.get_mouse_position()

        print("x: " + str(x_percent) + ", y: " + str(y_percent))

    def get_mouse_position(self) -> tuple[float, float]:
        """Get the current mouse position

        :return: The current mouse position
        """
        mouse_x, mouse_y = self._mouse.position
        right, bottom = win32gui.ClientToScreen(self._hwnd, (self._width, self._height))

        x_percent = (mouse_x - self._left) / (right - self._left)
        y_percent = (mouse_y - self._top) / (bottom - self._top)

        return x_percent, y_percent

    def get_aspect_ratio(self) -> str:
        """Get the aspect ratio of the game window

        :return: The aspect ratio of the game window
        """
        x, y = self._width, self._height
        gcd = self._gcd(x, y)
        return f"{x // gcd}:{y // gcd}"

    def _gcd(self, a: int, b: int) -> int:
        """Calculate the greatest common divisor of two numbers

        :param a: The first number
        :param b: The second number
        :return: The greatest common divisor of the two numbers
        """
        while b:
            a, b = b, a % b
        return a
