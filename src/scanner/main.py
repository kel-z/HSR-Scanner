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


class StarRailScanner:

    def __init__(self):
        try:
            hwnd = win32gui.FindWindow("UnityWndClass", "Honkai: Star Rail")
            if not hwnd:
                raise "Honkai: Star Rail not found. Please open the game and try again."
        except:
            raise ("Honkai: Star Rail not found. Please open the game and try again.")

        self.nav = Navigation(hwnd)

        self.aspect_ratio = self.nav.get_aspect_ratio()

        self.screenshot = Screenshot(hwnd, self.aspect_ratio)

        self.ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)

        self.nav.bring_window_to_foreground()

    def scan_light_cones(self):
        lc_nav_data = nav_data[self.aspect_ratio]["light_cone"]

        # Navigate to Light Cone tab from cellphone menu
        self.nav.send_key_press("esc")
        time.sleep(1)
        self.nav.send_key_press("b")
        time.sleep(1)
        self.nav.move_cursor_to(*lc_nav_data["inv_tab"])
        self.nav.click()
        time.sleep(0.5)

        # Main loop
        # TODO: Extract into new Light Cone scanner class, error checking and handling

        quantity = self.screenshot.screenshot_light_cone_quantity()
        quantity.save("quantity.png")
        quantity = np.array(quantity)
        quantity = self.ocr.ocr(quantity, cls=False, det=False)

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

                    self.nav.move_cursor_to(x, y)
                    self.nav.click()
                    x += lc_nav_data["offset_x"]

                    quantity_remaining -= 1

                    # TODO: equipped, locked
                    name, level, superimposition = self.screenshot.screenshot_light_cone_stats()

                    # Convert to numpy arrays
                    name = np.array(name)
                    level = np.array(level)
                    superimposition = np.array(superimposition)

                    # OCR
                    name = self.ocr.ocr(name, cls=False, det=False)
                    level = self.ocr.ocr(level, cls=False, det=False)
                    superimposition = self.ocr.ocr(
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
                    level, _ = level.split("/")
                    level = int(level)
                    ascension = int(level) // 10

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

            self.nav.drag_scroll(
                x, lc_nav_data["scroll_start_y"], lc_nav_data["row_start_top"][1])
            time.sleep(0.5)

        return scanned_light_cones


scanner = StarRailScanner()
print(scanner.scan_light_cones())
