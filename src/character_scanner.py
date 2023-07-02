from pyautogui import locate
from helper_functions import resource_path, image_to_string
from PIL import Image
from helper_functions import resource_path
from utils.game_data_helpers import get_character_meta_data, get_closest_character_name, get_closest_path_name
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
            "trailblazer": (0.3315, 0.4432, 0.126, 0.1037)
        }
    }

    def __init__(self, screenshot: Screenshot, logger, interrupt, update_progress) -> None:
        self.interrupt = interrupt
        self.update_progress = update_progress
        self._trailblazer_imgs = [
            Image.open(resource_path("images\\trailblazerm.png")),
            Image.open(resource_path("images\\trailblazerf.png"))
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
        level = image_to_string(level, "0123456789", 7, True)
        try:
            character["level"] = int(level)
        except ValueError:
            self._logger.emit(f"{character['key']}: Failed to parse level." +
                              (f" Got \"{level}\" instead." if level else "")) if self._logger else None

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
            v = image_to_string(v, "0123456789", 6, True)
            if not v:
                # Assuming level is max since it didn't parse any numbers
                if k == "basic":
                    v = 6
                else:
                    v = 10
                character["skills"][k] = v
            else:
                character["skills"][k] += int(v)

        for k, v in traces_dict["locks"].items():
            min_dim = min(v.size)
            lock_img = self._lock_img.resize((min_dim, min_dim))
            unlocked = locate(lock_img, v, confidence=0.2) is None
            character["traces"][k] = unlocked

        if self.update_progress:
            self.update_progress.emit(102)

        return character

    def get_traces_dict(self, path):
        path, _ = get_closest_path_name(path)

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

    def get_closest_name(self, character_name, path):
        if self.__is_trailblazer():
            if self._trailblazerScanned:
                self._logger.emit(
                    "WARNING: Parsed more than one Trailblazer. Please review JSON output.") if self._logger else None
            else:
                self._trailblazerScanned = True

            return "Trailblazer" + path.split(" ")[-1]
        else:
            character_name, min_dist = get_closest_character_name(
                character_name)

            if min_dist > 5:
                raise Exception(
                    f"Character not found in database. Got {character_name}")

            return character_name

    def __is_trailblazer(self):
        char = self._screenshot.screenshot_character()
        for trailblazer in self._trailblazer_imgs:
            trailblazer = trailblazer.resize(char.size)
            if locate(char, trailblazer, confidence=0.8) is not None:
                return True

        return False
