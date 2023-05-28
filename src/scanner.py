from utils.navigation import Navigation
import win32gui
import time
from utils.screenshot import Screenshot
import asyncio
from light_cone_strategy import LightConeStrategy
from relic_strategy import RelicStrategy
from pynput.keyboard import Key
from helper_functions import image_to_string


class HSRScanner:
    update_progress = None
    logger = None
    interrupt = asyncio.Event()

    def __init__(self, config):
        self._hwnd = win32gui.FindWindow("UnityWndClass", "Honkai: Star Rail")
        if not self._hwnd:
            Exception(
                "Honkai: Star Rail not found. Please open the game and try again.")

        self._config = config

        self._nav = Navigation(self._hwnd)

        self._aspect_ratio = self._nav.get_aspect_ratio()

        self._screenshot = Screenshot(self._hwnd, self._aspect_ratio)

        self.interrupt.clear()

    async def start_scan(self):
        if not any([self._config["scan_light_cones"], self._config["scan_relics"], self._config["scan_characters"]]):
            raise Exception("No scan options selected.")

        self._nav.bring_window_to_foreground()

        light_cones = []
        if self._config["scan_light_cones"] and not self.interrupt.is_set():
            light_cones = self.scan_inventory(
                LightConeStrategy(self._screenshot, self.logger))

        relics = []
        if self._config["scan_relics"] and not self.interrupt.is_set():
            relics = self.scan_inventory(
                RelicStrategy(self._screenshot, self.logger))

        if self._config["scan_characters"] and not self.interrupt.is_set():
            pass

        if self.interrupt.is_set():
            await asyncio.gather(*light_cones, *relics)
            return

        return {
            "light_cones": await asyncio.gather(*light_cones),
            "relics": await asyncio.gather(*relics)
        }

    def stop_scan(self):
        self.interrupt.set()

    def scan_inventory(self, strategy):
        nav_data = strategy.NAV_DATA[self._aspect_ratio]

        # Navigate to correct tab from cellphone menu
        time.sleep(1)
        self._nav.key_press(Key.esc)
        time.sleep(1)
        self._nav.key_hold(Key.tab)
        time.sleep(0.1)
        self._nav.move_cursor_to(0.75, 0.5)
        time.sleep(0.1)
        self._nav.key_release(Key.tab)
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
        quantity = image_to_string(quantity, "0123456789/", 7)

        try:
            quantity_remaining = int(quantity.split("/")[0])
        except ValueError:
            raise ValueError("Failed to parse quantity." +
                             (f" Got \"{quantity}\" instead." if quantity else "") +
                             " Did you start the scan from the ESC menu?")

        current_sort_method = strategy.screenshot_sort()
        current_sort_method = image_to_string(
            current_sort_method, "RarityLv", 7)
        optimal_sort_method = strategy.get_optimal_sort_method(
            self._config["filters"])

        if optimal_sort_method != current_sort_method:
            self._nav.move_cursor_to(*nav_data["sort"]["button"])
            self._nav.click()
            time.sleep(0.5)
            self._nav.move_cursor_to(*nav_data["sort"][optimal_sort_method])
            self._nav.click()
            current_sort_method = optimal_sort_method
            time.sleep(0.5)

        tasks = set()
        scanned_per_scroll = nav_data["rows"] * nav_data["cols"]
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

                    stats_dict = strategy.screenshot_stats()
                    x += nav_data["offset_x"]

                    if self._config["filters"]:
                        filter_results, stats_dict = strategy.check_filters(
                            stats_dict, self._config["filters"])
                        if (current_sort_method == "Lv" and not filter_results["min_level"]) or \
                                (current_sort_method == "Rarity" and not filter_results["min_rarity"]):
                            quantity_remaining = 0
                            break
                        if not all(filter_results.values()):
                            continue

                    if self.update_progress:
                        self.update_progress.emit(strategy.SCAN_TYPE)

                    task = asyncio.to_thread(
                        strategy.parse, stats_dict, self.interrupt, self.update_progress)
                    tasks.add(task)

                # Next row
                x = nav_data["row_start_top"][0]
                y += nav_data["offset_y"]

            if quantity_remaining <= 0:
                break

            self._nav.drag_scroll(
                x, nav_data["scroll_start_y"], nav_data["scroll_end_y"])
            time.sleep(0.5)

        self._nav.key_press(Key.esc)
        time.sleep(1)
        self._nav.key_press(Key.esc)
        return tasks
