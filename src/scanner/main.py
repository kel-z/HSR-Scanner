from utils.navigation import Navigation
import win32gui
import time
from utils.screenshot import Screenshot
import numpy as np
from paddleocr import PaddleOCR
from utils.game_data import GameData
import Levenshtein as lev


coords = {
    "16:9": {
        "light_cone": {
            "light_cone_tab": (0.38, 0.06),
            "light_cone_start": (0.1, 0.185),
            "offset_x": 0.075,
            "offset_y": 0.157,
            "rows": 5,
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
        self.screenshot = Screenshot(hwnd)
        self.ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)

        self.nav.bring_window_to_foreground()
        self.aspect_ratio = self.nav.get_aspect_ratio()

    # Assume cellphone menu is already open
    def scan_light_cones(self):
        light_cone_coords = coords[self.aspect_ratio]["light_cone"]

        self.nav.send_key_press("esc")
        time.sleep(1)
        self.nav.send_key_press("b")
        time.sleep(1)
        self.nav.move_cursor_to(*light_cone_coords["light_cone_tab"])
        self.nav.click()
        time.sleep(0.5)

        x, y = light_cone_coords["light_cone_start"]

        # Main loop
        # TODO: Parse quantity, scrolling, location, locked, error checking and handling
        scanned_light_cones = []
        for r in range(light_cone_coords["rows"]):
            for c in range(light_cone_coords["cols"]):
                self.nav.move_cursor_to(x, y)
                self.nav.click()

                img = self.screenshot.screenshot_light_cone()

                # Crop the image to the name, level, and superimposition
                name = img.crop((0, 0, img.width, 0.15 * img.height))
                level = img.crop(
                    (0.13 * img.width, 0.53 * img.height, 0.35 * img.width, 0.67 * img.height))
                superimposition = img.crop(
                    (0.1 * img.width, 0.87 * img.height, 0.7 * img.width, img.height))

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
                level, ascension = level.split("/")
                level = int(level)
                ascension = int(ascension) // 10

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

                x += light_cone_coords["offset_x"]
            x = light_cone_coords["light_cone_start"][0]
            y += light_cone_coords["offset_y"]

        print(scanned_light_cones)


scanner = StarRailScanner()
scanner.scan_light_cones()
