import pyautogui
import win32gui
from PIL import ImageFilter, Image
from utils.game_data import GameData


class Screenshot:
    coords = {
        "16:9": {
            "quantity": (0.89, 0.46, 0.13, 0.06),
            "stats": (0.09, 0.72, 0.25, 0.78),
            "sort": (0.9, 0.079, 0.07, 0.033),
            "light_cone": {
                "name": (0, 0, 1, 0.09),
                "level": (0.13, 0.32, 0.35, 0.37),
                "superimposition": (0.53, 0.48, 0.6, 0.55),
                "equipped": (0.45, 0.95, 0.68, 1),
                "equipped_avatar": (0.35, 0.94, 0.44, 0.99),
                "lock": (0.896, 0.321, 0.97, 0.365),
            },
            "relic": {
                "name": (0, 0, 1, 0.09),
                "level": (0.115, 0.255, 0.23, 0.3),
                "lock": (0.865, 0.253, 0.935, 0.293),
                "rarity": (0.07, 0.15, 0.2, 0.22),
                "equipped": (0.45, 0.95, 0.68, 1),
                "equipped_avatar": (0.35, 0.94, 0.44, 0.99),

                "mainStatKey": (0.115, 0.358, 0.7, 0.4),

                "subStatKey_1": (0.115, 0.41, 0.77, 0.45),
                "subStatVal_1": (0.77, 0.41, 1, 0.45),

                "subStatKey_2": (0.115, 0.45, 0.77, 0.5),
                "subStatVal_2": (0.77, 0.45, 1, 0.5),

                "subStatKey_3": (0.115, 0.495, 0.77, 0.542),
                "subStatVal_3": (0.77, 0.495, 1, 0.542),

                "subStatKey_4": (0.115, 0.545, 0.77, 0.595),
                "subStatVal_4": (0.77, 0.545, 1, 0.595),
            }
        }
    }

    def __init__(self, hwnd, aspect_ratio="16:9"):
        self._aspect_ratio = aspect_ratio

        self._width, self._height = win32gui.GetClientRect(hwnd)[2:]
        self._left, self._top = win32gui.ClientToScreen(hwnd, (0, 0))

    def screenshot_light_cone_stats(self):
        return self._screenshot_stats("light_cone")

    def screenshot_relic_stats(self):
        return self._screenshot_stats("relic")

    def screenshot_relic_sort(self):
        coords = self.coords[self._aspect_ratio]["sort"]
        coords = (coords[0], coords[1] + 0.035, coords[2], coords[3])
        return self._take_screenshot(*coords)

    def screenshot_light_cone_sort(self):
        return self._take_screenshot(
            *self.coords[self._aspect_ratio]["sort"])

    def screenshot_quantity(self):
        return self._take_screenshot(
            *self.coords[self._aspect_ratio]["quantity"])

    def preprocess_img(self, img):
        if img.height < 50:
            img = img.resize((img.width * 2, img.height * 2))

        for x in range(img.width):
            for y in range(img.height):
                pixel = img.getpixel((x, y))
                if pixel[0] > 150 and pixel[1] > 150 and pixel[2] > 150:
                    img.putpixel((x, y), (255, 255, 255))
                else:
                    img.putpixel(
                        (x, y), (pixel[0] - 75, pixel[1] - 75, pixel[2] - 75))

        img = img.convert('L')
        img = img.filter(ImageFilter.EDGE_ENHANCE)
        img = img.filter(ImageFilter.GaussianBlur(radius=1))

        return img

    def _take_screenshot(self, top, left, width, height):
        x = self._left + int(self._width * left)
        y = self._top + int(self._height * top)
        width = int(self._width * width)
        height = int(self._height * height)

        screenshot = pyautogui.screenshot(region=(x, y, width, height))

        return screenshot

    def _screenshot_stats(self, key):
        coords = self.coords[self._aspect_ratio]

        img = self._take_screenshot(*coords["stats"])

        adjusted_stat_coords = {
            k: tuple([int(v * img.width) if i % 2 == 0 else int(v * img.height) for i, v in enumerate(v)]) for k, v in coords[key].items()}

        result = {
            k: img.crop(v) for k, v in adjusted_stat_coords.items()
        }

        return result
