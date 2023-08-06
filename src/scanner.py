from utils.navigation import Navigation
import win32gui
import time
from utils.screenshot import Screenshot
import asyncio
from light_cone_strategy import LightConeStrategy
from relic_strategy import RelicStrategy
from pynput.keyboard import Key
from helper_functions import image_to_string
import pyautogui
from character_scanner import CharacterScanner


class HSRScanner:
    update_progress = None
    logger = None
    interrupt = asyncio.Event()

    def __init__(self, config):
        self._hwnd = win32gui.FindWindow("UnityWndClass", "Honkai: Star Rail")
        if not self._hwnd:
            Exception(
                "Honkai: Star Rail not found. Please open the game and try again."
            )

        self._config = config

        self._nav = Navigation(self._hwnd)

        self._aspect_ratio = self._nav.get_aspect_ratio()

        self._screenshot = Screenshot(self._hwnd, self._aspect_ratio)

        self.interrupt.clear()

    async def start_scan(self):
        if not any(
            [
                self._config["scan_light_cones"],
                self._config["scan_relics"],
                self._config["scan_characters"],
            ]
        ):
            raise Exception("No scan options selected.")

        self._nav.bring_window_to_foreground()

        light_cones = []
        if self._config["scan_light_cones"] and not self.interrupt.is_set():
            light_cones = self.scan_inventory(
                LightConeStrategy(self._screenshot, self.logger)
            )

        relics = []
        if self._config["scan_relics"] and not self.interrupt.is_set():
            relics = self.scan_inventory(RelicStrategy(self._screenshot, self.logger))

        characters = []
        if self._config["scan_characters"] and not self.interrupt.is_set():
            characters = self.scan_characters()

        if self.interrupt.is_set():
            await asyncio.gather(*light_cones, *relics, *characters)
            return

        return {
            "source": "HSR_Scanner",
            "version": 1,
            "light_cones": await asyncio.gather(*light_cones),
            "relics": await asyncio.gather(*relics),
            "characters": await asyncio.gather(*characters),
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
            quantity = quantity_remaining = int(quantity.split("/")[0])
        except ValueError:
            raise ValueError(
                "Failed to parse quantity."
                + (f' Got "{quantity}" instead.' if quantity else "")
                + " Did you start the scan from the ESC menu?"
            )

        current_sort_method = strategy.screenshot_sort()
        current_sort_method = image_to_string(current_sort_method, "RarityLv", 7)
        optimal_sort_method = strategy.get_optimal_sort_method(self._config["filters"])

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
            if (
                quantity_remaining <= scanned_per_scroll
                and not quantity <= scanned_per_scroll
            ):
                x, y = nav_data["row_start_bottom"]
                todo_rows = self._ceildiv(quantity_remaining, nav_data["cols"]) - 1
                y -= todo_rows * nav_data["offset_y"]
            else:
                x, y = nav_data["row_start_top"]

            for r in range(nav_data["rows"]):
                for c in range(nav_data["cols"]):
                    if quantity_remaining <= 0:
                        break

                    if self.interrupt.is_set():
                        return tasks

                    # Next item
                    self._nav.move_cursor_to(x, y)
                    time.sleep(0.1)
                    self._nav.click()
                    time.sleep(0.2)
                    quantity_remaining -= 1

                    # Get stats
                    stats_dict = strategy.screenshot_stats()
                    x += nav_data["offset_x"]

                    # Check if item satisfies filters
                    if self._config["filters"]:
                        filter_results, stats_dict = strategy.check_filters(
                            stats_dict, self._config["filters"]
                        )
                        if (
                            current_sort_method == "Lv"
                            and not filter_results["min_level"]
                        ) or (
                            current_sort_method == "Rarity"
                            and not filter_results["min_rarity"]
                        ):
                            quantity_remaining = 0
                            break
                        if not all(filter_results.values()):
                            continue

                    # Update UI count
                    if self.update_progress:
                        self.update_progress.emit(strategy.SCAN_TYPE)

                    task = asyncio.to_thread(
                        strategy.parse, stats_dict, self.interrupt, self.update_progress
                    )
                    tasks.add(task)

                # Next row
                x = nav_data["row_start_top"][0]
                y += nav_data["offset_y"]

            if quantity_remaining <= 0:
                break

            self._nav.drag_scroll(
                x, nav_data["scroll_start_y"], nav_data["scroll_end_y"]
            )
            time.sleep(0.5)

        self._nav.key_press(Key.esc)
        time.sleep(1.5)
        self._nav.key_press(Key.esc)
        return tasks

    def scan_characters(self):
        char_scanner = CharacterScanner(
            self._screenshot, self.logger, self.interrupt, self.update_progress
        )
        nav_data = char_scanner.NAV_DATA[self._aspect_ratio]

        # Get character count from Data Bank menu
        self._nav.bring_window_to_foreground()
        time.sleep(1)
        self._nav.move_cursor_to(*nav_data["data_bank"])
        time.sleep(0.1)
        self._nav.click()
        time.sleep(1)
        character_count = self._screenshot.screenshot_character_count()
        character_count = image_to_string(character_count, "0123456789/", 7)
        try:
            character_count, _ = character_count.split("/")
            character_count = int(character_count)
        except ValueError:
            raise ValueError(
                "Failed to parse character count."
                + (f' Got "{character_count}" instead.' if character_count else "")
                + " Did you start the scan from the ESC menu?"
            )

        # Update UI count
        if self.update_progress:
            for _ in range(character_count):
                self.update_progress.emit(2)

        # Navigate to characters menu
        self._nav.key_press(Key.esc)
        time.sleep(1)
        self._nav.key_press(Key.esc)
        time.sleep(1)
        self._nav.key_press("1")
        time.sleep(0.2)
        self._nav.key_hold(Key.tab)
        time.sleep(0.2)
        self._nav.move_cursor_to(0.5, 0.75)
        time.sleep(0.1)
        self._nav.key_release(Key.tab)

        tasks = set()
        x, y = nav_data["char_start"]
        i = 0
        while character_count > 0:
            if self.interrupt.is_set():
                return tasks

            # Next character
            self._nav.move_cursor_to(x, y)
            time.sleep(0.2)
            self._nav.click()
            time.sleep(1)

            # Get character name
            stats_dict = {}
            character_name = self._screenshot.screenshot_character_name()
            character_name = image_to_string(
                character_name,
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz/7",
                7,
            )
            try:
                path, character_name = map(str.strip, character_name.split("/"))
                character_name, path = char_scanner.get_closest_name_and_path(
                    character_name, path
                )
                stats_dict["name"] = character_name

                # Get level
                stats_dict["level"] = self._screenshot.screenshot_character_level()

                # Get ascension by counting ascension stars
                ascension_pos = nav_data["ascension_start"]
                ascension = 0
                for _ in range(6):
                    pixel = pyautogui.pixel(
                        *self._nav.translate_percent_to_coords(*ascension_pos)
                    )
                    dist = sum([(a - b) ** 2 for a, b in zip(pixel, (255, 222, 152))])
                    if dist > 100:
                        break

                    ascension += 1
                    ascension_pos = (
                        ascension_pos[0] + nav_data["ascension_offset_x"],
                        ascension_pos[1],
                    )
                stats_dict["ascension"] = ascension

                # Get traces
                self._nav.move_cursor_to(*nav_data["traces_button"])
                time.sleep(0.1)
                self._nav.click()
                time.sleep(1)
                stats_dict["traces"] = char_scanner.get_traces_dict(path)
                path_key = path.split(" ")[-1].lower()
                for k, v in nav_data["traces"][path_key].items():
                    pixel = pyautogui.pixel(*self._nav.translate_percent_to_coords(*v))
                    dist = min(
                        sum([(a - b) ** 2 for a, b in zip(pixel, (255, 255, 255))]),
                        sum([(a - b) ** 2 for a, b in zip(pixel, (178, 200, 255))]),
                    )
                    stats_dict["traces"]["unlocks"][k] = dist < 3000

                # Get eidelons
                self._nav.move_cursor_to(*nav_data["eidelons_button"])
                time.sleep(0.1)
                self._nav.click()
                time.sleep(1.5)
                eidlon_images = self._screenshot.screenshot_character_eidelons()

                task = asyncio.to_thread(char_scanner.parse, stats_dict, eidlon_images)
                tasks.add(task)
            except Exception as e:
                self.logger.emit(
                    f'Failed to parse character {character_name}. Got "{e}" error. Skipping...'
                ) if self.logger else None

            # Reset for next character
            self._nav.move_cursor_to(*nav_data["details_button"])
            time.sleep(0.1)
            self._nav.click()
            time.sleep(0.1)

            if (
                character_count - 1 == nav_data["chars_per_scan"]
                or i == nav_data["chars_per_scan"] - 1
            ):
                # Workaround to avoid drag scrolling
                x, y = nav_data["char_start"]
                i += 1
                x = x + nav_data["offset_x"] * i
                self._nav.move_cursor_to(x, y)
                time.sleep(0.1)
                self._nav.click()
                time.sleep(0.1)
                x, y = nav_data["list_button"]
                self._nav.move_cursor_to(x, y)
                time.sleep(0.1)
                self._nav.click()
                time.sleep(0.3)
                i = 0
            elif character_count <= nav_data["chars_per_scan"]:
                x, y = nav_data["char_end"]
                x -= nav_data["offset_x"] * (character_count - 2)
            else:
                x, y = nav_data["char_start"]
                i += 1
                x = x + nav_data["offset_x"] * i

            character_count -= 1

        time.sleep(1)
        self._nav.key_press(Key.esc)
        time.sleep(1.5)
        self._nav.key_press(Key.esc)
        return tasks

    def _ceildiv(self, a, b):
        return -(a // -b)
