import datetime
import os

import cv2
import numpy as np
import win32gui
from PIL import Image as PILImage
from PIL import ImageGrab
from PIL.Image import Image
from PyQt6.QtCore import pyqtBoundSignal

from config.const import (
    ASPECT_16_9,
    CHARACTER,
    CHAR_EIDOLONS,
    CHEST,
    COUNT,
    QUANTITY,
    SORT,
    STATS,
    TRACES,
    UID,
)
from config.screenshot import SCREENSHOT_COORDS
from enums.increment_type import IncrementType
from models.const import CHAR_LEVEL, CHAR_NAME


class Screenshot:
    """Screenshot class for taking screenshots of the game window"""

    def __init__(
        self,
        hwnd: int,
        log_signal: pyqtBoundSignal,
        aspect_ratio: str = ASPECT_16_9,
        debug: bool = False,
        debug_output_location: str = "",
    ) -> None:
        """Constructor

        :param hwnd: The window handle of the game window
        :param aspect_ratio: The aspect ratio of the game window, defaults to "16:9"
        :param debug_mode: Whether to save screenshots, default False
        :param debug_output_location: Output location of saved screenshots
        """
        self._aspect_ratio = aspect_ratio
        self._log_signal = log_signal

        self._window_width, self._window_height = win32gui.GetClientRect(hwnd)[2:]
        self._window_x, self._window_y = win32gui.ClientToScreen(hwnd, (0, 0))

        self._x_scaling_factor = self._window_width / 1920
        self._y_scaling_factor = self._window_height / 1080

        self._debug = debug
        self._debug_output_location = debug_output_location

    def screenshot_screen(self) -> Image:
        """Takes a screenshot of the entire screen

        :return: The screenshot
        """
        do_not_save = True  # so users don't unintentionally reveal their UID when naively sharing debug folder
        return self._take_screenshot(0, 0, 1, 1, do_not_save)

    def screenshot_stats(self, scan_type: IncrementType) -> dict:
        """Takes a screenshot of the stats. Requires an item to be selected in the inventory.

        :param scan_type: The scan type
        :raises ValueError: Thrown if the scan type is invalid
        :return: A dict of the stats with the key being the stat name and the value being the screenshot
        """
        match IncrementType(scan_type):
            case IncrementType.LIGHT_CONE_ADD:
                return self._screenshot_stats("light_cone")
            case IncrementType.RELIC_ADD:
                return self._screenshot_stats("relic")
            case _:
                raise ValueError(f"Invalid scan type: {scan_type.name}.")

    def screenshot_sort(self) -> Image:
        """Takes a screenshot of the current sort option. Requires inventory to be open.

        :return: The screenshot
        """
        coords = SCREENSHOT_COORDS[self._aspect_ratio][SORT]
        return self._take_screenshot(*coords)

    def screenshot_quantity(self) -> Image:
        """Takes a screenshot of the quantity. Requires inventory to be open.

        :return: The screenshot
        """
        return self._take_screenshot(*SCREENSHOT_COORDS[self._aspect_ratio][QUANTITY])

    def screenshot_character_count(self) -> Image:
        """Takes a screenshot of the character count. Requires

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][COUNT]
        )

    def screenshot_character_name(self) -> Image:
        """Takes a screenshot of the character name

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][CHAR_NAME]
        )

    def screenshot_character_level(self) -> Image:
        """Takes a screenshot of the character level

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][CHAR_LEVEL]
        )

    def screenshot_character(self) -> Image:
        """Takes a screenshot of the character

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][CHEST]
        )

    def screenshot_character_eidolons(self) -> list[np.ndarray]:
        """Takes a screenshot of the character eidolons

        :return: A list of the screenshots
        """
        res = []

        screenshot = ImageGrab.grab(all_screens=True)
        offset, _, _ = PILImage.core.grabscreen_win32(False, True)  # type: ignore
        x0, y0 = offset
        dim = 81

        # Circle mask
        mask = np.zeros((dim, dim), dtype="uint8")
        cv2.circle(mask, (int(dim / 2), int(dim / 2)), int(dim / 2), 255, -1)  # type: ignore

        for c in SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][CHAR_EIDOLONS]:
            left = self._window_x + int(self._window_width * c[0])
            upper = self._window_y + int(self._window_height * c[1])
            right = left + self._window_width * 0.042
            lower = upper + self._window_height * 0.075
            img = screenshot.crop((left - x0, upper - y0, right - x0, lower - y0))

            # Apply circle mask
            img = np.array(img)
            img = cv2.resize(img, (dim, dim))  # type: ignore
            img = cv2.bitwise_and(img, img, mask=mask)  # type: ignore

            res.append(img)

        if self._debug:
            for img in res:
                self._save_image(PILImage.fromarray(img))

        return res

    def screenshot_character_traces(self, key: str) -> dict:
        """Takes a screenshot of the character trace levels

        :param key: The key of the traces to screenshot
        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces(key)

    def screenshot_uid(self) -> Image:
        """Takes a screenshot of the UID. Requires ESC menu to be open.

        :return: The screenshot
        """
        return self._take_screenshot(*SCREENSHOT_COORDS[self._aspect_ratio][UID])

    def _take_screenshot(
        self, x: float, y: float, width: float, height: float, do_not_save: bool = False
    ) -> Image:
        """Takes a screenshot of the game window

        :param x: The x percent coordinate of the top left corner of the screenshot
        :param y: The y percent coordinate of the top left corner of the screenshot
        :param width: The width of the screenshot
        :param height: The height of the screenshot
        :return: The screenshot normalized to 1920x1080
        """
        # adjust coordinates to window
        x = self._window_x + int(self._window_width * x)
        y = self._window_y + int(self._window_height * y)
        width = int(self._window_width * width)
        height = int(self._window_height * height)

        screenshot = ImageGrab.grab(
            bbox=(int(x), int(y), int(x + width), int(y + height)), all_screens=True
        )

        screenshot = screenshot.resize(
            (int(width / self._x_scaling_factor), int(height / self._y_scaling_factor))
        )

        if self._debug and not do_not_save:
            self._save_image(screenshot)

        return screenshot

    def _screenshot_stats(self, key: str) -> dict:
        """Takes a screenshot of the stats

        :param key: The key of the stats to screenshot
        :return: A dict of the stats with the key being the stat name and the value being the screenshot
        """
        coords = SCREENSHOT_COORDS[self._aspect_ratio]

        img = self._take_screenshot(*coords[STATS])

        adjusted_stat_coords = {
            k: (
                int(v[0] * img.width),
                int(v[1] * img.height),
                int(v[2] * img.width),
                int(v[3] * img.height),
            )
            for k, v in coords[key].items()
        }

        res = {k: img.crop(v) for k, v in adjusted_stat_coords.items()}

        return res

    def _screenshot_traces(self, key: str) -> dict:
        """Takes a screenshot of the trace levels

        :param key: The key of the traces to screenshot
        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        coords = SCREENSHOT_COORDS[self._aspect_ratio]

        res = {}

        screenshot = ImageGrab.grab(all_screens=True)
        offset, _, _ = PILImage.core.grabscreen_win32(False, True)  # type: ignore
        x0, y0 = offset

        for k, v in coords[CHARACTER][TRACES][key].items():
            left = self._window_x + int(self._window_width * v[0])
            upper = self._window_y + int(self._window_height * v[1])
            right = left + int(self._window_width * 0.04)
            lower = upper + int(self._window_height * 0.028)

            res[k] = screenshot.crop((left - x0, upper - y0, right - x0, lower - y0))

        if self._debug:
            for img in res.values():
                self._save_image(img)

        return res

    def _save_image(self, img: Image) -> None:
        """Save the image on disk.

        :param img: The image to save.
        """
        file_name = f"{datetime.datetime.now().strftime('%H%M%S%f')}.png"
        output_location = os.path.join(self._debug_output_location, file_name)
        img.save(output_location)
        self._log_signal.emit((f"Saving {file_name}."))
