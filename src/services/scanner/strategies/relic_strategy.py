from models.game_data import GameData
import numpy as np
from config.relic_scan import RELIC_NAV_DATA
from utils.helpers import (
    resource_path,
    image_to_string,
    preprocess_main_stat_img,
    preprocess_equipped_img,
)
from PIL import Image
from pyautogui import locate
from enums.increment_type import IncrementType
from PyQt6.QtCore import pyqtBoundSignal
from asyncio import Event


class RelicStrategy:
    """RelicStrategy class for parsing relic data from screenshots."""

    SCAN_TYPE = IncrementType.RELIC_ADD
    NAV_DATA = RELIC_NAV_DATA

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
        self._lock_icon = Image.open(resource_path("assets/images/lock.png"))
        self._curr_id = 1

    def get_optimal_sort_method(self, filters: dict) -> str:
        """Gets the optimal sort method based on the filters

        :param filters: The filters
        :return: The optimal sort method
        """
        if filters["relic"]["min_level"] > 0:
            return "Lv"
        else:
            return "Rarity"

    def check_filters(self, stats_dict: dict, filters: dict) -> tuple[dict, dict]:
        """Checks if the relic passes the filters

        :param stats_dict: The stats dict
        :param filters: The filters
        :raises ValueError: Thrown if the filter key does not have an int value
        :return: A tuple of the filter results and the stats dict
        """
        filters = filters["relic"]

        filter_results = {}
        for key in filters:
            filter_type, filter_key = key.split("_")

            val = stats_dict[filter_key] if filter_key in stats_dict else None

            if not val or isinstance(val, Image.Image):
                if key == "min_rarity":
                    # Trivial case
                    if filters[key] <= 2:
                        filter_results[key] = True
                        continue
                    val = stats_dict["rarity"] = self.extract_stats_data(
                        filter_key, stats_dict["rarity"]
                    )
                elif key == "min_level":
                    # Trivial case
                    if filters[key] <= 0:
                        filter_results[key] = True
                        continue
                    val = stats_dict["level"] = self.extract_stats_data(
                        "level", stats_dict["level"]
                    )

            if not isinstance(val, int):
                raise ValueError(f"Filter key {key} does not have an int value.")

            if filter_type == "min":
                filter_results[key] = val >= filters[key]
            elif filter_type == "max":
                filter_results[key] = val <= filters[key]

        return (filter_results, stats_dict)

    def extract_stats_data(self, key: str, img: Image):
        """Extracts the stats data from the image

        :param key: The key
        :param img: The image
        :return: The extracted data, or the image if the key is not recognized
        """
        match key:
            case "name":
                return image_to_string(
                    img, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 'abcedfghijklmnopqrstuvwxyz-", 6
                )
            case "level":
                level = image_to_string(img, "0123456789", 7)
                if not level:
                    self._log_signal.emit(
                        f"Relic ID {self._curr_id}: Failed to extract level. Setting to 0."
                    )
                    level = 0
                return int(level)
            case "mainStatKey":
                return image_to_string(
                    img,
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz",
                    7,
                    True,
                    preprocess_main_stat_img,
                )
            case "equipped":
                return image_to_string(img, "Equiped", 7, True, preprocess_equipped_img)
            case "rarity":
                # Get rarity by color matching
                rarity_sample = np.array(img)
                rarity_sample = rarity_sample[int(rarity_sample.shape[0] / 2)][
                    int(rarity_sample.shape[1] / 2)
                ]
                return self._game_data.get_closest_rarity(rarity_sample)
            case _:
                return img

    def parse(self, stats_dict: dict) -> dict:
        """Parses the relic data

        :param stats_dict: The stats dict
        :return: The parsed relic data
        """
        if self._interrupt_event.is_set():
            return

        for key in stats_dict:
            if isinstance(stats_dict[key], Image.Image):
                stats_dict[key] = self.extract_stats_data(key, stats_dict[key])

        name = stats_dict["name"]
        level = stats_dict["level"]
        main_stat_key = stats_dict["mainStatKey"]
        lock = stats_dict["lock"]
        rarity = stats_dict["rarity"]
        equipped = stats_dict["equipped"]

        # Fix OCR errors
        name, _ = self._game_data.get_closest_relic_name(name)
        main_stat_key, _ = self._game_data.get_closest_relic_main_stat(main_stat_key)

        # Parse sub-stats
        sub_stats = []
        for i in range(1, 5):
            sub_stat_img = stats_dict["subStat_" + str(i)]

            parsed_sub_stat_str = image_to_string(
                sub_stat_img,
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz 0123456789.%",
                7,
                True,
            )
            if not parsed_sub_stat_str:
                break

            try:
                key, val = parsed_sub_stat_str.rsplit(" ", 1)
                val = val.strip()
            except ValueError:
                break

            key, min_dist = self._game_data.get_closest_relic_sub_stat(key.strip())
            if min_dist > 5:
                break

            if not val or val == ".":
                if min_dist == 0:
                    self._log_signal.emit(
                        f"Relic ID {self._curr_id}: Failed to get value for sub-stat: {key}. Either it doesn't exist or the OCR failed."
                    )
                break

            try:
                if val[-1] == "%":
                    val = float(val[:-1])
                    key += "_"
                else:
                    val = int(val)
            except ValueError:
                if min_dist == 0:
                    self._log_signal.emit(
                        f"Relic ID {self._curr_id}: Failed to get value for sub-stat: {key}. Error parsing sub-stat value: {val}."
                    )
                break

            sub_stats.append({"key": key, "value": val})

        metadata = self._game_data.get_relic_meta_data(name)
        set_key = metadata["setKey"]
        slot_key = metadata["slotKey"]

        # Check if locked by image matching
        min_dim = min(lock.size)
        lock_img = self._lock_icon.resize((min_dim, min_dim))
        lock = locate(lock_img, lock, confidence=0.1) is not None

        location = ""
        if equipped == "Equipped":
            equipped_avatar = stats_dict["equipped_avatar"]

            location = self._game_data.get_equipped_character(equipped_avatar)

        result = {
            "setKey": set_key,
            "slotKey": slot_key,
            "rarity": rarity,
            "level": level,
            "mainStatKey": main_stat_key,
            "subStats": sub_stats,
            "location": location,
            "lock": lock,
            "_id": f"relic_{self._curr_id}",
        }

        self._update_signal.emit(IncrementType.RELIC_SUCCESS.value)
        self._curr_id += 1

        return result
