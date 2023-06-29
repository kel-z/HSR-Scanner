from utils.game_data_helpers import get_closest_rarity, get_closest_relic_name, get_relic_meta_data, get_closest_relic_sub_stat, get_equipped_character, get_closest_relic_main_stat
import numpy as np
from helper_functions import resource_path, image_to_string
from PIL import Image
from pyautogui import locate


class RelicStrategy:
    SCAN_TYPE = 1
    NAV_DATA = {
        "16:9": {
            "inv_tab": (0.43, 0.06),
            "sort": {
                "button": (0.12, 0.91),
                "Rarity": (0.12, 0.7),
                "Lv": (0.12, 0.77),
            },
            "row_start_top": (0.096875, 0.242),
            "row_start_bottom": (0.096875, 0.776),
            "scroll_start_y": 0.7944,
            "scroll_end_y": 0.2135,
            "offset_x": 0.065,
            "offset_y": 0.13796,
            "rows": 4,
            "cols": 9
        }
    }

    def __init__(self, screenshot, logger):
        self._lock_icon = Image.open(resource_path("images\\lock.png"))
        self._screenshot = screenshot
        self._logger = logger
        self._curr_id = 0

    def screenshot_stats(self):
        return self._screenshot.screenshot_relic_stats()

    def screenshot_sort(self):
        return self._screenshot.screenshot_relic_sort()

    def get_optimal_sort_method(self, filters):
        if filters["relic"]["min_level"] > 0:
            return "Lv"
        else:
            return "Rarity"

    def check_filters(self, stats_dict, filters):
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
                        filter_key, stats_dict["rarity"])
                elif key == "min_level":
                    # Trivial case
                    if filters[key] <= 0:
                        filter_results[key] = True
                        continue
                    val = stats_dict["level"] = self.extract_stats_data(
                        "level", stats_dict["level"])

            if not isinstance(val, int):
                raise ValueError(
                    f"Filter key {key} does not have an int value.")

            if filter_type == "min":
                filter_results[key] = val >= filters[key]
            elif filter_type == "max":
                filter_results[key] = val <= filters[key]

        return (filter_results, stats_dict)

    def extract_stats_data(self, key, img):
        if key == "name":
            return image_to_string(img, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 'abcedfghijklmnopqrstuvwxyz-", 6)
        elif key == "level":
            level = image_to_string(img, "0123456789", 7)
            if not level:
                self._logger.emit(
                    f"Relic ID {self._curr_id}: Failed to extract level. Setting to 0."
                ) if self._logger else None
                level = 0
            return int(level)
        elif key == "mainStatKey":
            return image_to_string(img, "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz", 7)
        elif key == "equipped":
            return image_to_string(img, "Equiped", 7)
        elif key == "rarity":
            # Get rarity by color matching
            rarity_sample = np.array(img)
            rarity_sample = rarity_sample[int(
                rarity_sample.shape[0]/2)][int(rarity_sample.shape[1]/2)]
            return get_closest_rarity(rarity_sample)
        else:
            return img

    def parse(self, stats_dict, interrupt, update_progress):
        if interrupt.is_set():
            return

        for key in stats_dict:
            if isinstance(stats_dict[key], Image.Image):
                stats_dict[key] = self.extract_stats_data(key, stats_dict[key])

        name = stats_dict["name"]
        level = stats_dict["level"]
        mainStatKey = stats_dict["mainStatKey"]
        lock = stats_dict["lock"]
        rarity = stats_dict["rarity"]
        equipped = stats_dict["equipped"]

        # Fix OCR errors
        name, _ = get_closest_relic_name(name)
        mainStatKey, _ = get_closest_relic_main_stat(mainStatKey)

        # Parse sub-stats
        subStats = []
        for i in range(1, 5):
            key = stats_dict["subStatKey_" + str(i)]

            key = image_to_string(
                key, "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz", 7)
            if not key:
                # self._logger.emit(
                #     f"Relic ID {self._curr_id}: Failed to get key. Either it doesn't exist or the OCR failed.") if self._logger else None
                break
            key, min_dist = get_closest_relic_sub_stat(key)
            if min_dist > 5:
                break

            val_img = stats_dict["subStatVal_" + str(i)]
            val = image_to_string(val_img, "0123456789.%", 7)
            if not val:
                # self._logger.emit(
                #     f"Relic ID {self._curr_id}: Found sub-stat with no value: {key}. Either it doesn't exist or the OCR failed.") if self._logger else None
                break

            if val[-1] == '%':
                if '.' not in val:
                    val = image_to_string(
                        val_img, "0123456789.%", 7, True)
                val = float(val[:-1])
                key += '_'
            else:
                val = int(val)

            subStats.append(
                {
                    "key": key,
                    "value": val
                }
            )

        metadata = get_relic_meta_data(name)
        setKey = metadata["setKey"]
        slotKey = metadata["slotKey"]

        # Check if locked by image matching
        min_dim = min(lock.size)
        lock_img = self._lock_icon.resize((min_dim, min_dim))
        lock = locate(lock_img, lock, confidence=0.1) is not None

        location = ""
        if equipped == "Equipped":
            equipped_avatar = stats_dict["equipped_avatar"]

            location = get_equipped_character(
                equipped_avatar, resource_path("images\\avatars\\"))

        result = {
            "setKey": setKey,
            "slotKey": slotKey,
            "rarity": rarity,
            "level": level,
            "mainStatKey": mainStatKey,
            "subStats": subStats,
            "location": location,
            "lock": lock,
            "_id": f"relic_{self._curr_id}"
        }

        update_progress.emit(101)
        self._curr_id += 1

        return result
