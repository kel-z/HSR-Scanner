from asyncio import Event

from PIL import Image as PILImage
from PIL.Image import Image
from pyautogui import locate
from PyQt6.QtCore import pyqtBoundSignal

from config.light_cone_scan import LIGHT_CONE_NAV_DATA
from enums.increment_type import IncrementType
from enums.log_level import LogLevel
from models.game_data import GameData
from utils.data import filter_images_from_dict, resource_path
from utils.ocr import (
    image_to_string,
    preprocess_equipped_img,
    preprocess_lc_level_img,
    preprocess_superimposition_img,
)


class LightConeStrategy:
    """LightConeStrategy class for parsing light cone data from screenshots."""

    SCAN_TYPE = IncrementType.LIGHT_CONE_ADD
    NAV_DATA = LIGHT_CONE_NAV_DATA

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
        """
        self._game_data = game_data
        self._log_signal = log_signal
        self._update_signal = update_signal
        self._interrupt_event = interrupt_event
        self._debug = debug
        self._lock_icon = PILImage.open(resource_path("assets/images/lock.png"))

    def get_optimal_sort_method(self, filters: dict) -> str:
        """Gets the optimal sort method based on the filters

        :param filters: The filters
        :return: The optimal sort method
        """
        if filters["light_cone"]["min_level"] > 1:
            return "Lv"
        else:
            return "Rarity"

    def check_filters(
        self, stats_dict: dict, filters: dict, lc_id: int
    ) -> tuple[dict, dict]:
        """Check if the stats dictionary passes the filters

        :param stats_dict: The stats dictionary
        :param filters: The filters
        :param lc_id: The ID of the light cone
        :raises ValueError: Thrown if the filter key does not have an int value
        :raises KeyError: Thrown if the filter key is not valid
        :return: The filter results and the stats dictionary
        """
        filters = filters["light_cone"]

        filter_results = {}
        for key in filters:
            filter_type, filter_key = key.split("_")

            val = stats_dict[filter_key] if filter_key in stats_dict else None

            if not val or isinstance(val, Image):
                if key == "min_rarity":
                    # Trivial case
                    if filters[key] <= 3:
                        filter_results[key] = True
                        continue
                    stats_dict["name"] = self.extract_stats_data(
                        "name", stats_dict["name"]
                    )
                    if not stats_dict["name"]:
                        self._log(
                            f'Light Cone ID {lc_id}: Failed to parse name. Setting to "Void".',
                            LogLevel.ERROR,
                        )
                        stats_dict["name"] = "Void"
                        filter_results[key] = True
                        continue
                    stats_dict["name"], _ = self._game_data.get_closest_light_cone_name(
                        stats_dict["name"]
                    )
                    val = self._game_data.get_light_cone_meta_data(stats_dict["name"])[
                        "rarity"
                    ]
                    stats_dict["rarity"] = val
                elif key == "min_level":
                    # Trivial case
                    if filters[key] <= 1:
                        filter_results[key] = True
                        continue
                    stats_dict["level"] = self.extract_stats_data(
                        "level", stats_dict["level"]
                    )
                    if not stats_dict["level"]:
                        self._log(
                            f"Light Cone ID {lc_id}: Failed to parse level. Setting to 1.",
                            LogLevel.ERROR,
                        )
                        stats_dict["level"] = "1/20"
                        filter_results[key] = True
                        continue
                    val = int(stats_dict["level"].split("/")[0])

            if not isinstance(val, int):
                raise ValueError(f'Filter key "{key}" does not have an int value.')

            if filter_type == "min":
                filter_results[key] = val >= filters[key]
            elif filter_type == "max":
                filter_results[key] = val <= filters[key]
            else:
                raise KeyError(f'"{key}" is not a valid filter.')

        return (filter_results, stats_dict)

    def extract_stats_data(self, key: str, img: Image) -> str | Image:
        """Extracts the stats data from the image

        :param key: The key
        :param img: The image
        :return: The extracted data, or the image if the key is not recognized
        """
        match key:
            case "name":
                name, _ = self._game_data.get_closest_light_cone_name(
                    image_to_string(
                        img,
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ 'abcedfghijklmnopqrstuvwxyz-",
                        6,
                    )
                )
                return name
            case "level":
                return image_to_string(
                    img, "0123456789S/", 7, True, preprocess_lc_level_img
                ).replace("S", "5")
            case "superimposition":
                return image_to_string(
                    img, "12345S", 10, True, preprocess_superimposition_img
                ).replace("S", "5")
            case "equipped":
                return image_to_string(
                    img, "Equipped", 7, True, preprocess_equipped_img
                )
            case _:
                return img

    def parse(self, stats_dict: dict, lc_id: int) -> dict:
        """Parses the stats dictionary

        :param stats_dict: The stats dictionary
        :param lc_id: The ID of the light cone
        :return: The parsed stats dictionary
        """
        if self._interrupt_event.is_set():
            return

        for key in stats_dict:
            if isinstance(stats_dict[key], Image):
                stats_dict[key] = self.extract_stats_data(key, stats_dict[key])

        (
            self._log(
                f"Light Cone ID {lc_id}: Raw data: {filter_images_from_dict(stats_dict)}",
                LogLevel.DEBUG,
            )
            if self._debug
            else None
        )

        name = stats_dict["name"]
        level = stats_dict["level"]
        superimposition = stats_dict["superimposition"]
        lock = stats_dict["lock"]
        equipped = stats_dict["equipped"]

        if not name:
            self._log(
                f'Light Cone ID {lc_id}: Failed to parse name. Setting to "Void".',
                LogLevel.ERROR,
            )
            name = "Void"

        # Parse level, ascension, superimposition
        try:
            level, max_level = level.split("/")
            level = int(level)
            max_level = int(max_level)
        except ValueError:
            self._log(
                f"Light Cone ID {lc_id}: Failed to parse level. Setting to 1.",
                LogLevel.ERROR,
            )
            level = 1
            max_level = 20

        ascension = (max(max_level, 20) - 20) // 10

        try:
            superimposition = int(superimposition)
        except ValueError:
            self._log(
                f"Light Cone ID {lc_id}: Failed to parse superimposition. Setting to 1.",
                LogLevel.ERROR,
            )
            superimposition = 1

        min_dim = min(lock.size)
        try:
            locked = self._lock_icon.resize((min_dim, min_dim))

            # Check if locked by image matching
            lock = locate(locked, lock, confidence=0.1) is not None
        except Exception:  # https://github.com/kel-z/HSR-Scanner/issues/41
            self._log(
                f"Light Cone ID {lc_id}: Failed to parse lock. Setting to False.",
                LogLevel.ERROR,
            )
            lock = False

        location = ""
        if equipped == "Equipped":
            equipped_avatar = stats_dict["equipped_avatar"]
            location = self._game_data.get_equipped_character(equipped_avatar)
        elif equipped == "Equippe":  # https://github.com/kel-z/HSR-Scanner/issues/88
            equipped_avatar = stats_dict["equipped_avatar_trailblazer"]
            location = self._game_data.get_equipped_character(equipped_avatar)

        result = {
            "key": name,
            "level": int(level),
            "ascension": int(ascension),
            "superimposition": int(superimposition),
            "location": location,
            "lock": lock,
            "_id": f"light_cone_{lc_id}",
        }

        self._update_signal.emit(IncrementType.LIGHT_CONE_SUCCESS.value)

        return result

    def _log(self, msg: str, level: LogLevel = LogLevel.INFO) -> None:
        """Logs a message

        :param msg: The message to log
        :param level: The log level
        """
        if self._debug or level in [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
            self._log_signal.emit((msg, level))
