from models.game_data import GameData
from pyautogui import locate
from PIL import Image
from utils.helpers import resource_path, image_to_string
from config.light_cone_scan import LIGHT_CONE_NAV_DATA
from enums.increment_type import IncrementType
from utils.screenshot import Screenshot
from PyQt6.QtCore import pyqtBoundSignal
from asyncio import Event


class LightConeStrategy:
    """LightConeStrategy class for parsing light cone data from screenshots."""

    SCAN_TYPE = IncrementType.LIGHT_CONE_ADD
    NAV_DATA = LIGHT_CONE_NAV_DATA

    def __init__(
        self, game_data: GameData, screenshot: Screenshot, logger: pyqtBoundSignal
    ) -> None:
        """Constructor

        :param game_data: The GameData class instance
        :param screenshot: The Screenshot class instance
        :param logger: The logger signal
        """
        self._game_data = game_data
        self._lock_icon = Image.open(resource_path("assets/images/lock.png"))
        self._screenshot = screenshot
        self._logger = logger
        self._curr_id = 1

    def screenshot_stats(self) -> Image:
        """Takes a screenshot of the light cone stats

        :return: The screenshot
        """
        return self._screenshot.screenshot_light_cone_stats()

    def screenshot_sort(self) -> Image:
        """Takes a screenshot of the light cone sort

        :return: The screenshot
        """
        return self._screenshot.screenshot_light_cone_sort()

    def get_optimal_sort_method(self, filters: dict) -> str:
        """Gets the optimal sort method based on the filters

        :param filters: The filters
        :return: The optimal sort method
        """
        if filters["light_cone"]["min_level"] > 1:
            return "Lv"
        else:
            return "Rarity"

    def check_filters(self, stats_dict: dict, filters: dict) -> tuple[dict, dict]:
        """Check if the stats dictionary passes the filters

        :param stats_dict: The stats dictionary
        :param filters: The filters
        :raises ValueError: Thrown if the filter key does not have an int value
        :raises KeyError: Thrown if the filter key is not valid
        :return: The filter results and the stats dictionary
        """
        filters = filters["light_cone"]

        filter_results = {}
        for key in filters:
            filter_type, filter_key = key.split("_")

            val = stats_dict[filter_key] if filter_key in stats_dict else None

            if not val or isinstance(val, Image.Image):
                if key == "min_rarity":
                    # Trivial case
                    if filters[key] <= 3:
                        filter_results[key] = True
                        continue
                    stats_dict["name"] = self.extract_stats_data(
                        "name", stats_dict["name"]
                    )
                    stats_dict["name"], _ = self._game_data.get_closest_light_cone_name(
                        stats_dict["name"]
                    )
                    val = self._game_data.get_light_cone_meta_data(stats_dict["name"])[
                        "rarity"
                    ]
                elif key == "min_level":
                    # Trivial case
                    if filters[key] <= 1:
                        filter_results[key] = True
                        continue
                    stats_dict["level"] = self.extract_stats_data(
                        "level", stats_dict["level"]
                    )
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

    def extract_stats_data(self, key: str, img: Image):
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
                return image_to_string(img, "0123456789/", 7)
            case "superimposition":
                return image_to_string(img, "12345", 10)
            case "equipped":
                return image_to_string(img, "Equipped", 7)
            case _:
                return img

    def parse(
        self,
        stats_dict: dict,
        interrupt: Event,
        update_progress: pyqtBoundSignal,
    ) -> dict:
        """Parses the stats dictionary

        :param stats_dict: The stats dictionary
        :param interrupt: The interrupt event
        :param update_progress: The update progress signal
        :return: The parsed stats dictionary
        """
        if interrupt.is_set():
            return

        for key in stats_dict:
            if isinstance(stats_dict[key], Image.Image):
                stats_dict[key] = self.extract_stats_data(key, stats_dict[key])

        name = stats_dict["name"]
        level = stats_dict["level"]
        superimposition = stats_dict["superimposition"]
        lock = stats_dict["lock"]
        equipped = stats_dict["equipped"]

        # Parse level, ascension, superimposition
        try:
            level, max_level = level.split("/")
            level = int(level)
            max_level = int(max_level)
        except ValueError:
            self._logger.emit(
                f"Light Cone ID {self._curr_id}: Error parsing level, setting to 1"
            ) if self._logger else None
            level = 1
            max_level = 20

        ascension = (max(max_level, 20) - 20) // 10

        try:
            superimposition = int(superimposition)
        except ValueError:
            self._logger.emit(
                f"Light Cone ID {self._curr_id}: Error parsing superimposition, setting to 1"
            ) if self._logger else None
            superimposition = 1

        min_dim = min(lock.size)
        locked = self._lock_icon.resize((min_dim, min_dim))

        # Check if locked by image matching
        lock = locate(locked, lock, confidence=0.1) is not None

        location = ""
        if equipped == "Equipped":
            equipped_avatar = stats_dict["equipped_avatar"]

            location = self._game_data.get_equipped_character(equipped_avatar)

        result = {
            "key": name,
            "level": int(level),
            "ascension": int(ascension),
            "superimposition": int(superimposition),
            "location": location,
            "lock": lock,
            "_id": f"light_cone_{self._curr_id}",
        }

        update_progress.emit(IncrementType.LIGHT_CONE_SUCCESS.value)
        self._curr_id += 1

        return result
