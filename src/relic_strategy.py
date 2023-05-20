from utils.game_data import GameData
import Levenshtein as lev
import numpy as np

# TODO: equipped, locked


class RelicStrategy:
    scan_type = 1
    nav_data = {
        "16:9": {
            "inv_tab": (0.43, 0.06),
            "row_start_top": (0.1, 0.25),
            "row_start_bottom": (0.1, 0.77),
            "scroll_start_y": 0.752,
            "offset_x": 0.075,
            "offset_y": 0.157,
            "rows": 3,
            "cols": 8
        }
    }

    def __init__(self, ocr, screenshot):
        self._ocr = ocr
        self._screenshot = screenshot

        self._relic_sub_stats = GameData.get_relic_sub_stats()
        self._relic_metadata = GameData.get_relic_metadata()

    def screenshot_stats(self):
        return self._screenshot.screenshot_relic_stats()

    async def parse(self, stats_map):
        # Get each np array
        name = stats_map["name"]
        level = stats_map["level"]
        mainStatKey = stats_map["mainStatKey"]

        # OCR
        name = self._ocr.ocr(name, cls=False, det=False)
        level = self._ocr.ocr(level, cls=False, det=False)
        mainStatKey = self._ocr.ocr(mainStatKey, cls=False, det=False)

        # Convert to strings
        name = name[0][0][0].strip()
        level = level[0][0][0].strip()
        mainStatKey = mainStatKey[0][0][0].strip()

        # Fix OCR errors
        if name not in self._relic_metadata:
            min_dist = 100
            min_name = ""
            for relic in self._relic_metadata:
                dist = lev.distance(name, relic)
                if dist < min_dist:
                    min_dist = dist
                    min_name = relic
            name = min_name

        # Parse substats
        subStats = []
        for i in range(1, 5):
            key = stats_map["subStatKey_" + str(i)]
            val = stats_map["subStatVal_" + str(i)]

            key = self._ocr.ocr(key, cls=False, det=False)
            val = self._ocr.ocr(val, cls=False, det=False)

            key = key[0][0][0].strip()
            val = val[0][0][0].strip()

            if key not in self._relic_sub_stats:
                # Get similarity, then get closest match if threshold is met
                min_dist = 100
                min_key = ""
                for sub_stat in self._relic_sub_stats:
                    dist = lev.distance(key, sub_stat)
                    if dist < min_dist:
                        min_dist = dist
                        min_key = sub_stat

                if min_dist > 5:
                    break

                key = min_key

            if len(val) == 0:
                print("ERROR: Substat value not found: " + key)
                break
            if val[-1] == '%':
                val = val[:-1]
                key += '_'

            subStats.append(
                {
                    "key": key,
                    "value": val
                }
            )

        metadata = self._relic_metadata[name]
        setKey = metadata["setKey"]
        slotKey = metadata["slotKey"]

        result = {
            "setKey": setKey,
            "slotKey": slotKey,
            "level": level,
            "mainStatKey": mainStatKey,
            "subStats": subStats
        }

        return result
