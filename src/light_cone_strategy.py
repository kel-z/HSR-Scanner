from utils.game_data import GameData
import pytesseract
from pyautogui import locate
from PIL import Image
from file_helpers import resource_path


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
            "row_start_top": (0.1, 0.185),
            "row_start_bottom": (0.1, 0.77),
            "scroll_start_y": 0.849,
            "scroll_end_y": 0.185,
            "offset_x": 0.075,
            "offset_y": 0.157,
            "rows": 4,
            "cols": 8
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
                    stats_dict["name"], _ = GameData.get_closest_light_cone_name(
                        stats_dict["name"])
                    val = GameData.get_light_cone_meta_data(
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
                    f"Filter key {key} does not have an int value.")

            if filter_type == "min":
                filter_results[key] = val >= filters[key]
            elif filter_type == "max":
                filter_results[key] = val <= filters[key]

        return (filter_results, stats_dict)

    def extract_stats_data(self, key, img):
        if key == "name":
            name, _ = GameData.get_closest_light_cone_name(pytesseract.image_to_string(
                img, config="-c tessedit_char_whitelist=\"ABCDEFGHIJKLMNOPQRSTUVWXYZ \'abcedfghijklmnopqrstuvwxyz-\" --psm 6").strip().replace("\n", " "))
            return name
        elif key == "level":
            return pytesseract.image_to_string(
                img, config='-c tessedit_char_whitelist=0123456789/ --psm 7').strip()
        elif key == "superimposition":
            return pytesseract.image_to_string(
                img, config='-c tessedit_char_whitelist=12345 --psm 10').strip()
        elif key == "equipped":
            return pytesseract.image_to_string(
                img, config='-c tessedit_char_whitelist=Equipped --psm 7').strip()
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
        if locate(locked, lock, confidence=0.1):
            lock = True
        else:
            lock = False

        location = ""
        if equipped == "Equipped":
            equipped_avatar = stats_dict["equipped_avatar"]

            location = GameData.get_equipped_character(
                equipped_avatar, resource_path("images\\avatars\\"))

        result = {
            "name": name,
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
