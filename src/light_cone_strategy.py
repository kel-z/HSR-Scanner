from utils.game_data import GameData
import Levenshtein as lev
import numpy as np

# TODO: equipped, locked


class LightConeStrategy:
    nav_data = {
        "16:9": {
            "inv_tab": (0.38, 0.06),
            "row_start_top": (0.1, 0.185),
            "row_start_bottom": (0.1, 0.77),
            "scroll_start_y": 0.849,
            "offset_x": 0.075,
            "offset_y": 0.157,
            "rows": 4,
            "cols": 8
        }
    }

    def __init__(self, ocr, screenshot):
        self._ocr = ocr
        self._screenshot = screenshot

    def screenshot_stats(self):
        return self._screenshot.screenshot_light_cone_stats()

    async def parse(self, name, level, superimposition):
        # Convert to numpy arrays
        name = np.array(name)
        level = np.array(level)
        superimposition = np.array(superimposition)

        # OCR
        name = self._ocr.ocr(name, cls=False, det=False)
        level = self._ocr.ocr(level, cls=False, det=False)
        superimposition = self._ocr.ocr(
            superimposition, cls=False, det=False)

        # Convert to strings
        name = name[0][0][0].strip()
        level = level[0][0][0].strip()
        superimposition = superimposition[0][0][0].strip()

        # Fix OCR errors
        lc = GameData.get_light_cones()
        if name not in lc:
            min_dist = 100
            min_name = ""
            for cone in lc:
                dist = lev.distance(name, cone)
                if dist < min_dist:
                    min_dist = dist
                    min_name = cone
            name = min_name

        # Parse level and ascension
        level, max_level = level.split("/")
        level = int(level)
        ascension = (max(int(max_level), 20) - 20) // 10

        # Parse superimposition
        superimposition = superimposition.split(" ")
        superimposition = int(
            "".join(filter(str.isdigit, superimposition[1])))

        result = {
            "name": name,
            "level": level,
            "ascension": ascension,
            "superimposition": superimposition
        }

        return result
