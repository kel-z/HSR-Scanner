from utils.navigation import Navigation
import win32gui
import time
from utils.screenshot import Screenshot

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

        self.nav.bring_window_to_foreground()
        self.aspect_ratio = self.nav.get_aspect_ratio()

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

        for r in range(light_cone_coords["rows"]):
            for c in range(light_cone_coords["cols"]):
                self.nav.move_cursor_to(x, y)
                self.nav.click()
                time.sleep(0.2)

                img = self.screenshot.screenshot_light_cone()
                # img.save(str(r) + "_" + str(c) + "test.png")

                x += light_cone_coords["offset_x"]
            x = light_cone_coords["light_cone_start"][0]
            y += light_cone_coords["offset_y"]


scanner = StarRailScanner()
scanner.scan_light_cones()
