from utils.game_data import GameData
import Levenshtein as lev
import numpy as np
import pytesseract

# TODO: equipped, locked


class RelicStrategy:
    scan_type = 1
    nav_data = {
        "16:9": {
            "inv_tab": (0.43, 0.06),
            "row_start_top": (0.1, 0.25),
            "row_start_bottom": (0.1, 0.77),
            "scroll_start_y": 0.85,
            "scroll_end_y": 0.186,
            "offset_x": 0.075,
            "offset_y": 0.157,
            "rows": 4,
            "cols": 8
        }
    }

    def __init__(self, screenshot):
        self._screenshot = screenshot

    def screenshot_stats(self):
        return self._screenshot.screenshot_relic_stats()

    async def parse(self, stats_map):
        # Get each np array
        name = stats_map["name"]
        level = stats_map["level"]
        mainStatKey = stats_map["mainStatKey"]

        # OCR
        name = pytesseract.image_to_string(
            name, config="-c tessedit_char_whitelist=\"ABCDEFGHIJKLMNOPQRSTUVWXYZ \'abcedfghijklmnopqrstuvwxyz-\" --psm 6")
        level = pytesseract.image_to_string(
            level, config='-c tessedit_char_whitelist=0123456789 --psm 7')
        mainStatKey = pytesseract.image_to_string(
            mainStatKey, config='-c tessedit_char_whitelist=\'ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz\' --psm 7')

        # Clean up
        name = name.strip().replace("\n", " ")
        level = level.strip()
        mainStatKey = mainStatKey.strip()

        # Fix OCR errors
        name, _ = GameData.get_closest_relic_name(name)
        mainStatKey, _ = GameData.get_closest_relic_main_stat(mainStatKey)

        # Parse substats
        subStats = []
        for i in range(1, 5):
            key = stats_map["subStatKey_" + str(i)]
            val = stats_map["subStatVal_" + str(i)]

            key = pytesseract.image_to_string(
                key, config='-c tessedit_char_whitelist=\'ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz\' --psm 7')
            val = pytesseract.image_to_string(
                val, config='-c tessedit_char_whitelist=0123456789.% --psm 7')

            key = key.strip()
            val = val.strip()

            key, min_dist = GameData.get_closest_relic_sub_stat(key)
            if min_dist > 5:
                break

            if len(val) == 0:
                print("ERROR: Substat value not found: " + key)
                break

            if val[-1] == '%':
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

        metadata = GameData.get_relic_meta_data(name)
        setKey = metadata["setKey"]
        slotKey = metadata["slotKey"]

        result = {
            "setKey": setKey,
            "slotKey": slotKey,
            "level": int(level),
            "mainStatKey": mainStatKey,
            "subStats": subStats
        }

        print(result)

        return result
