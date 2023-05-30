import pyautogui
import win32gui


class Screenshot:
    coords = {
        "16:9": {
            "quantity": (0.89, 0.46, 0.13, 0.06),
            "stats": (0.09, 0.72, 0.25, 0.78),
            "sort": (0.9, 0.079, 0.07, 0.033),
            "character": {
                "count": (0.555, 0.56, 0.05, 0.035),
                "name": (0.059, 0.0656, 0.144, 0.0314),
                "level": (0.216, 0.795, 0.024, 0.034),
                "traces": {
                    "hunt": {
                        "levels": {
                            "basic": (0.5324, 0.526),
                            "skill": (0.5324, 0.679),
                            "ult": (0.6, 0.602),
                            "talent": (0.4628, 0.602),
                        },
                        "locks": {
                            "bonus_1": (0.647, 0.53, 0.015, 0.027),
                            "bonus_2": (0.647, 0.692, 0.015, 0.027),
                            "bonus_3": (0.279, 0.612, 0.015, 0.027),
                            "stat_1": (0.797, 0.6061, 0.011, 0.023),
                            "stat_2": (0.572, 0.468, 0.011, 0.023),
                            "stat_3": (0.479, 0.413, 0.011, 0.023),
                            "stat_4": (0.355, 0.47, 0.011, 0.023),
                            "stat_5": (0.574, 0.741, 0.011, 0.023),
                            "stat_6": (0.479, 0.798, 0.011, 0.023),
                            "stat_7": (0.355, 0.74, 0.011, 0.023),
                            "stat_8": (0.20, 0.605, 0.011, 0.023),
                            "stat_9": (0.227, 0.517, 0.011, 0.023),
                            "stat_10": (0.227, 0.693, 0.011, 0.023),
                        }
                    },
                    "erudition": {
                        "levels": {
                            "basic": (0.588, 0.53),
                            "skill": (0.588, 0.674),
                            "ult": (0.588, 0.603),
                            "talent": (0.438, 0.603)
                        },
                        "locks": {
                            "bonus_1": (0.504, 0.481, 0.015, 0.027),
                            "bonus_2": (0.504, 0.744, 0.015, 0.027),
                            "bonus_3": (0.185, 0.612, 0.015, 0.027),
                            "stat_1": (0.726, 0.535, 0.011, 0.023),
                            "stat_2": (0.523, 0.419, 0.011, 0.023),
                            "stat_3": (0.413, 0.435, 0.011, 0.023),
                            "stat_4": (0.635, 0.435, 0.011, 0.023),
                            "stat_5": (0.523, 0.793, 0.011, 0.023),
                            "stat_6": (0.413, 0.778, 0.011, 0.023),
                            "stat_7": (0.635, 0.778, 0.011, 0.023),
                            "stat_8": (0.23, 0.517, 0.011, 0.023),
                            "stat_9": (0.23, 0.697, 0.011, 0.023),
                            "stat_10": (0.726, 0.678, 0.011, 0.023),
                        }
                    }
                }
            },
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
        return self.__screenshot_stats("light_cone")

    def screenshot_relic_stats(self):
        return self.__screenshot_stats("relic")

    def screenshot_relic_sort(self):
        coords = self.coords[self._aspect_ratio]["sort"]
        coords = (coords[0], coords[1] + 0.035, coords[2], coords[3])
        return self.__take_screenshot(*coords)

    def screenshot_light_cone_sort(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["sort"])

    def screenshot_quantity(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["quantity"])

    def screenshot_character_count(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["character"]["count"])

    def screenshot_character_name(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["character"]["name"])

    def screenshot_character_level(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["character"]["level"])

    def screenshot_character_hunt_traces(self):
        return self.__screenshot_traces("hunt")
    
    def screenshot_character_erudition_traces(self):
        return self.__screenshot_traces("erudition")

    def __take_screenshot(self, top, left, width, height):
        x = self._left + int(self._width * left)
        y = self._top + int(self._height * top)
        width = int(self._width * width)
        height = int(self._height * height)

        screenshot = pyautogui.screenshot(region=(x, y, width, height))

        return screenshot

    def __screenshot_stats(self, key):
        coords = self.coords[self._aspect_ratio]

        img = self.__take_screenshot(*coords["stats"])

        adjusted_stat_coords = {
            k: tuple([int(v * img.width) if i % 2 == 0 else int(v * img.height) for i, v in enumerate(v)]) for k, v in coords[key].items()}

        res = {
            k: img.crop(v) for k, v in adjusted_stat_coords.items()
        }

        return res

    def __screenshot_traces(self, key):
        coords = self.coords[self._aspect_ratio]

        res = {
            "levels": {},
            "locks": {}
        }
        for k, v in coords["character"]["traces"][key]["levels"].items():
            res["levels"][k] = self.__take_screenshot(*v, 0.0177, 0.028)

        for k, v in coords["character"]["traces"][key]["locks"].items():
            res["locks"][k] = self.__take_screenshot(*v)

        return res
