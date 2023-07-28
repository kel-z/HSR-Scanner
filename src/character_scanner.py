from pyautogui import locate
from helper_functions import resource_path, image_to_string
from PIL import Image
from helper_functions import resource_path, preprocess_trace_img
from utils.game_data_helpers import (
    get_character_meta_data,
    get_closest_character_name,
    get_closest_path_name,
)
from utils.screenshot import Screenshot


class CharacterScanner:
    NAV_DATA = {
        "16:9": {
            "data_bank": (0.765, 0.715),
            "ascension_start": (0.78125, 0.203),
            "ascension_offset_x": 0.01328,
            "chars_per_scan": 9,
            "char_start": (0.256, 0.065),
            "char_end": (0.744, 0.066),
            "offset_x": 0.055729,
            "details_button": (0.13, 0.143),
            "traces_button": (0.13, 0.315),
            "eidelons_button": (0.13, 0.49),
            "list_button": (0.033, 0.931),
            "trailblazer": (0.3315, 0.4432, 0.126, 0.1037),
            # trigger warning:
            "traces": {
                "hunt": {
                    "ability_1": (0.5020833333333333, 0.6833333333333333),
                    "ability_2": (0.6635, 0.6879),
                    "ability_3": (0.5828, 0.3166),
                    "skill_1": (0.58958, 0.8185),
                    "skill_2": (0.451, 0.599),
                    "skill_3": (0.3963, 0.5037),
                    "skill_4": (0.7255, 0.6),
                    "skill_5": (0.7255, 0.59629),
                    "skill_6": (0.7807, 0.5037),
                    "skill_7": (0.7239, 0.3805),
                    "skill_8": (0.58854, 0.2259),
                    "skill_9": (0.49948, 0.25277),
                    "skill_10": (0.6786, 0.25277),
                },
                "erudition": {
                    "ability_1": (0.45156, 0.541666),
                    "ability_2": (0.715625, 0.53889),
                    "ability_3": (0.5828, 0.22),
                    "skill_1": (0.5161, 0.7509),
                    "skill_2": (0.3989, 0.5472),
                    "skill_3": (0.4156, 0.43426),
                    "skill_4": (0.4156, 0.6555),
                    "skill_5": (0.7744, 0.54537),
                    "skill_6": (0.759375, 0.4352),
                    "skill_7": (0.759375, 0.6555),
                    "skill_8": (0.4984, 0.25),
                    "skill_9": (0.67864, 0.2481),
                    "skill_10": (0.6588, 0.74537),
                },
                "harmony": {
                    "ability_1": (0.414, 0.56389),
                    "ability_2": (0.752083, 0.56389),
                    "ability_3": (0.5838, 0.3315),
                    "skill_1": (0.5901, 0.819),
                    "skill_2": (0.3828, 0.47685),
                    "skill_3": (0.446875, 0.40925),
                    "skill_4": (0.509895, 0.79444),
                    "skill_5": (0.72656, 0.67685),
                    "skill_6": (0.66718, 0.63981),
                    "skill_7": (0.67031, 0.79444),
                    "skill_8": (0.5911, 0.22685),
                    "skill_9": (0.50468, 0.25277),
                    "skill_10": (0.67604, 0.2537),
                },
                "preservation": {
                    "ability_1": (0.497395, 0.8037037),
                    "ability_2": (0.665625, 0.803703),
                    "ability_3": (0.5822916, 0.321296296),
                    "skill_1": (0.589583, 0.8),
                    "skill_2": (0.435416, 0.66296),
                    "skill_3": (0.38333, 0.55185),
                    "skill_4": (0.45208, 0.44444),
                    "skill_5": (0.743229, 0.66481),
                    "skill_6": (0.795833, 0.550925),
                    "skill_7": (0.727083, 0.4462962),
                    "skill_8": (0.589583, 0.229629),
                    "skill_9": (0.499479, 0.255555),
                    "skill_10": (0.6796875, 0.2537),
                },
                "destruction": {
                    "ability_1": (0.4901041666666667, 0.7046296296296296),
                    "ability_2": (0.678125, 0.696296296),
                    "ability_3": (0.5880208, 0.31296296),
                    "skill_1": (0.5890625, 0.813889),
                    "skill_2": (0.4395833, 0.63425925),
                    "skill_3": (0.3875, 0.54537),
                    "skill_4": (0.4375, 0.41851),
                    "skill_5": (0.7395833, 0.63796296),
                    "skill_6": (0.7921875, 0.5462962962962963),
                    "skill_7": (0.741666, 0.42037),
                    "skill_8": (0.58958333, 0.229629),
                    "skill_9": (0.50052, 0.256481),
                    "skill_10": (0.6791666, 0.25555),
                },
                "nihility": {
                    "ability_1": (0.436871875, 0.4256944444),
                    "ability_2": (0.731640625, 0.4215277),
                    "ability_3": (0.5859375, 0.22291666),
                    "skill_1": (0.590234375, 0.7034722),
                    "skill_2": (0.38125, 0.5458333),
                    "skill_3": (0.4359375, 0.6569444),
                    "skill_4": (0.489453125, 0.76875),
                    "skill_5": (0.798828, 0.5465277),
                    "skill_6": (0.744921875, 0.6569444),
                    "skill_7": (0.691796875, 0.7680555),
                    "skill_8": (0.50078125, 0.2527777),
                    "skill_9": (0.680859375, 0.25257777),
                    "skill_10": (0.590625, 0.80763888),
                },
                "abundance": {
                    "ability_1": (0.472265, 0.720138),
                    "ability_2": (0.694140, 0.71875),
                    "ability_3": (0.584375, 0.2159723),
                    "skill_1": (0.630859, 0.802777),
                    "skill_2": (0.749218, 0.616666),
                    "skill_3": (0.778515, 0.527777),
                    "skill_4": (0.722656, 0.4354166),
                    "skill_5": (0.433203125, 0.618055),
                    "skill_6": (0.40390625, 0.52708333),
                    "skill_7": (0.459765625, 0.43541666),
                    "skill_8": (0.67890625, 0.2576388),
                    "skill_9": (0.504296875, 0.2583333),
                    "skill_10": (0.550390625, 0.80416666),
                },
            },
        }
    }

    def __init__(
        self, screenshot: Screenshot, logger, interrupt, update_progress
    ) -> None:
        self.interrupt = interrupt
        self.update_progress = update_progress
        self._trailblazer_imgs = [
            Image.open(resource_path("images\\trailblazerm.png")),
            Image.open(resource_path("images\\trailblazerf.png")),
        ]
        self._lock_img = Image.open(resource_path("./images/lock2.png"))
        self._screenshot = screenshot
        self._logger = logger
        self._trailblazerScanned = False

    def parse(self, stats_dict, eidlon_images):
        if self.interrupt.is_set():
            return

        character = {
            "key": stats_dict["name"],
            "level": 1,
            "ascension": stats_dict["ascension"],
            "eidelon": 0,
            "skills": {
                "basic": 0,
                "skill": 0,
                "ult": 0,
                "talent": 0,
            },
            "traces": {},
        }

        level = stats_dict["level"]
        res = image_to_string(level, "0123456789", 7, True)
        if not res:
            res = image_to_string(level, "0123456789", 6, True)
        level = res

        try:
            character["level"] = int(level)
        except ValueError:
            self._logger.emit(
                f"{character['key']}: Failed to parse level."
                + (f' Got "{level}" instead.' if level else "")
            ) if self._logger else None

        for img in eidlon_images:
            img = img.convert("L")
            min_dim = min(img.size)
            lock_img = self._lock_img.resize((min_dim, min_dim))
            unlocked = locate(lock_img, img, confidence=0.8) is None
            if not unlocked:
                break

            character["eidelon"] += 1

        if character["eidelon"] >= 5:
            character["skills"]["basic"] -= 1
            character["skills"]["skill"] -= 2
            character["skills"]["ult"] -= 2
            character["skills"]["talent"] -= 2
        elif character["eidelon"] >= 3:
            for k, v in get_character_meta_data(character["key"])["e3"].items():
                character["skills"][k] -= v

        traces_dict = stats_dict["traces"]
        for k, v in traces_dict["levels"].items():
            try:
                res = image_to_string(v, "0123456789/", 6, True, preprocess_trace_img)
                if not res or not res.find("/"):
                    res = image_to_string(
                        v, "0123456789/", 7, True, preprocess_trace_img
                    )
                character["skills"][k] += int(res.split("/")[0])
            except ValueError:
                self._logger.emit(
                    f"{character['key']}: Failed to parse {k} level."
                    + (f' Got "{res}" instead.' if res else "")
                    + " Setting to 1."
                ) if self._logger else None
                character["skills"][k] = 1

        character["traces"] = traces_dict["unlocks"]

        if self.update_progress:
            self.update_progress.emit(102)

        return character

    def get_traces_dict(self, path):
        if path == "The Hunt":
            traces_dict = self._screenshot.screenshot_character_hunt_traces()
        elif path == "Erudition":
            traces_dict = self._screenshot.screenshot_character_erudition_traces()
        elif path == "Harmony":
            traces_dict = self._screenshot.screenshot_character_harmony_traces()
        elif path == "Preservation":
            traces_dict = self._screenshot.screenshot_character_preservation_traces()
        elif path == "Destruction":
            traces_dict = self._screenshot.screenshot_character_destruction_traces()
        elif path == "Nihility":
            traces_dict = self._screenshot.screenshot_character_nihility_traces()
        elif path == "Abundance":
            traces_dict = self._screenshot.screenshot_character_abundance_traces()
        else:
            raise ValueError("Invalid path")

        return traces_dict

    def get_closest_name_and_path(self, character_name, path):
        path, _ = get_closest_path_name(path)

        if self.__is_trailblazer():
            if self._trailblazerScanned:
                self._logger.emit(
                    "WARNING: Parsed more than one Trailblazer. Please review JSON output."
                ) if self._logger else None
            else:
                self._trailblazerScanned = True

            return "Trailblazer" + path.split(" ")[-1], path
        else:
            character_name, min_dist = get_closest_character_name(character_name)

            if min_dist > 5:
                raise Exception(
                    f"Character not found in database. Got {character_name}"
                )

            return character_name, path

    def __is_trailblazer(self):
        char = self._screenshot.screenshot_character()
        for trailblazer in self._trailblazer_imgs:
            trailblazer = trailblazer.resize(char.size)
            if locate(char, trailblazer, confidence=0.8) is not None:
                return True

        return False
