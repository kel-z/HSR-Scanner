import pyautogui
import win32gui


class Screenshot:
    coords = {
        "16:9": {
            "quantity": (0.89, 0.46, 0.13, 0.06),
            "stats": (0.11, 0.72, 0.25, 0.755),
            "light_cone": {
                "stats_attr": {
                    "name": (0, 0, 1, 0.08),
                    "level": (0.13, 0.3, 0.35, 0.35),
                    "superimposition": (0.1, 0.48, 0.7, 0.55)
                }
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
            k: tuple([int(v * img.width) if i % 2 == 0 else int(v * img.height) for i, v in enumerate(v)]) for k, v in coords[key]["stats_attr"].items()}

        return {
            k: img.crop(v) for k, v in adjusted_stat_coords.items()
        }

    def screenshot_light_cone_stats(self):
        return self.screenshot_stats("light_cone")

    def screenshot_quantity(self):
        return self._take_screenshot(
            *self.coords[self._aspect_ratio]["quantity"])

    def _take_screenshot(self, top, left, width, height):
        x = self._left + int(self._width * left)
        y = self._top + int(self._height * top)
        width = int(self._width * width)
        height = int(self._height * height)

        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        return screenshot
