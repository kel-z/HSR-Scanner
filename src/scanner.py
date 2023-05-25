from utils.navigation import Navigation
import win32gui
import time
from utils.screenshot import Screenshot
import numpy as np
import asyncio
from light_cone_strategy import LightConeStrategy
from relic_strategy import RelicStrategy
from pynput.keyboard import Key
import pytesseract


class HSRScanner:
    scan_light_cones = False
    scan_relics = False
    scan_characters = False
    update_progress = None
    interrupt = asyncio.Event()

    esc_key = Key.esc
    inventory_key = "b"
    character_key = "c"

    def __init__(self):
        self._hwnd = win32gui.FindWindow("UnityWndClass", "Honkai: Star Rail")
        if not self._hwnd:
            Exception(
                "Honkai: Star Rail not found. Please open the game and try again.")

        self._nav = Navigation(self._hwnd)

        self._aspect_ratio = self._nav.get_aspect_ratio()

        self._screenshot = Screenshot(self._hwnd, self._aspect_ratio)

        self._item_id = 0

        self.interrupt.clear()

    def stop_scan(self):
        self.interrupt.set()

    async def start_scan(self):
        if not any([self.scan_light_cones, self.scan_relics, self.scan_characters]):
            raise Exception("No scan options selected.")

        self._nav.bring_window_to_foreground()

        self._item_id = 0

        light_cones = []
        if self.scan_light_cones and not self.interrupt.is_set():
            light_cones = self.scan_inventory(
                LightConeStrategy(self._screenshot))

        relics = []
        if self.scan_relics and not self.interrupt.is_set():
            relics = self.scan_inventory(
                RelicStrategy(self._screenshot))

        if self.scan_characters:
            pass

        if self.interrupt.is_set():
            await asyncio.gather(*light_cones, *relics)
            return

        return {
            "light_cones": await asyncio.gather(*light_cones),
            "relics": await asyncio.gather(*relics)
        }

    def scan_inventory(self, strategy):
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
        quantity = pytesseract.image_to_string(
            quantity, config='-c tessedit_char_whitelist=0123456789/ --psm 7').strip()

        try:
            quantity_remaining = int(quantity.split("/")[0])
        except Exception as e:
            raise Exception("Could not parse quantity. Got " + quantity + ".")

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

                    if self.interrupt.is_set():
                        return tasks

                    self._nav.move_cursor_to(x, y)
                    time.sleep(0.1)
                    self._nav.click()
                    time.sleep(0.2)

                    quantity_remaining -= 1

                    stats_img_map = strategy.screenshot_stats()

                    # TODO: check min level / rarity

                    if self.update_progress:
                        self.update_progress(strategy.scan_type)

                    task = asyncio.to_thread(
                        strategy.parse, stats_img_map, self._item_id, self.interrupt)

                    tasks.add(task)

                    x += nav_data["offset_x"]
                    self._item_id += 1

                # Next row
                x = nav_data["row_start_top"][0]
                y += nav_data["offset_y"]

            if quantity_remaining <= 0:
                break

            self._nav.drag_scroll(
                x, nav_data["scroll_start_y"], nav_data["scroll_end_y"])
            time.sleep(0.5)

        self._nav.send_key_press(self.esc_key)
        time.sleep(1)
        self._nav.send_key_press(self.esc_key)
        return tasks
