from utils.game_data import GameData
import Levenshtein as lev
import numpy as np
import pytesseract

# TODO: equipped, locked


class LightConeStrategy:
    scan_type = 0
    nav_data = {
        "16:9": {
            "inv_tab": (0.38, 0.06),
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

    def __init__(self, screenshot):
        self._screenshot = screenshot

    def screenshot_stats(self):
        return self._screenshot.screenshot_light_cone_stats()

    async def parse(self, stats_map):
        # Get each cropped img
        name = stats_map["name"]
        level = stats_map["level"]
        superimposition = stats_map["superimposition"]

        # OCR
        name = pytesseract.image_to_string(
            name, config="-c tessedit_char_whitelist=\"ABCDEFGHIJKLMNOPQRSTUVWXYZ \'abcedfghijklmnopqrstuvwxyz-\" --psm 6")
        level = pytesseract.image_to_string(
            level, config='-c tessedit_char_whitelist=0123456789/ --psm 7')
        superimposition = pytesseract.image_to_string(
            superimposition, config='-c tessedit_char_whitelist=12345 --psm 10')

        # Convert to strings
        name = name.strip()
        level = level.strip()
        superimposition = superimposition.strip()

        # Fix OCR errors
        name, _ = GameData.get_closest_light_cone_name(name)

        # Parse level, ascension, superimposition
        try:
            level, max_level = level.split("/")
            level = int(level)
            max_level = int(max_level)
        except ValueError:
            print("Failed to parse level for ", name, level)
            level = 1
            max_level = 20

        ascension = (max(max_level, 20) - 20) // 10
        superimposition = int(superimposition)

        result = {
            "name": name,
            "level": int(level),
            "ascension": int(ascension),
            "superimposition": int(superimposition)
        }

        print(result)

        return result
