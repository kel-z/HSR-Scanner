from utils.navigation import Navigation
import win32gui
import time
from utils.screenshot import Screenshot
import numpy as np
from paddleocr import PaddleOCR
import asyncio
from light_cone_strategy import LightConeStrategy
from relic_strategy import RelicStrategy
from pynput.keyboard import Key


class HSRScanner ():
    scan_light_cones = False
    scan_relics = False
    scan_characters = False
    update_progress = None

    esc_key = Key.esc
    inventory_key = "b"
    character_key = "c"

    def __init__(self):
        self.interrupt_requested = False
        hwnd = win32gui.FindWindow("UnityWndClass", "Honkai: Star Rail")
        if not hwnd:
            Exception(
                "Honkai: Star Rail not found. Please open the game and try again.")

        self._nav = Navigation(hwnd)

        self._aspect_ratio = self._nav.get_aspect_ratio()

        self._screenshot = Screenshot(hwnd, self._aspect_ratio)

        self._ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)

    def stop_scan(self):
        self.interrupt_requested = True

    async def start_scan(self, callback=None):
        if not any([self.scan_light_cones, self.scan_relics, self.scan_characters]):
            raise Exception("No scan options selected.")

        self._nav.bring_window_to_foreground()
        tasks = []

        res = {}

        if self.scan_light_cones:
            res["light_cones"] = []
            tasks.append(self.scan_inventory(LightConeStrategy(
                self._ocr, self._screenshot), res["light_cones"].append))

        if self.scan_relics:
            res["relics"] = []
            tasks.append(self.scan_inventory(RelicStrategy(
                self._ocr, self._screenshot), res["relics"].append))

        if self.scan_characters:
            pass
        
        await asyncio.gather(*tasks)

        if callback:
            callback(res)

    async def scan_inventory(self, strategy, callback):
        nav_data = strategy.nav_data[self._aspect_ratio]

        # Navigate to correct tab from cellphone menu
        time.sleep(1)
        self._nav.send_key_press(self.esc_key)
        time.sleep(1)
        self._nav.send_key_press(self.inventory_key)
        time.sleep(1)
        self._nav.move_cursor_to(*nav_data["inv_tab"])
        self._nav.click()
        time.sleep(0.5)

        # TODO: using quantity to know when to scan the bottom row is not ideal
        #       because it will not work for tabs that do not have a quantity
        #       (i.e. materials).
        #
        #       for now, it will work for light cones and relics.
        quantity = self._screenshot.screenshot_quantity()
        quantity = np.array(quantity)
        quantity = self._ocr.ocr(quantity, cls=False, det=False)

        try:
            quantity_remaining = int(
                quantity[0][0][0].split(" ")[1].split("/")[0])
        except:
            raise Exception("Could not parse quantity.")

        scanned_per_scroll = nav_data["rows"] * nav_data["cols"]

        tasks = set()
        while quantity_remaining > 0:
            if quantity_remaining <= scanned_per_scroll:
                x, y = nav_data["row_start_bottom"]
                start_row = quantity_remaining // (nav_data["cols"] + 1)
                y -= start_row * nav_data["offset_y"]
            else:
                x, y = nav_data["row_start_top"]

            for r in range(nav_data["rows"]):
                for c in range(nav_data["cols"]):
                    if quantity_remaining <= 0:
                        break

                    if self.interrupt_requested:
                        raise Exception("Scan interrupted.")

                    self._nav.move_cursor_to(x, y)
                    time.sleep(0.05)
                    self._nav.click()
                    time.sleep(0.05)

                    quantity_remaining -= 1

                    stats_img_map = strategy.screenshot_stats()

                    # Convert each image to numpy array
                    stats_img_map = {k: np.array(v)
                                     for k, v in stats_img_map.items()}

                    # TODO: check min level / rarity

                    if self.update_progress:
                        self.update_progress(strategy.scan_type)

                    task = asyncio.create_task(strategy.parse(stats_img_map))
                    tasks.add(task)

                    task.add_done_callback(
                        lambda t: callback(t.result()))
                    task.add_done_callback(tasks.discard)

                    x += nav_data["offset_x"]

                # Next row
                x = nav_data["row_start_top"][0]
                y += nav_data["offset_y"]

            if quantity_remaining <= 0:
                break

            self._nav.drag_scroll(
                x, nav_data["scroll_start_y"], nav_data["row_start_top"][1])
            time.sleep(0.5)

        self._nav.send_key_press(self.esc_key)
        time.sleep(1)
        self._nav.send_key_press(self.esc_key)
        return tasks
