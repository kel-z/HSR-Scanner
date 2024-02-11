from asyncio import Event

import cv2
import numpy as np
from PIL import Image as PILImage
from PIL.Image import Image
from pyautogui import locate
from PyQt6.QtCore import QSettings, pyqtBoundSignal

from enums.increment_type import IncrementType
from models.game_data import GameData
from utils.data import resource_path
from utils.ocr import image_to_string, preprocess_trace_img


class CharacterParser:
    """CharacterParser class containing all the logic for parsing characters"""

    def __init__(
        self,
        game_data: GameData,
        log_signal: pyqtBoundSignal,
        update_signal: pyqtBoundSignal,
        interrupt_event: Event,
    ) -> None:
        """Constructor

        :param game_data: The GameData class instance
        :param log_signal: The log signal
        :param update_signal: The update signal
        :param interrupt_event: The interrupt event
        """
        self._game_data = game_data
        self._log_signal = log_signal
        self._update_signal = update_signal
        self._interrupt_event = interrupt_event
        self._trailblazer_imgs = {
            "M": PILImage.open(resource_path("assets/images/trailblazerm.png")),
            "F": PILImage.open(resource_path("assets/images/trailblazerf.png")),
        }
        self._is_trailblazer_scanned = False

    def parse(self, stats_dict: dict) -> dict:
        """Parse the stats dictionary and return a character dictionary

        :param stats_dict: The stats dictionary
        :raises ValueError: If the level cannot be parsed
        :return: The character dictionary
        """
        if self._interrupt_event.is_set():
            return

        character = {
            "key": stats_dict["name"].split("#")[0],
            "level": 1,
            "ascension": stats_dict["ascension"],
            "eidolon": self._process_eidolons(stats_dict["eidolon_images"]),
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
            self._log_signal.emit(
                f"{character['key']}: Failed to parse level."
                + (f' Got "{level}" instead.' if level else "")
            )

        for eidolon in (5, 3):
            if character["eidolon"] >= eidolon:
                e_token = f"e{eidolon}"
                metadata = self._game_data.get_character_meta_data(character["key"])[
                    e_token
                ]
                for k, v in metadata.items():
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
                self._log_signal.emit(
                    f"{character['key']}: Failed to parse '{k}' level. "
                    + (f"Got '{res}' instead. " if res else "")
                    + "Setting to 1."
                )
                character["skills"][k] = 1

        character["traces"] = traces_dict["unlocks"]

        self._update_signal.emit(IncrementType.CHARACTER_SUCCESS.value)

        return character

    def get_closest_name_and_path(
        self, character_name: str, path: str, character_img: Image
    ) -> tuple[str, str]:
        """Get the closest name and path

        :param character_name: The character name
        :param path: The path
        :param character_img: The character image
        :raises Exception: If the character is not found in the database
        :return: The closest name and path
        """
        path, _ = self._game_data.get_closest_path_name(path)

        if self._is_trailblazer(character_img):
            if self._is_trailblazer_scanned:
                (
                    self._log_signal.emit(
                        "WARNING: Parsed more than one Trailblazer. Please review JSON output."
                    )
                    if self._log_signal
                    else None
                )
            else:
                self._is_trailblazer_scanned = True

            return "Trailblazer" + path.split(" ")[-1], path
        else:
            character_name, min_dist = self._game_data.get_closest_character_name(
                character_name
            )

            if min_dist > 5:
                raise Exception(
                    f'Failed to get a character name: got "{character_name}".'
                )

            return character_name, path

    def _is_trailblazer(self, character_img: Image) -> bool:
        """Check if the character is Trailblazer

        Side effect: Sets the is_stelle QSetting

        :param character_img: The character image
        :return: True if the character is Trailblazer, False otherwise
        """
        for k, trailblazer_img in self._trailblazer_imgs.items():
            trailblazer_img = trailblazer_img.resize(character_img.size)
            if locate(character_img, trailblazer_img, confidence=0.8) is not None:
                QSettings("kel-z", "HSR-Scanner").setValue("is_stelle", k == "F")
                return True

        return False

    def _process_eidolons(self, eidolon_images: list[Image]) -> int:
        """Process eidolons

        :param eidolon_images: The eidolon images
        :return: The number of eidolons unlocked
        """
        lower_orange = np.array([127, 104, 51])
        upper_orange = np.array([210, 175, 100])

        eidolon = 0
        for img_np in eidolon_images:
            img_bw = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            white = cv2.Laplacian(img_bw, cv2.CV_64F).var()

            # Eidolon is locked if the image is too dark
            if white < 10000:
                break

            mask = cv2.inRange(img_np, lower_orange, upper_orange)
            orange = cv2.countNonZero(mask)

            # Eidolon is unlocked but not activated if the image is too orange
            if orange > 200:
                break

            eidolon += 1

        return eidolon
