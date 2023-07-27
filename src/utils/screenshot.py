# import pyautogui
import win32gui
from PIL import Image, ImageGrab


class Screenshot:
    coords = {
        "16:9": {
            "quantity": (0.46, 0.89, 0.13, 0.06),
            "stats": (0.72, 0.09, 0.25, 0.78),
            "sort": (0.079, 0.9, 0.07, 0.033),
            "character": {
                "count": (0.56, 0.555, 0.05, 0.035),
                "chest": (0.44, 0.3315, 0.1245, 0.1037),
                "name": (0.0656, 0.059, 0.16, 0.0314),
                "level": (0.795, 0.216, 0.024, 0.034),
                "eidelons": [
                    (0.198, 0.34),
                    (0.187, 0.546),
                    (0.377, 0.793),
                    (0.826, 0.679),
                    (0.796, 0.43),
                    (0.716, 0.197),
                ],
                "traces": {
                    "hunt": {
                        "basic": (0.505, 0.5352),
                        "skill": (0.655, 0.5352),
                        "ult": (0.578, 0.599),
                        "talent": (0.578, 0.462),
                    },
                },
            },
            # each tuple is (x1, y1, x2, y2) in % of the stat box
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
            },
        }
    }

    # coords = {
    #     "16:9": {
    #         "quantity": (0.89, 0.46, 0.13, 0.06),
    #         "stats": (0.09, 0.72, 0.25, 0.78),
    #         "sort": (0.9, 0.079, 0.07, 0.033),
    #         "character": {
    #             "count": (0.555, 0.56, 0.05, 0.035),
    #             "chest": (0.3315, 0.44, 0.1245, 0.1037),
    #             "name": (0.059, 0.0656, 0.16, 0.0314),
    #             "level": (0.216, 0.795, 0.024, 0.034),
    #             "traces": {
    #                 # yeah this part is quite masochistic
    #                 "hunt": {
    #                     "levels": {
    #                         "basic": (0.5352, 0.505),
    #                         "skill": (0.5352, 0.655),
    #                         "ult": (0.599, 0.578),
    #                         "talent": (0.462, 0.578),
    #                     },
    #                     "locks": {
    #                         "ability_1": (0.647, 0.53, 0.015, 0.027),
    #                         "ability_2": (0.647, 0.692, 0.015, 0.027),
    #                         "ability_3": (0.278, 0.611, 0.015, 0.027),
    #                         "stat_1": (0.797, 0.605, 0.011, 0.023),
    #                         "stat_2": (0.572, 0.468, 0.011, 0.023),
    #                         "stat_3": (0.479, 0.413, 0.011, 0.023),
    #                         "stat_4": (0.354, 0.469, 0.011, 0.023),
    #                         "stat_5": (0.574, 0.741, 0.011, 0.023),
    #                         "stat_6": (0.479, 0.797, 0.011, 0.023),
    #                         "stat_7": (0.355, 0.74, 0.011, 0.023),
    #                         "stat_8": (0.20, 0.605, 0.011, 0.023),
    #                         "stat_9": (0.227, 0.517, 0.011, 0.023),
    #                         "stat_10": (0.227, 0.693, 0.011, 0.023)
    #                     }
    #                 },
    #                 "erudition": {
    #                     "levels": {
    #                         "basic": (0.588, 0.528),
    #                         "skill": (0.588, 0.673),
    #                         "ult": (0.588, 0.601),
    #                         "talent": (0.438, 0.601)
    #                     },
    #                     "locks": {
    #                         "ability_1": (0.504, 0.479, 0.015, 0.027),
    #                         "ability_2": (0.504, 0.742, 0.015, 0.027),
    #                         "ability_3": (0.185, 0.61, 0.015, 0.027),
    #                         "stat_1": (0.726, 0.533, 0.011, 0.023),
    #                         "stat_2": (0.523, 0.417, 0.011, 0.023),
    #                         "stat_3": (0.412, 0.433, 0.011, 0.023),
    #                         "stat_4": (0.635, 0.433, 0.011, 0.023),
    #                         "stat_5": (0.523, 0.791, 0.011, 0.023),
    #                         "stat_6": (0.413, 0.777, 0.011, 0.023),
    #                         "stat_7": (0.635, 0.777, 0.011, 0.023),
    #                         "stat_8": (0.23, 0.515, 0.011, 0.023),
    #                         "stat_9": (0.23, 0.695, 0.011, 0.023),
    #                         "stat_10": (0.726, 0.676, 0.011, 0.023)
    #                     }
    #                 },
    #                 "harmony": {
    #                     "levels": {
    #                         "basic": (0.548, 0.528),
    #                         "skill": (0.548, 0.673),
    #                         "ult": (0.644, 0.601),
    #                         "talent": (0.522, 0.601)
    #                     },
    #                     "locks": {
    #                         "ability_1": (0.526, 0.442, 0.015, 0.027),
    #                         "ability_2": (0.526, 0.78, 0.015, 0.027),
    #                         "ability_3": (0.298, 0.61, 0.015, 0.027),
    #                         "stat_1": (0.798, 0.605, 0.011, 0.023),
    #                         "stat_2": (0.452, 0.398, 0.011, 0.023),
    #                         "stat_3": (0.389, 0.461, 0.011, 0.023),
    #                         "stat_4": (0.771, 0.525, 0.011, 0.023),
    #                         "stat_5": (0.656, 0.741, 0.011, 0.023),
    #                         "stat_6": (0.618, 0.682, 0.011, 0.023),
    #                         "stat_7": (0.771, 0.684, 0.011, 0.023),
    #                         "stat_8": (0.203, 0.605, 0.011, 0.023),
    #                         "stat_9": (0.231, 0.52, 0.011, 0.023),
    #                         "stat_10": (0.231, 0.69, 0.011, 0.023)
    #                     }
    #                 },
    #                 "preservation": {
    #                     "levels": {
    #                         "basic": (0.606, 0.527),
    #                         "skill": (0.606, 0.677),
    #                         "ult": (0.588, 0.602),
    #                         "talent": (0.461, 0.602)
    #                     },
    #                     "locks": {
    #                         "ability_1": (0.762, 0.526, 0.015, 0.027),
    #                         "ability_2": (0.762, 0.695, 0.015, 0.027),
    #                         "ability_3": (0.281, 0.611, 0.015, 0.027),
    #                         "stat_1": (0.776, 0.605, 0.011, 0.023),
    #                         "stat_2": (0.639, 0.451, 0.011, 0.023),
    #                         "stat_3": (0.529, 0.398, 0.011, 0.023),
    #                         "stat_4": (0.422, 0.467, 0.011, 0.023),
    #                         "stat_5": (0.639, 0.758, 0.011, 0.023),
    #                         "stat_6": (0.528, 0.811, 0.011, 0.023),
    #                         "stat_7": (0.422, 0.743, 0.011, 0.023),
    #                         "stat_8": (0.208, 0.605, 0.011, 0.023),
    #                         "stat_9": (0.231, 0.515, 0.011, 0.023),
    #                         "stat_10": (0.231, 0.694, 0.011, 0.023)
    #                     }
    #                 },
    #                 "destruction": {
    #                     "levels": {
    #                         "basic": (0.569, 0.516),
    #                         "skill": (0.569, 0.689),
    #                         "ult": (0.588, 0.602),
    #                         "talent": (0.461, 0.602)
    #                     },
    #                     "locks": {
    #                         "ability_1": (0.664, 0.520, 0.015, 0.027),
    #                         "ability_2": (0.664, 0.703, 0.015, 0.027),
    #                         "ability_3": (0.281, 0.610, 0.015, 0.027),
    #                         "stat_1": (0.788, 0.604, 0.011, 0.023),
    #                         "stat_2": (0.612, 0.454, 0.011, 0.023),
    #                         "stat_3": (0.523, 0.402, 0.011, 0.023),
    #                         "stat_4": (0.396, 0.452, 0.011, 0.023),
    #                         "stat_5": (0.612, 0.755, 0.011, 0.023),
    #                         "stat_6": (0.524, 0.807, 0.011, 0.023),
    #                         "stat_7": (0.396, 0.757, 0.011, 0.023),
    #                         "stat_8": (0.209, 0.605, 0.011, 0.023),
    #                         "stat_9": (0.232, 0.515, 0.011, 0.023),
    #                         "stat_10": (0.232, 0.694, 0.011, 0.023)
    #                     }
    #                 },
    #                 "nihility": {
    #                     "levels": {
    #                         "basic": (0.517, 0.521),
    #                         "skill": (0.517, 0.683),
    #                         "ult": (0.501, 0.602),
    #                         "talent": (0.387, 0.602)
    #                     },
    #                     "locks": {
    #                         "ability_1": (0.388, 0.465, 0.015, 0.027),
    #                         "ability_2": (0.388, 0.757, 0.015, 0.027),
    #                         "ability_3": (0.19, 0.611, 0.015, 0.027),
    #                         "stat_1": (0.68, 0.604, 0.011, 0.023),
    #                         "stat_2": (0.524, 0.401, 0.011, 0.023),
    #                         "stat_3": (0.638, 0.449, 0.011, 0.023),
    #                         "stat_4": (0.748, 0.502, 0.011, 0.023),
    #                         "stat_5": (0.524, 0.808, 0.011, 0.023),
    #                         "stat_6": (0.638, 0.760, 0.011, 0.023),
    #                         "stat_7": (0.748, 0.707, 0.011, 0.023),
    #                         "stat_8": (0.231, 0.515, 0.011, 0.023),
    #                         "stat_9": (0.231, 0.694, 0.011, 0.023),
    #                         "stat_10": (0.787, 0.604, 0.011, 0.023)
    #                     }
    #                 },
    #                 "abundance": {
    #                     "levels": {
    #                         "basic": (0.566, 0.53),
    #                         "skill": (0.566, 0.674),
    #                         "ult": (0.592, 0.602),
    #                         "talent": (0.462, 0.602)
    #                     },
    #                     "locks": {
    #                         "ability_1": (0.685, 0.722, 0.015, 0.027),
    #                         "ability_2": (0.685, 0.501, 0.015, 0.027),
    #                         "ability_3": (0.183, 0.611, 0.015, 0.027),
    #                         "stat_1": (0.782, 0.644, 0.011, 0.023),
    #                         "stat_2": (0.597, 0.763, 0.011, 0.023),
    #                         "stat_3": (0.507, 0.792, 0.011, 0.023),
    #                         "stat_4": (0.415, 0.736, 0.011, 0.023),
    #                         "stat_5": (0.595, 0.446, 0.011, 0.023),
    #                         "stat_6": (0.507, 0.417, 0.011, 0.023),
    #                         "stat_7": (0.414, 0.473, 0.011, 0.023),
    #                         "stat_8": (0.238, 0.517, 0.011, 0.023),
    #                         "stat_9": (0.231, 0.694, 0.011, 0.023),
    #                         "stat_10": (0.782, 0.564, 0.011, 0.023)
    #                     }
    #                 }
    #             },
    #             "eidelons": [
    #                 (0.198, 0.34),
    #                 (0.187, 0.546),
    #                 (0.377, 0.793),
    #                 (0.826, 0.679),
    #                 (0.796, 0.43),
    #                 (0.716, 0.197)
    #             ]
    #         },
    #         "light_cone": {
    #             "name": (0, 0, 1, 0.09),
    #             "level": (0.13, 0.32, 0.35, 0.37),
    #             "superimposition": (0.53, 0.48, 0.6, 0.55),
    #             "equipped": (0.45, 0.95, 0.68, 1),
    #             "equipped_avatar": (0.35, 0.94, 0.44, 0.99),
    #             "lock": (0.896, 0.321, 0.97, 0.365),
    #         },
    #         "relic": {
    #             "name": (0, 0, 1, 0.09),
    #             "level": (0.115, 0.255, 0.23, 0.3),
    #             "lock": (0.865, 0.253, 0.935, 0.293),
    #             "rarity": (0.07, 0.15, 0.2, 0.22),
    #             "equipped": (0.45, 0.95, 0.68, 1),
    #             "equipped_avatar": (0.35, 0.94, 0.44, 0.99),

    #             "mainStatKey": (0.115, 0.358, 0.7, 0.4),

    #             "subStatKey_1": (0.115, 0.41, 0.77, 0.45),
    #             "subStatVal_1": (0.77, 0.41, 1, 0.45),

    #             "subStatKey_2": (0.115, 0.45, 0.77, 0.5),
    #             "subStatVal_2": (0.77, 0.45, 1, 0.5),

    #             "subStatKey_3": (0.115, 0.495, 0.77, 0.542),
    #             "subStatVal_3": (0.77, 0.495, 1, 0.542),

    #             "subStatKey_4": (0.115, 0.545, 0.77, 0.595),
    #             "subStatVal_4": (0.77, 0.545, 1, 0.595),
    #         }
    #     }
    # }

    def __init__(self, hwnd, aspect_ratio="16:9"):
        self._aspect_ratio = aspect_ratio

        self._window_width, self._window_height = win32gui.GetClientRect(hwnd)[2:]
        self._window_x, self._window_y = win32gui.ClientToScreen(hwnd, (0, 0))

    def screenshot_light_cone_stats(self):
        return self.__screenshot_stats("light_cone")

    def screenshot_relic_stats(self):
        return self.__screenshot_stats("relic")

    def screenshot_relic_sort(self):
        coords = self.coords[self._aspect_ratio]["sort"]
        coords = (coords[0], coords[1] + 0.035, coords[2], coords[3])
        return self.__take_screenshot(*coords)

    def screenshot_light_cone_sort(self):
        return self.__take_screenshot(*self.coords[self._aspect_ratio]["sort"])

    def screenshot_quantity(self):
        return self.__take_screenshot(*self.coords[self._aspect_ratio]["quantity"])

    def screenshot_character_count(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["character"]["count"]
        )

    def screenshot_character_name(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["character"]["name"]
        )

    def screenshot_character_level(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["character"]["level"]
        )

    def screenshot_character(self):
        return self.__take_screenshot(
            *self.coords[self._aspect_ratio]["character"]["chest"]
        )

    def screenshot_character_eidelons(self):
        res = []

        screenshot = ImageGrab.grab(all_screens=True)
        offset, _, _ = Image.core.grabscreen_win32(False, True)
        x0, y0 = offset

        for c in self.coords[self._aspect_ratio]["character"]["eidelons"]:
            left = self._window_x + int(self._window_width * c[1])
            upper = self._window_y + int(self._window_height * c[0])
            right = left + self._window_width * 0.018
            lower = upper + self._window_height * 0.0349
            res.append(screenshot.crop((left - x0, upper - y0, right - x0, lower - y0)))

        return res

    def screenshot_character_hunt_traces(self):
        return self.__screenshot_traces("hunt")

    def screenshot_character_erudition_traces(self):
        return self.__screenshot_traces("erudition")

    def screenshot_character_harmony_traces(self):
        return self.__screenshot_traces("harmony")

    def screenshot_character_preservation_traces(self):
        return self.__screenshot_traces("preservation")

    def screenshot_character_destruction_traces(self):
        return self.__screenshot_traces("destruction")

    def screenshot_character_nihility_traces(self):
        return self.__screenshot_traces("nihility")

    def screenshot_character_abundance_traces(self):
        return self.__screenshot_traces("abundance")

    def __take_screenshot(self, x, y, width, height):
        # adjust coordinates to window
        x = self._window_x + int(self._window_width * x)
        y = self._window_y + int(self._window_height * y)
        width = int(self._window_width * width)
        height = int(self._window_height * height)

        # screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot = ImageGrab.grab(
            bbox=(x, y, x + width, y + height), all_screens=True
        )

        return screenshot

    def __screenshot_stats(self, key):
        coords = self.coords[self._aspect_ratio]

        img = self.__take_screenshot(*coords["stats"])
        # img = img.resize((480, 842), Image.ANTIALIAS)

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

    def __screenshot_traces(self, key):
        coords = self.coords[self._aspect_ratio]

        res = {"levels": {}, "unlocks": {}}

        screenshot = ImageGrab.grab(all_screens=True)
        offset, _, _ = Image.core.grabscreen_win32(False, True)
        x0, y0 = offset

        for k, v in coords["character"]["traces"][key].items():
            left = self._window_x + int(self._window_width * v[0])
            upper = self._window_y + int(self._window_height * v[1])
            right = left + int(self._window_width * 0.0177)
            lower = upper + int(self._window_height * 0.028)

            res["levels"][k] = screenshot.crop(
                (left - x0, upper - y0, right - x0, lower - y0)
            )

        return res
