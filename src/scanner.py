from utils.navigation import Navigation
import win32gui
import time
from utils.screenshot import Screenshot
import numpy as np
from paddleocr import PaddleOCR
from utils.game_data import GameData
import Levenshtein as lev


nav_data = {
    "16:9": {
        "light_cone": {
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
}


class HSRScanner:

    def __init__(self):
        self.scan_light_cones = False
        self.scan_relics = False
        self.scan_characters = False

        hwnd = win32gui.FindWindow("UnityWndClass", "Honkai: Star Rail")
        if not hwnd:
            Exception(
                "Honkai: Star Rail not found. Please open the game and try again.")

        self._nav = Navigation(hwnd)

        self._aspect_ratio = self._nav.get_aspect_ratio()

        self._screenshot = Screenshot(hwnd, self._aspect_ratio)

        self._ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)

    def scan(self):
        if not any([self.scan_light_cones, self.scan_relics, self.scan_characters]):
            raise Exception("No scan options selected.")

        self._nav.bring_window_to_foreground()

        if self.scan_light_cones:
            self.get_light_cones()

        if self.scan_relics:
            pass

        if self.scan_characters:
            pass

    def get_light_cones(self):
        lc_nav_data = nav_data[self._aspect_ratio]["light_cone"]

        # Navigate to Light Cone tab from cellphone menu
        self._nav.send_key_press("esc")
        time.sleep(1)
        self._nav.send_key_press("b")
        time.sleep(1)
        self._nav.move_cursor_to(*lc_nav_data["inv_tab"])
        self._nav.click()
        time.sleep(0.5)

        # Main loop
        # TODO: Extract into new Light Cone scanner class, error checking and handling

        quantity = self._screenshot.screenshot_light_cone_quantity()
        quantity.save("quantity.png")
        quantity = np.array(quantity)
        quantity = self._ocr.ocr(quantity, cls=False, det=False)

        try:
            quantity_remaining = int(
                quantity[0][0][0].split(" ")[1].split("/")[0])
        except:
            raise Exception("Could not parse quantity.")

        print("Quantity remaining: ", quantity_remaining)

        scanned_light_cones = []
        scanned_per_scroll = lc_nav_data["rows"] * \
            lc_nav_data["cols"]

        while quantity_remaining > 0:
            if quantity_remaining < scanned_per_scroll:
                x, y = lc_nav_data["row_start_bottom"]
                start_row = quantity_remaining // (lc_nav_data["cols"] + 1)
                y -= start_row * lc_nav_data["offset_y"]
            else:
                x, y = lc_nav_data["row_start_top"]

            for r in range(lc_nav_data["rows"]):
                for c in range(lc_nav_data["cols"]):
                    if quantity_remaining <= 0:
                        break

                    self._nav.move_cursor_to(x, y)
                    self._nav.click()
                    x += lc_nav_data["offset_x"]

                    quantity_remaining -= 1

                    # TODO: equipped, locked
                    name, level, superimposition = self._screenshot.screenshot_light_cone_stats()

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

                    scanned_light_cones.append(result)

                # Next row
                x = lc_nav_data["row_start_top"][0]
                y += lc_nav_data["offset_y"]

            if quantity_remaining <= 0:
                break

            self._nav.drag_scroll(
                x, lc_nav_data["scroll_start_y"], lc_nav_data["row_start_top"][1])
            time.sleep(0.5)

        return scanned_light_cones
