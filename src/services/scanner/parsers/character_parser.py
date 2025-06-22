from asyncio import Event

import cv2
import numpy as np
from PIL import Image as PILImage
from PIL.Image import Image
from pyautogui import locate
from PyQt6.QtCore import QSettings, pyqtBoundSignal

from enums.increment_type import IncrementType
from enums.log_level import LogLevel
from models.const import (
    CAELUS_ICON_PATH,
    CHAR_NAME,
    CHAR_PATH,
    CHAR_ID,
    CHAR_ASCENSION,
    CHAR_EIDOLON,
    EIDOLON_IMAGES,
    HSR_SCANNER,
    IS_STELLE,
    KEL_Z,
    CHAR_MEMOSPRITE,
    CHAR_LEVEL,
    CHAR_SKILLS,
    CHAR_TRACES,
    BASIC,
    SKILL,
    STELLE_ICON_PATH,
    TALENT,
    ULT,
    TRACES_LEVELS,
    TRACES_UNLOCKS,
)
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
        debug: bool = False,
    ) -> None:
        """Constructor

        :param game_data: The GameData class instance
        :param log_signal: The log signal
        :param update_signal: The update signal
        :param interrupt_event: The interrupt event
        :param debug: Whether to run in debug mode, defaults to False
        """
        self._game_data = game_data
        self._log_signal = log_signal
        self._update_signal = update_signal
        self._interrupt_event = interrupt_event
        self._debug = debug
        self._trailblazer_imgs = {
            "M": PILImage.open(resource_path(CAELUS_ICON_PATH)),
            "F": PILImage.open(resource_path(STELLE_ICON_PATH)),
        }
        self._is_trailblazer_scanned = False

    def parse(self, stats_dict: dict) -> dict:
        """Parse the stats dictionary and return a character dictionary

        :param stats_dict: The stats dictionary
        :raises ValueError: If the level cannot be parsed
        :return: The character dictionary
        """
        if self._interrupt_event.is_set():
            return {}

        try:
            name = stats_dict[CHAR_NAME]
            path = stats_dict[CHAR_PATH]
            metadata = self._game_data.get_character_meta_data(name, path)
            char_id = str(metadata[CHAR_ID])

            # Output
            character = {
                CHAR_ID: char_id,
                CHAR_NAME: name,
                CHAR_PATH: path,
                CHAR_LEVEL: 1,
                CHAR_ASCENSION: stats_dict[CHAR_ASCENSION],
                CHAR_EIDOLON: self._process_eidolons(stats_dict[EIDOLON_IMAGES]),
                CHAR_SKILLS: {
                    BASIC: 0,
                    SKILL: 0,
                    ULT: 0,
                    TALENT: 0,
                },
                CHAR_TRACES: {},
            }

            if path == "Remembrance":
                character[CHAR_MEMOSPRITE] = {
                    SKILL: 0,
                    TALENT: 0,
                }

            level = stats_dict[CHAR_LEVEL]
            try:
                character[CHAR_LEVEL] = self.get_level(level)
            except ValueError:
                self._log(
                    f"{character[CHAR_NAME]}: Failed to parse level."
                    + (f' Got "{level}" instead.' if level else ""),
                    LogLevel.ERROR,
                )

            for eidolon in (5, 3):
                if character[CHAR_EIDOLON] >= eidolon:
                    e_token = f"e{eidolon}"
                    for k, v in metadata[e_token].items():
                        if k == CHAR_MEMOSPRITE:
                            for k2, v2 in v.items():
                                character[CHAR_MEMOSPRITE][k2] -= v2
                        else:
                            character[CHAR_SKILLS][k] -= v

            traces_dict = stats_dict[CHAR_TRACES]
            for k, v in traces_dict[TRACES_LEVELS].items():
                try:
                    res = image_to_string(
                        v, "0123456789/", 6, True, preprocess_trace_img
                    )

                    # If the first OCR attempt failed, try again with different parameters
                    if not res or "/" not in res:
                        self._log(
                            f"{character[CHAR_NAME]}: Failed to parse '{k}' level. Trying again with PSM 6 and no force preprocess.",
                            LogLevel.DEBUG,
                        )
                        res = image_to_string(
                            v, "0123456789/", 6, False, preprocess_trace_img
                        )
                    if not res or "/" not in res:
                        self._log(
                            f"{character[CHAR_NAME]}: Failed to parse '{k}' level. Trying again with PSM 7 and force preprocess.",
                            LogLevel.DEBUG,
                        )
                        res = image_to_string(
                            v, "0123456789/", 7, True, preprocess_trace_img
                        )
                    if not res or "/" not in res:
                        self._log(
                            f"{character[CHAR_NAME]}: Failed to parse '{k}' level. Trying again with PSM 7 and no force preprocess.",
                            LogLevel.DEBUG,
                        )
                        res = image_to_string(
                            v, "0123456789/", 7, False, preprocess_trace_img
                        )

                    if k.startswith(CHAR_MEMOSPRITE):
                        key = k.split("_")[1]
                        character[CHAR_MEMOSPRITE][key] += int(res.split("/")[0])
                        if not 1 <= character[CHAR_MEMOSPRITE][key] <= 6:
                            raise ValueError
                    else:
                        character[CHAR_SKILLS][k] += int(res.split("/")[0])
                        if (
                            not 1
                            <= character[CHAR_SKILLS][k]
                            <= (6 if k == "basic" else 10)
                        ):
                            raise ValueError
                except ValueError:
                    self._log(
                        f"{character[CHAR_NAME]}: Failed to parse '{k}' level. "
                        + (f"Got '{res}' instead. " if res else "")
                        + "Setting to 1.",
                        LogLevel.ERROR,
                    )
                    character[CHAR_SKILLS][k] = 1

            character[CHAR_TRACES] = traces_dict[TRACES_UNLOCKS]

            self._update_signal.emit(IncrementType.CHARACTER_SUCCESS.value)

            return character
        except Exception as e:
            self._log(
                f"Failed to parse character. stats_dict={stats_dict}, exception={e}",
                LogLevel.ERROR,
            )
            return {}

    def get_level(self, level: Image | str | int) -> int:
        """Get the level if level is an image, otherwise return the level as is

        :param level: The level image, string, or integer
        :return: The level
        """
        if isinstance(level, int):
            return level

        if isinstance(level, Image):
            res = image_to_string(level, "0123456789", 7, True)
            if not res or not res.isdigit():
                res = image_to_string(level, "0123456789", 6, True)

        if not res.isdigit():
            self._log(
                f"Failed to parse level. Got '{res}' instead. Setting to 1.",
                LogLevel.ERROR,
            )
            return 1

        return int(res)

    def get_closest_name_and_path(
        self, name: str, path: str, is_trailblazer: bool
    ) -> tuple[str, str]:
        """Get the closest name and path

        :param name: The parsed name
        :param path: The path
        :param is_trailblazer: Whether the character is Trailblazer
        :raises Exception: If the character is not found in the database
        :return: The closest character name and path
        """
        path, _ = self._game_data.get_closest_path_name(path)

        if is_trailblazer:
            if self._is_trailblazer_scanned:
                self._log(
                    "Parsed more than one Trailblazer. Please review JSON output.",
                    LogLevel.ERROR,
                )
            else:
                self._is_trailblazer_scanned = True

            return "Trailblazer", path
        else:
            character_name, min_dist = self._game_data.get_closest_character_name(name)
            self._log(
                f'Got character name "{character_name}" for string "{name}" with distance {min_dist} out of max 5.',
                LogLevel.TRACE,
            )

            if int(min_dist) > 5:
                raise Exception(
                    f'Failed to get a character name: got "{character_name}".'
                )

            return character_name, path

    def is_trailblazer(self, character_img: Image) -> bool:
        """Check if the character is Trailblazer

        Side effect: Sets the is_stelle QSetting

        :param character_img: The character image
        :return: True if the character is Trailblazer, False otherwise
        """
        for k, trailblazer_img in self._trailblazer_imgs.items():
            trailblazer_img = trailblazer_img.resize(character_img.size)
            if locate(character_img, trailblazer_img, confidence=0.8) is not None:
                QSettings(KEL_Z, HSR_SCANNER).setValue(IS_STELLE, k == "F")
                self._log(
                    f'{"Stelle" if k == "F" else "Caelus"} detected.', LogLevel.DEBUG
                )
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
        for img in eidolon_images:
            img_bw = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # type: ignore
            white = cv2.Laplacian(img_bw, cv2.CV_64F).var()  # type: ignore

            # Eidolon is locked if the image is too dark
            if white < 10000:
                break

            mask = cv2.inRange(img, lower_orange, upper_orange)  # type: ignore
            orange = cv2.countNonZero(mask)  # type: ignore

            # Eidolon is unlocked but not activated if the image is too orange
            if orange > 200:
                break

            eidolon += 1

        return eidolon

    def _log(self, msg: str, level: LogLevel = LogLevel.INFO) -> None:
        """Logs a message

        :param msg: The message to log
        :param level: The log level
        """
        if self._debug or level in [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
            self._log_signal.emit((msg, level))
