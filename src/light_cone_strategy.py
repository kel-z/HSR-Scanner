from utils.game_data_helpers import get_closest_light_cone_name, get_light_cone_meta_data, get_equipped_character
from pyautogui import locate
from PIL import Image
from helper_functions import resource_path, image_to_string


class LightConeStrategy:
    SCAN_TYPE = 0
    NAV_DATA = {
        "16:9": {
            "inv_tab": (0.38, 0.06),
            "sort": {
                "button": (0.093, 0.91),
                "Rarity": (0.093, 0.49),
                "Lv": (0.093, 0.56),
            },
            "row_start_top": (0.096, 0.175),
            "row_start_bottom": (0.1, 0.77),
            "scroll_start_y": 0.849,
            "scroll_end_y": 0.124,
            "offset_x": 0.065,
            "offset_y": 0.13796,
            "rows": 5,
            "cols": 9
        }
    }

    def __init__(self, screenshot, logger):
        self._lock_icon = Image.open(resource_path("images\\lock.png"))
        self._screenshot = screenshot
        self._logger = logger
        self._curr_id = 0

    def screenshot_stats(self):
        return self._screenshot.screenshot_light_cone_stats()

    def screenshot_sort(self):
        return self._screenshot.screenshot_light_cone_sort()

    def get_optimal_sort_method(self, filters):
        if filters["light_cone"]["min_level"] > 1:
            return "Lv"
        else:
            return "Rarity"

    def check_filters(self, stats_dict, filters):
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
                        "name", stats_dict["name"])
                    stats_dict["name"], _ = get_closest_light_cone_name(
                        stats_dict["name"])
                    val = get_light_cone_meta_data(
                        stats_dict["name"])["rarity"]
                elif key == "min_level":
                    # Trivial case
                    if filters[key] <= 1:
                        filter_results[key] = True
                        continue
                    stats_dict["level"] = self.extract_stats_data(
                        "level", stats_dict["level"])
                    val = int(stats_dict["level"].split("/")[0])

            if not isinstance(val, int):
                raise ValueError(
                    f"Filter key \"{key}\" does not have an int value.")

            if filter_type == "min":
                filter_results[key] = val >= filters[key]
            elif filter_type == "max":
                filter_results[key] = val <= filters[key]
            else:
                raise KeyError(
                    f"\"{key}\" is not a valid filter.")

        return (filter_results, stats_dict)

    def extract_stats_data(self, key, img):
        if key == "name":
            name, _ = get_closest_light_cone_name(
                image_to_string(img, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 'abcedfghijklmnopqrstuvwxyz-", 6))
            return name
        elif key == "level":
            return image_to_string(img, "0123456789/", 7)
        elif key == "superimposition":
            return image_to_string(img, "12345", 10)
        elif key == "equipped":
            return image_to_string(img, "Equipped", 7)
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
                f"Light Cone ID {self._curr_id}: Error parsing level, setting to 1")
            level = 1
            max_level = 20

        ascension = (max(max_level, 20) - 20) // 10

        try:
            superimposition = int(superimposition)
        except ValueError:
            self._logger.emit(
                f"Light Cone ID {self._curr_id}: Error parsing superimposition, setting to 1")
            superimposition = 1

        min_dim = min(lock.size)
        locked = self._lock_icon.resize((min_dim, min_dim))

        # Check if locked by image matching
        lock = locate(locked, lock, confidence=0.1) is not None

        location = ""
        if equipped == "Equipped":
            equipped_avatar = stats_dict["equipped_avatar"]

            location = get_equipped_character(
                equipped_avatar, resource_path("images\\avatars\\"))

        result = {
            "key": name,
            "level": int(level),
            "ascension": int(ascension),
            "superimposition": int(superimposition),
            "location": location,
            "lock": lock,
            "_id": f"light_cone_{self._curr_id}"
        }

        update_progress.emit(100)
        self._curr_id += 1

        return result
