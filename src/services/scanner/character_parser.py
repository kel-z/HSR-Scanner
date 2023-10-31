from pyautogui import locate
from utils.helpers import resource_path, image_to_string
from PIL import Image
from utils.helpers import resource_path, preprocess_trace_img
from models.game_data import GameData
from utils.screenshot import Screenshot
from PyQt6.QtCore import pyqtBoundSignal


class CharacterParser:
    """CharacterParser class containing all the logic for parsing characters"""

    def __init__(
        self,
        game_data: GameData,
        screenshot: Screenshot,
        logger: pyqtBoundSignal,
        interrupt: pyqtBoundSignal,
        update_progress: pyqtBoundSignal,
    ) -> None:
        """Constructor

        :param game_data: The GameData class instance
        :param screenshot: The Screenshot class instance
        :param logger: The logger signal
        :param interrupt: The interrupt signal
        :param update_progress: The update progress signal
        """
        self._game_data = game_data
        self.interrupt = interrupt
        self.update_progress = update_progress
        self._trailblazer_imgs = [
            Image.open(resource_path("assets/images/trailblazerm.png")),
            Image.open(resource_path("assets/images/trailblazerf.png")),
        ]
        self._lock_img = Image.open(resource_path("assets/images/lock2.png"))
        self._screenshot = screenshot
        self._logger = logger
        self._trailblazerScanned = False

    def parse(self, stats_dict: dict, eidolon_images: list[Image.Image]) -> dict:
        """Parse the stats dictionary and return a character dictionary

        :param stats_dict: The stats dictionary
        :param eidolon_images: The eidolon images
        :raises ValueError: If the level cannot be parsed
        :return: The character dictionary
        """
        if self.interrupt.is_set():
            return

        character = {
            "key": stats_dict["name"].split("#")[0],
            "level": 1,
            "ascension": stats_dict["ascension"],
            "eidolon": 0,
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

        for img in eidolon_images:
            img = img.convert("L")
            min_dim = min(img.size)
            lock_img = self._lock_img.resize((min_dim, min_dim))
            unlocked = locate(lock_img, img, confidence=0.8) is None
            if not unlocked:
                break

            character["eidolon"] += 1

        if character["eidolon"] >= 5:
            character["skills"]["basic"] -= 1
            character["skills"]["skill"] -= 2
            character["skills"]["ult"] -= 2
            character["skills"]["talent"] -= 2
        elif character["eidolon"] >= 3:
            for k, v in self._game_data.get_character_meta_data(character["key"])[
                "e3"
            ].items():
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
                if not 1 <= character["skills"][k] <= (6 if k == "basic" else 10):
                    raise ValueError
            except ValueError:
                self._logger.emit(
                    f"{character['key']}: Failed to parse '{k}' level. "
                    + (f"Got '{res}' instead. " if res else "")
                    + "Setting to 1."
                ) if self._logger else None
                print(character)
                print(stats_dict)
                character["skills"][k] = 1

        character["traces"] = traces_dict["unlocks"]

        if self.update_progress:
            self.update_progress.emit(102)

        return character

    def get_traces_levels_dict(self, path: str) -> dict:
        """Get the traces levels dictionary

        :param path: The path
        :raises ValueError: If the path is invalid
        :return: The traces levels dictionary
        """
        match path:
            case "The Hunt":
                return self._screenshot.screenshot_character_hunt_traces()
            case "Erudition":
                return self._screenshot.screenshot_character_erudition_traces()
            case "Harmony":
                return self._screenshot.screenshot_character_harmony_traces()
            case "Preservation":
                return self._screenshot.screenshot_character_preservation_traces()
            case "Destruction":
                return self._screenshot.screenshot_character_destruction_traces()
            case "Nihility":
                return self._screenshot.screenshot_character_nihility_traces()
            case "Abundance":
                return self._screenshot.screenshot_character_abundance_traces()
            case _:
                raise ValueError("Invalid path")

    def get_closest_name_and_path(
        self, character_name: str, path: str
    ) -> tuple[str, str]:
        """Get the closest name and path

        :param character_name: The character name
        :param path: The path
        :raises Exception: If the character is not found in the database
        :return: The closest name and path
        """
        path, _ = self._game_data.get_closest_path_name(path)

        if self._is_trailblazer():
            if self._trailblazerScanned:
                self._logger.emit(
                    "WARNING: Parsed more than one Trailblazer. Please review JSON output."
                ) if self._logger else None
            else:
                self._trailblazerScanned = True

            return "Trailblazer" + path.split(" ")[-1], path
        else:
            character_name, min_dist = self._game_data.get_closest_character_name(
                character_name
            )

            if min_dist > 5:
                raise Exception(
                    f"Character not found in database. Got {character_name}"
                )

            return character_name, path

    def _is_trailblazer(self) -> bool:
        """Check if the character is Trailblazer

        :return: True if the character is Trailblazer, False otherwise
        """
        char = self._screenshot.screenshot_character()
        for trailblazer in self._trailblazer_imgs:
            trailblazer = trailblazer.resize(char.size)
            if locate(char, trailblazer, confidence=0.8) is not None:
                return True

        return False
