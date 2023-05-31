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
                    # yeah this part is quite masochistic
                    "hunt": {
                        "levels": {
                            "basic": (0.5324, 0.526),
                            "skill": (0.5324, 0.679),
                            "ult": (0.599, 0.601),
                            "talent": (0.462, 0.601),
                        },
                        "locks": {
                            "ability_1": (0.647, 0.53, 0.015, 0.027),
                            "ability_2": (0.647, 0.692, 0.015, 0.027),
                            "ability_3": (0.278, 0.611, 0.015, 0.027),
                            "stat_1": (0.797, 0.605, 0.011, 0.023),
                            "stat_2": (0.572, 0.468, 0.011, 0.023),
                            "stat_3": (0.479, 0.413, 0.011, 0.023),
                            "stat_4": (0.354, 0.469, 0.011, 0.023),
                            "stat_5": (0.574, 0.741, 0.011, 0.023),
                            "stat_6": (0.479, 0.797, 0.011, 0.023),
                            "stat_7": (0.355, 0.74, 0.011, 0.023),
                            "stat_8": (0.20, 0.605, 0.011, 0.023),
                            "stat_9": (0.227, 0.517, 0.011, 0.023),
                            "stat_10": (0.227, 0.693, 0.011, 0.023),
                        }
                    },
                    "erudition": {
                        "levels": {
                            "basic": (0.588, 0.528),
                            "skill": (0.588, 0.673),
                            "ult": (0.588, 0.601),
                            "talent": (0.438, 0.601)
                        },
                        "locks": {
                            "ability_1": (0.504, 0.479, 0.015, 0.027),
                            "ability_2": (0.504, 0.742, 0.015, 0.027),
                            "ability_3": (0.185, 0.61, 0.015, 0.027),
                            "stat_1": (0.726, 0.533, 0.011, 0.023),
                            "stat_2": (0.523, 0.417, 0.011, 0.023),
                            "stat_3": (0.412, 0.433, 0.011, 0.023),
                            "stat_4": (0.635, 0.433, 0.011, 0.023),
                            "stat_5": (0.523, 0.791, 0.011, 0.023),
                            "stat_6": (0.413, 0.777, 0.011, 0.023),
                            "stat_7": (0.635, 0.777, 0.011, 0.023),
                            "stat_8": (0.23, 0.515, 0.011, 0.023),
                            "stat_9": (0.23, 0.695, 0.011, 0.023),
                            "stat_10": (0.726, 0.676, 0.011, 0.023),
                        }
                    },
                    "harmony": {
                        "levels": {
                            "basic": (0.548, 0.528),
                            "skill": (0.548, 0.673),
                            "ult": (0.644, 0.601),
                            "talent": (0.522, 0.601)
                        },
                        "locks": {
                            "ability_1": (0.526, 0.442, 0.015, 0.027),
                            "ability_2": (0.526, 0.78, 0.015, 0.027),
                            "ability_3": (0.298, 0.61, 0.015, 0.027),
                            "stat_1": (0.798, 0.605, 0.011, 0.023),
                            "stat_2": (0.452, 0.398, 0.011, 0.023),
                            "stat_3": (0.389, 0.461, 0.011, 0.023),
                            "stat_4": (0.771, 0.525, 0.011, 0.023),
                            "stat_5": (0.656, 0.741, 0.011, 0.023),
                            "stat_6": (0.618, 0.682, 0.011, 0.023),
                            "stat_7": (0.771, 0.684, 0.011, 0.023),
                            "stat_8": (0.203, 0.605, 0.011, 0.023),
                            "stat_9": (0.231, 0.52, 0.011, 0.023),
                            "stat_10": (0.231, 0.69, 0.011, 0.023),
                        }
                    },
                    "preservation": {
                        "levels": {
                            "basic": (0.606, 0.527),
                            "skill": (0.606, 0.677),
                            "ult": (0.588, 0.602),
                            "talent": (0.461, 0.602)
                        },
                        "locks": {
                            "ability_1": (0.762, 0.526, 0.015, 0.027),
                            "ability_2": (0.762, 0.695, 0.015, 0.027),
                            "ability_3": (0.281, 0.611, 0.015, 0.027),
                            "stat_1": (0.776, 0.605, 0.011, 0.023),
                            "stat_2": (0.639, 0.451, 0.011, 0.023),
                            "stat_3": (0.529, 0.398, 0.011, 0.023),
                            "stat_4": (0.422, 0.467, 0.011, 0.023),
                            "stat_5": (0.639, 0.758, 0.011, 0.023),
                            "stat_6": (0.528, 0.811, 0.011, 0.023),
                            "stat_7": (0.422, 0.743, 0.011, 0.023),
                            "stat_8": (0.208, 0.605, 0.011, 0.023),
                            "stat_9": (0.231, 0.515, 0.011, 0.023),
                            "stat_10": (0.231, 0.694, 0.011, 0.023),
                        }
                    },
                    "destruction": {
                        "levels": {
                            "basic": (0.569, 0.516),
                            "skill": (0.569, 0.689),
                            "ult": (0.588, 0.602),
                            "talent": (0.461, 0.602)
                        },
                        "locks": {
                            "ability_1": (0.664, 0.520, 0.015, 0.027),
                            "ability_2": (0.664, 0.703, 0.015, 0.027),
                            "ability_3": (0.281, 0.610, 0.015, 0.027),
                            "stat_1": (0.788, 0.604, 0.011, 0.023),
                            "stat_2": (0.612, 0.454, 0.011, 0.023),
                            "stat_3": (0.523, 0.402, 0.011, 0.023),
                            "stat_4": (0.396, 0.452, 0.011, 0.023),
                            "stat_5": (0.612, 0.755, 0.011, 0.023),
                            "stat_6": (0.524, 0.807, 0.011, 0.023),
                            "stat_7": (0.396, 0.757, 0.011, 0.023),
                            "stat_8": (0.209, 0.605, 0.011, 0.023),
                            "stat_9": (0.232, 0.515, 0.011, 0.023),
                            "stat_10": (0.232, 0.694, 0.011, 0.023),
                        }
                    },
                    "nihility": {
                        "levels": {
                            "basic": (0.517, 0.521),
                            "skill": (0.517, 0.683),
                            "ult": (0.501, 0.602),
                            "talent": (0.387, 0.602)
                        },
                        "locks": {
                            "ability_1": (0.388, 0.465, 0.015, 0.027),
                            "ability_2": (0.388, 0.757, 0.015, 0.027),
                            "ability_3": (0.19, 0.611, 0.015, 0.027),
                            "stat_1": (0.68, 0.604, 0.011, 0.023),
                            "stat_2": (0.524, 0.401, 0.011, 0.023),
                            "stat_3": (0.638, 0.449, 0.011, 0.023),
                            "stat_4": (0.748, 0.502, 0.011, 0.023),
                            "stat_5": (0.524, 0.808, 0.011, 0.023),
                            "stat_6": (0.638, 0.760, 0.011, 0.023),
                            "stat_7": (0.748, 0.707, 0.011, 0.023),
                            "stat_8": (0.231, 0.515, 0.011, 0.023),
                            "stat_9": (0.231, 0.694, 0.011, 0.023),
                            "stat_10": (0.787, 0.604, 0.011, 0.023),
                        }
                    },
                    "abundance": {
                        "levels": {
                            "basic": (0.566, 0.53),
                            "skill": (0.566, 0.674),
                            "ult": (0.592, 0.602),
                            "talent": (0.462, 0.602)
                        },
                        "locks": {
                            "ability_1": (0.685, 0.501, 0.015, 0.027),
                            "ability_2": (0.685, 0.722, 0.015, 0.027),
                            "ability_3": (0.183, 0.611, 0.015, 0.027),
                            "stat_1": (0.782, 0.644, 0.011, 0.023),
                            "stat_2": (0.782, 0.564, 0.011, 0.023),
                            "stat_3": (0.595, 0.446, 0.011, 0.023),
                            "stat_4": (0.507, 0.417, 0.011, 0.023),
                            "stat_5": (0.414, 0.473, 0.011, 0.023),
                            "stat_6": (0.597, 0.763, 0.011, 0.023),
                            "stat_7": (0.507, 0.792, 0.011, 0.023),
                            "stat_8": (0.415, 0.736, 0.011, 0.023),
                            "stat_9": (0.238, 0.517, 0.011, 0.023),
                            "stat_10": (0.231, 0.694, 0.011, 0.023),
                        }
                    }
                },
                "eidelons": [
                    (0.198, 0.34),
                    (0.187, 0.546),
                    (0.377, 0.793),
                    (0.826, 0.679),
                    (0.796, 0.43),
                    (0.716, 0.197)
                ]
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

    def screenshot_character_eidelons(self):
        res = []
        for c in self.coords[self._aspect_ratio]["character"]["eidelons"]:
            res.append(self.__take_screenshot(*c, 0.018, 0.0349))
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
