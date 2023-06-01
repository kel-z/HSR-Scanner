import traceback
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
from PIL import Image
from helper_functions import resource_path
from utils.game_data_helpers import get_character_meta_data, CHARACTER_META_DATA, get_closest_character_name


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

        characters = []
        if self._config["scan_characters"] and not self.interrupt.is_set():
            characters = self.scan_characters()

        if self.interrupt.is_set():
            await asyncio.gather(*light_cones, *relics, *characters)
            return

        return {
            "light_cones": await asyncio.gather(*light_cones),
            "relics": await asyncio.gather(*relics),
            "characters": await asyncio.gather(*characters)
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

    def scan_characters(self):
        NAV_DATA = {
            "16:9": {
                "data_bank": (0.765, 0.715),
                "ascension_start": (0.78125, 0.203),
                "ascension_offset_x": 0.01328,
                "chars_per_scan": 9,
                "char_start": (0.256, 0.065),
                "char_end": (0.744, 0.066),
                "offset_x": 0.055729,
                "details_button": (0.13, 0.143),
                "traces_button": (0.13, 0.315),
                "eidelons_button": (0.13, 0.49),
                "list_button": (0.033, 0.931),
                "trailblazer": (0.3315, 0.4432, 0.126, 0.1037)
            }
        }[self._aspect_ratio]

        self._nav.bring_window_to_foreground()
        time.sleep(1)
        self._nav.move_cursor_to(*NAV_DATA["data_bank"])
        time.sleep(0.1)
        self._nav.click()
        time.sleep(1)
        character_count = self._screenshot.screenshot_character_count()
        character_count = image_to_string(character_count, "0123456789/", 7)

        try:
            character_count, _ = character_count.split("/")
            # +1 for the player character
            character_count = int(character_count) + 1
        except ValueError:
            raise ValueError("Failed to parse character count." +
                             (f" Got \"{character_count}\" instead." if character_count else "") +
                             " Did you start the scan from the ESC menu?")

        if self.update_progress:
            for _ in range(character_count):
                self.update_progress.emit(2)

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
        x, y = NAV_DATA["char_start"]
        i = 0
        while character_count > 0:
            if self.interrupt.is_set():
                return tasks

            self._nav.move_cursor_to(x, y)
            time.sleep(0.1)
            self._nav.click()
            time.sleep(1)

            stats_dict = {}
            character_name = self._screenshot.screenshot_character_name()
            character_name = image_to_string(
                character_name, "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz/7", 7)

            try:
                path, character_name = map(
                    str.strip, character_name.split("/"))

                char = self._screenshot.screenshot_character()

                if self.is_trailblazer(char):
                    character_name = "Trailblazer" + path.split(" ")[-1]

                character_name, min_dist = get_closest_character_name(
                    character_name)

                if min_dist > 5:
                    raise Exception(
                        f"Character not found in database. Got {character_name}")

                stats_dict["name"] = character_name

                stats_dict["level"] = self._screenshot.screenshot_character_level()

                ascension_pos = NAV_DATA["ascension_start"]
                ascension = 0
                for _ in range(6):
                    pixel = pyautogui.pixel(
                        *self._nav.translate_percent_to_coords(*ascension_pos))
                    dist = sum(
                        [(a - b) ** 2 for a, b in zip(pixel, (255, 222, 152))])
                    if dist > 100:
                        break

                    ascension += 1
                    ascension_pos = (
                        ascension_pos[0] + NAV_DATA["ascension_offset_x"], ascension_pos[1])

                stats_dict["ascension"] = ascension

                self._nav.move_cursor_to(*NAV_DATA["traces_button"])
                time.sleep(0.1)
                self._nav.click()

                time.sleep(1)

                if path == "The Hunt":
                    traces_dict = self._screenshot.screenshot_character_hunt_traces()
                elif path == "Erudition":
                    traces_dict = self._screenshot.screenshot_character_erudition_traces()
                elif path == "Harmony":
                    traces_dict = self._screenshot.screenshot_character_harmony_traces()
                elif path == "Preservation":
                    traces_dict = self._screenshot.screenshot_character_preservation_traces()
                elif path == "Destruction":
                    traces_dict = self._screenshot.screenshot_character_destruction_traces()
                elif path == "Nihility":
                    traces_dict = self._screenshot.screenshot_character_nihility_traces()
                elif path == "Abundance":
                    traces_dict = self._screenshot.screenshot_character_abundance_traces()
                else:
                    raise ValueError("Invalid path")

                stats_dict["traces"] = traces_dict

                self._nav.move_cursor_to(*NAV_DATA["eidelons_button"])
                time.sleep(0.1)
                self._nav.click()
                time.sleep(1.5)

                eidlon_images = self._screenshot.screenshot_character_eidelons()

                task = asyncio.to_thread(
                    self.parse_character, stats_dict, eidlon_images)
                tasks.add(task)
            except Exception as e:
                print(e)
                traceback.print_exc()
                self.logger.emit(
                    f"Failed to parse character {character_name}. Got \"{e}\" error. Skipping...")

            self._nav.move_cursor_to(*NAV_DATA["details_button"])
            time.sleep(0.1)
            self._nav.click()
            time.sleep(0.1)

            if character_count - 1 == NAV_DATA["chars_per_scan"]:
                x, y = NAV_DATA["char_start"]
                i += 1
                x = x + NAV_DATA["offset_x"] * i
                self._nav.move_cursor_to(x, y)
                time.sleep(0.1)
                self._nav.click()
                time.sleep(0.1)
                x, y = NAV_DATA["list_button"]
                self._nav.move_cursor_to(x, y)
                time.sleep(0.1)
                self._nav.click()
                time.sleep(0.3)
            elif character_count <= NAV_DATA["chars_per_scan"]:
                x, y = NAV_DATA["char_end"]
                x -= NAV_DATA["offset_x"] * (character_count - 2)
            elif i == NAV_DATA["chars_per_scan"] - 1:
                i = 0
                x, y = NAV_DATA["char_start"]
            else:
                x, y = NAV_DATA["char_start"]
                i += 1
                x = x + NAV_DATA["offset_x"] * i

            character_count -= 1

        self._nav.key_press(Key.esc)
        time.sleep(1)
        self._nav.key_press(Key.esc)
        return tasks

    def parse_character(self, stats_dict, eidlon_images):
        if self.interrupt.is_set():
            return

        character = {
            "key": stats_dict["name"],
            "level": 1,
            "ascension": stats_dict["ascension"],
            "eidelon": 0,
            "skills": {
                "basic": 0,
                "skill": 0,
                "ult": 0,
                "talent": 0,
            },
            "traces": {},
        }

        level = stats_dict["level"]
        level = image_to_string(level, "0123456789", 7, True)
        try:
            character["level"] = int(level)
        except ValueError:
            self.logger.emit(f"{character['key']}: Failed to parse level." +
                             (f" Got \"{level}\" instead." if level else ""))

        lock = Image.open(resource_path("./images/lock2.png"))

        for img in eidlon_images:
            img = img.convert("L")
            min_dim = min(img.size)
            temp = lock.resize((min_dim, min_dim))
            unlocked = pyautogui.locate(temp, img, confidence=0.8) is None
            if not unlocked:
                break

            character["eidelon"] += 1

        if character["eidelon"] >= 5:
            character["skills"]["basic"] -= 1
            character["skills"]["skill"] -= 2
            character["skills"]["ult"] -= 2
            character["skills"]["talent"] -= 2
        elif character["eidelon"] >= 3:
            for k, v in get_character_meta_data(character["key"])["e3"].items():
                character["skills"][k] -= v

        traces_dict = stats_dict["traces"]
        for k, v in traces_dict["levels"].items():
            v = image_to_string(v, "0123456789", 6, True)
            if not v:
                # Assuming level is max since it didn't parse any numbers
                if k == "basic":
                    v = 7
                else:
                    v = 12
            character["skills"][k] += int(v)

        for k, v in traces_dict["locks"].items():
            min_dim = min(v.size)
            temp = lock.resize((min_dim, min_dim))
            unlocked = pyautogui.locate(temp, v, confidence=0.2) is None
            character["traces"][k] = unlocked

        if self.update_progress:
            self.update_progress.emit(102)

        return character

    def is_trailblazer(self, char):
        for c in {"trailblazerm", "trailblazerf"}:
            trailblazer = Image.open(resource_path(f"images\\{c}.png"))
            trailblazer = trailblazer.resize(char.size)
            if pyautogui.locate(char, trailblazer, confidence=0.8) is not None:
                return True

        return False
