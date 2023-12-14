from models.game_data import GameData
import numpy as np
from config.relic_scan import RELIC_NAV_DATA
from utils.data import resource_path
from utils.ocr import (
    image_to_string,
    preprocess_main_stat_img,
    preprocess_sub_stat_img,
    preprocess_equipped_img,
)
from PIL import Image
from pyautogui import locate
from enums.increment_type import IncrementType
from PyQt6.QtCore import pyqtBoundSignal
from asyncio import Event
from models.substat_vals import SUBSTAT_ROLL_VALS


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

    def get_optimal_sort_method(self, filters: dict) -> str:
        """Gets the optimal sort method based on the filters

        :param filters: The filters
        :return: The optimal sort method
        """
        if filters["relic"]["min_level"] > 0:
            return "Lv"
        else:
            return "Rarity"

    def check_filters(
        self, stats_dict: dict, filters: dict, relic_id: int
    ) -> tuple[dict, dict]:
        """Checks if the relic passes the filters

        :param stats_dict: The stats dict
        :param filters: The filters
        :param relic_id: The relic ID
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
                    level = self.extract_stats_data("level", stats_dict["level"])
                    if not level:
                        self._log_signal.emit(
                            f"Relic ID {relic_id}: Failed to parse level. Setting to 0."
                        )
                        level = 0
                    val = stats_dict["level"] = int(level)

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
        :return: The extracted data, or the image if the key is not relevant
        """
        match key:
            case "name":
                return image_to_string(
                    img, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 'abcedfghijklmnopqrstuvwxyz-", 6
                )
            case "level":
                return image_to_string(img, "0123456789S", 7).replace("S", "5")
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
            case "substat_names":
                return image_to_string(
                    img,
                    " ABCDEFGHIKMPRSTacefikrt",
                    6,
                    True,
                    preprocess_sub_stat_img,
                    False,
                )
            case "substat_vals":
                return image_to_string(
                    img, "0123456789S.%", 6, True, preprocess_sub_stat_img, False
                ).replace("S", "5")
            case _:
                return img

    def parse(self, stats_dict: dict, relic_id: int) -> dict:
        """Parses the relic data

        :param stats_dict: The stats dict
        :param relic_id: The relic ID
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
        substat_names = stats_dict["substat_names"]
        substat_vals = stats_dict["substat_vals"]

        # Fix OCR errors
        name, _ = self._game_data.get_closest_relic_name(name)
        main_stat_key, _ = self._game_data.get_closest_relic_main_stat(main_stat_key)
        if not level:
            self._log_signal.emit(
                f"Relic ID {relic_id}: Failed to extract level. Setting to 0."
            )
            level = 0
        level = int(level)

        # Substats
        while "\n\n" in substat_names:
            substat_names = substat_names.replace("\n\n", "\n")
        while "\n\n" in substat_vals:
            substat_vals = substat_vals.replace("\n\n", "\n")
        substat_names = substat_names.split("\n")
        substat_vals = substat_vals.split("\n")

        substats_res = self._parse_substats(
            substat_names, substat_vals, rarity, relic_id
        )
        self._validate_substats(substats_res, rarity, level, relic_id)

        # Set and slot
        metadata = self._game_data.get_relic_meta_data(name)
        set_key = metadata["set"]
        slot_key = metadata["slot"]

        # Check if locked by image matching
        min_dim = min(lock.size)
        lock_img = self._lock_icon.resize((min_dim, min_dim))
        lock = locate(lock_img, lock, confidence=0.1) is not None

        location = ""
        if equipped == "Equipped":
            equipped_avatar = stats_dict["equipped_avatar"]

            location = self._game_data.get_equipped_character(equipped_avatar)

        result = {
            "set": set_key,
            "slot": slot_key,
            "rarity": rarity,
            "level": level,
            "mainstat": main_stat_key,
            "substats": substats_res,
            "location": location,
            "lock": lock,
            "_id": f"relic_{relic_id}",
        }

        self._update_signal.emit(IncrementType.RELIC_SUCCESS.value)

        return result

    def _parse_substats(
        self, names: list[str], vals: list[str], rarity: int, relic_id: int
    ) -> list[dict[str, int | float]]:
        """Parses the substats

        :param names: The substat names
        :param vals: The substat values
        :param rarity: The rarity of the relic
        :param relic_id: The relic ID
        :return: The parsed substats
        """
        substats = []
        for i in range(len(names)):
            name = names[i]
            if not name:
                continue

            name, dist = self._game_data.get_closest_relic_sub_stat(name)
            if dist > 3:
                continue

            if i >= len(vals):
                self._log_signal.emit(
                    f"Relic ID {relic_id}: Failed to get value for substat: {name}."
                )
                continue
            val = vals[i]

            try:
                if "%" in val:
                    val = float(val[: val.index("%")])
                    name += "_"
                else:
                    val = int(val)
            except ValueError:
                if dist == 0:
                    self._log_signal.emit(
                        f"Relic ID {relic_id}: Failed to get value for substat: {name}. Error parsing substat value: {val}."
                    )
                continue

            if not self._validate_substat(name, val, rarity):
                self._log_signal.emit(
                    f"WARNING: Relic ID {relic_id}: Substat {name} has illegal value {val}."
                )

            substats.append({"key": name, "value": val})

        return substats

    def _validate_substat(self, name: str, val: int | float, rarity: int) -> bool:
        """Validates the substat

        :param name: The name of the substat
        :param val: The value of the substat
        :param rarity: The rarity of the relic
        :return: True if the substat is valid, False otherwise
        """
        try:
            if str(val) not in SUBSTAT_ROLL_VALS[str(rarity)][name]:
                return False
        except KeyError:
            return False

        return True

    def _validate_substats(
        self,
        substats: list[dict[str, int | float]],
        rarity: int,
        level: int,
        relic_id: int,
    ) -> None:
        """Rudimentary substat validation on number of substats based on rarity and level

        :param substats: The substats
        :param rarity: The rarity of the relic
        :param level: The level of the relic
        :param relic_id: The relic ID
        """
        substats_len = len(substats)
        min_substats = min(rarity - 2 + int(level / 3), 4)

        if substats_len < min_substats:
            self._log_signal.emit(
                f"WARNING: Relic ID {relic_id} has {substats_len} substats, but the minimum for rarity {rarity} and level {level} is {min_substats}."
            )
