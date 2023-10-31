import cv2
import numpy as np
import win32gui
from PIL import Image, ImageGrab
from config.screenshot import SCREENSHOT_COORDS


class Screenshot:
    """Screenshot class for taking screenshots of the game window"""

    def __init__(self, hwnd: int, aspect_ratio: str = "16:9") -> None:
        """Constructor

        :param hwnd: The window handle of the game window
        :param aspect_ratio: The aspect ratio of the game window, defaults to "16:9"
        """
        self._aspect_ratio = aspect_ratio

        self._window_width, self._window_height = win32gui.GetClientRect(hwnd)[2:]
        self._window_x, self._window_y = win32gui.ClientToScreen(hwnd, (0, 0))

        self._x_scaling_factor = self._window_width / 1920
        self._y_scaling_factor = self._window_height / 1080

    def screenshot_screen(self) -> Image:
        """Takes a screenshot of the entire screen

        :return: The screenshot
        """
        return self._take_screenshot(0, 0, 1, 1)

    def screenshot_light_cone_stats(self) -> dict:
        """Takes a screenshot of the light cone stats

        :return: A dict of the stats with the key being the stat name and the value being the screenshot
        """
        return self._screenshot_stats("light_cone")

    def screenshot_relic_stats(self) -> dict:
        """Takes a screenshot of the relic stats

        :return: A dict of the stats with the key being the stat name and the value being the screenshot
        """
        return self._screenshot_stats("relic")

    def screenshot_relic_sort(self) -> Image:
        """Takes a screenshot of the relic sort button

        :return: The screenshot
        """

        # need to adjust coordinates for relic sort button because it's not in the same place as the light cone sort button
        coords = SCREENSHOT_COORDS[self._aspect_ratio]["sort"]
        coords = (coords[0] + 0.035, coords[1], coords[2], coords[3])

        return self._take_screenshot(*coords)

    def screenshot_light_cone_sort(self) -> Image:
        """Takes a screenshot of the light cone sort button

        :return: The screenshot
        """
        return self._take_screenshot(*SCREENSHOT_COORDS[self._aspect_ratio]["sort"])

    def screenshot_quantity(self) -> Image:
        """Takes a screenshot of the quantity

        :return: The screenshot
        """
        return self._take_screenshot(*SCREENSHOT_COORDS[self._aspect_ratio]["quantity"])

    def screenshot_character_count(self) -> Image:
        """Takes a screenshot of the character count

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio]["character"]["count"]
        )

    def screenshot_character_name(self) -> Image:
        """Takes a screenshot of the character name

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio]["character"]["name"]
        )

    def screenshot_character_level(self) -> Image:
        """Takes a screenshot of the character level

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio]["character"]["level"]
        )

    def screenshot_character(self) -> Image:
        """Takes a screenshot of the character

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio]["character"]["chest"]
        )

    def screenshot_character_eidolons(self) -> list[np.ndarray]:
        """Takes a screenshot of the character eidolons

        :return: A list of the screenshots
        """
        res = []

        screenshot = ImageGrab.grab(all_screens=True)
        offset, _, _ = Image.core.grabscreen_win32(False, True)
        x0, y0 = offset
        dim = 81

        # Circle mask
        mask = np.zeros((dim, dim), dtype="uint8")
        cv2.circle(mask, (int(dim / 2), int(dim / 2)), int(dim / 2), 255, -1)

        for c in SCREENSHOT_COORDS[self._aspect_ratio]["character"]["eidolons"]:
            left = self._window_x + int(self._window_width * c[0])
            upper = self._window_y + int(self._window_height * c[1])
            right = left + self._window_width * 0.042
            lower = upper + self._window_height * 0.075
            img = screenshot.crop((left - x0, upper - y0, right - x0, lower - y0))

            # Apply circle mask
            img = np.array(img)
            img = cv2.resize(img, (dim, dim))
            img = cv2.bitwise_and(img, img, mask=mask)

            res.append(img)

        return res

    def screenshot_character_hunt_traces(self) -> dict:
        """Takes a screenshot of the character hunt trace levels

        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces("hunt")

    def screenshot_character_erudition_traces(self) -> dict:
        """Takes a screenshot of the character erudition trace levels

        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces("erudition")

    def screenshot_character_harmony_traces(self) -> dict:
        """Takes a screenshot of the character harmony trace levels

        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces("harmony")

    def screenshot_character_preservation_traces(self) -> dict:
        """Takes a screenshot of the character preservation trace levels

        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces("preservation")

    def screenshot_character_destruction_traces(self) -> dict:
        """Takes a screenshot of the character destruction trace levels

        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces("destruction")

    def screenshot_character_nihility_traces(self) -> dict:
        """Takes a screenshot of the character nihility trace levels

        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces("nihility")

    def screenshot_character_abundance_traces(self) -> dict:
        """Takes a screenshot of the character abundance trace levels

        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces("abundance")

    def _take_screenshot(
        self, x: float, y: float, width: float, height: float
    ) -> Image:
        """Takes a screenshot of the game window

        :param x: The x coordinate of the top left corner of the screenshot
        :param y: The y coordinate of the top left corner of the screenshot
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
            bbox=(x, y, x + width, y + height), all_screens=True
        )

        screenshot = screenshot.resize(
            (int(width / self._x_scaling_factor), int(height / self._y_scaling_factor))
        )

        return screenshot

    def _screenshot_stats(self, key: str) -> dict:
        """Takes a screenshot of the stats

        :param key: The key of the stats to screenshot
        :return: A dict of the stats with the key being the stat name and the value being the screenshot
        """
        coords = SCREENSHOT_COORDS[self._aspect_ratio]

        img = self._take_screenshot(*coords["stats"])

        adjusted_stat_coords = {
            k: tuple(
                [
                    int(v * img.width) if i % 2 == 0 else int(v * img.height)
                    for i, v in enumerate(v)
                ]
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
        offset, _, _ = Image.core.grabscreen_win32(False, True)
        x0, y0 = offset

        for k, v in coords["character"]["traces"][key].items():
            left = self._window_x + int(self._window_width * v[0])
            upper = self._window_y + int(self._window_height * v[1])
            right = left + int(self._window_width * 0.04)
            lower = upper + int(self._window_height * 0.028)

            res[k] = screenshot.crop((left - x0, upper - y0, right - x0, lower - y0))

        return res
