import pyautogui
import win32gui
from PIL import ImageFilter


class Screenshot:
    coords = {
        "16:9": {
            "quantity": (0.89, 0.46, 0.13, 0.06),
            "stats": (0.09, 0.72, 0.25, 0.78),
            "light_cone": {
                "name": (0, 0, 1, 0.09),
                "level": (0.13, 0.32, 0.35, 0.37),
                "superimposition": (0.53, 0.48, 0.6, 0.55)
            },
            "relic": {
                "name": (0, 0, 1, 0.09),
                "level": (0.115, 0.25, 0.23, 0.3),

                "mainStatKey": (0.115, 0.358, 0.7, 0.4),

                "subStatKey_1": (0.115, 0.4, 0.77, 0.45),
                "subStatVal_1": (0.77, 0.4, 1, 0.45),

                "subStatKey_2": (0.115, 0.45, 0.77, 0.5),
                "subStatVal_2": (0.77, 0.45, 1, 0.5),

                "subStatKey_3": (0.115, 0.495, 0.77, 0.545),
                "subStatVal_3": (0.77, 0.495, 1, 0.545),

                "subStatKey_4": (0.115, 0.545, 0.77, 0.595),
                "subStatVal_4": (0.77, 0.545, 1, 0.595),
            }
        }
    }

    def __init__(self, hwnd, aspect_ratio="16:9"):
        self._aspect_ratio = aspect_ratio

        self._width, self._height = win32gui.GetClientRect(hwnd)[2:]
        self._left, self._top = win32gui.ClientToScreen(hwnd, (0, 0))

    def screenshot_stats(self, key):
        coords = self.coords[self._aspect_ratio]

        img = self._take_screenshot(*coords["stats"])

        adjusted_stat_coords = {
            k: tuple([int(v * img.width) if i % 2 == 0 else int(v * img.height) for i, v in enumerate(v)]) for k, v in coords[key].items()}

        return {
            k: img.crop(v) for k, v in adjusted_stat_coords.items()
        }

    def screenshot_light_cone_stats(self):
        return self.screenshot_stats("light_cone")

    def screenshot_relic_stats(self):
        return self.screenshot_stats("relic")

    def screenshot_quantity(self):
        return self._take_screenshot(
            *self.coords[self._aspect_ratio]["quantity"])

    def _take_screenshot(self, top, left, width, height):
        x = self._left + int(self._width * left)
        y = self._top + int(self._height * top)
        width = int(self._width * width)
        height = int(self._height * height)

        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot = screenshot.convert('L')
        screenshot = screenshot.filter(ImageFilter.GaussianBlur(radius=1))

        screenshot = screenshot.filter(ImageFilter.EDGE_ENHANCE)
        
        return screenshot
