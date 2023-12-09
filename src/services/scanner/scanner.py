from utils.navigation import Navigation
import win32gui
import time
from utils.screenshot import Screenshot
import asyncio
from .strategies.light_cone_strategy import LightConeStrategy
from .strategies.relic_strategy import RelicStrategy
from pynput.keyboard import Key
from utils.helpers import image_to_string, resource_path, preprocess_char_count_img
import pyautogui
from .character_parser import CharacterParser
from config.character_scan import CHARACTER_NAV_DATA
from PIL import Image
from models.game_data import GameData
from PyQt6 import QtCore
from enums.increment_type import IncrementType

SUPPORTED_ASPECT_RATIOS = ["16:9"]


class HSRScanner(QtCore.QObject):
    """HSRScanner class is responsible for scanning the game for light cones, relics, and characters"""

    update_signal = QtCore.pyqtSignal(int)
    log_signal = QtCore.pyqtSignal(str)
    complete_signal = QtCore.pyqtSignal()

    def __init__(self, config: dict, game_data: GameData) -> None:
        """Constructor

        :param config: The config dict
        :param game_data: The GameData class instance
        :raises Exception: Thrown if the game is not found
        :raises Exception: Thrown if no scan options are selected
        """
        super().__init__()
        for i, game_name in enumerate(["Honkai: Star Rail", "崩坏：星穹铁道", "崩壞：星穹鐵道"]):
            self._hwnd = win32gui.FindWindow("UnityWndClass", game_name)
            if self._hwnd:
                self._is_en = i == 0
                break
        if not self._hwnd:
            raise Exception(
                "Honkai: Star Rail not found. Please open the game and try again."
            )
        self._game_data = game_data
        self._config = config
        self._nav = Navigation(self._hwnd)

        self._aspect_ratio = self._nav.get_aspect_ratio()
        if self._aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
            raise Exception(
                f"Aspect ratio {self._aspect_ratio} not supported. Supported aspect ratios: {SUPPORTED_ASPECT_RATIOS}"
            )

        self._screenshot = Screenshot(self._hwnd, self._aspect_ratio)
        self._databank_img = Image.open(resource_path("assets/images/databank.png"))

        self._interrupt_event = asyncio.Event()

    async def start_scan(self) -> dict:
        """Starts the scan

        :return: The scan results
        """
        if not self._is_en:
            self.log_signal.emit(
                "WARNING: Non-English game name detected. The scanner only works with English text."
            )
        self._nav.bring_window_to_foreground()

        light_cones = []
        if self._config["scan_light_cones"] and not self._interrupt_event.is_set():
            light_cones = self.scan_inventory(
                LightConeStrategy(
                    self._game_data,
                    self.log_signal,
                    self.update_signal,
                    self._interrupt_event,
                )
            )
            self.log_signal.emit(
                "Finished scanning light cones"
            ) if not self._interrupt_event.is_set() else None

        relics = []
        if self._config["scan_relics"] and not self._interrupt_event.is_set():
            relics = self.scan_inventory(
                RelicStrategy(
                    self._game_data,
                    self.log_signal,
                    self.update_signal,
                    self._interrupt_event,
                )
            )
            self.log_signal.emit(
                "Finished scanning relics"
            ) if not self._interrupt_event.is_set() else None

        characters = []
        if self._config["scan_characters"] and not self._interrupt_event.is_set():
            characters = self.scan_characters()
            self.log_signal.emit(
                "Finished scanning characters"
            ) if not self._interrupt_event.is_set() else None

        if self._interrupt_event.is_set():
            await asyncio.gather(*light_cones, *relics, *characters)
            return

        self.complete_signal.emit()

        return {
            "source": "HSR-Scanner",
            "version": 3,
            "light_cones": await asyncio.gather(*light_cones),
            "relics": await asyncio.gather(*relics),
            "characters": await asyncio.gather(*characters),
        }

    def stop_scan(self) -> None:
        """Stops the scan"""
        self._interrupt_event.set()

    def scan_inventory(
        self, strategy: LightConeStrategy | RelicStrategy
    ) -> set[asyncio.Task]:
        """Scans the inventory for light cones or relics

        :param strategy: The strategy to use
        :raises ValueError: Thrown if the quantity could not be parsed
        :return: The tasks to await
        """
        nav_data = strategy.NAV_DATA[self._aspect_ratio]

        # Navigate to correct tab from cellphone menu
        time.sleep(1)
        self._nav.key_press(Key.esc)
        time.sleep(1)
        self._nav.key_press(self._config["inventory_key"])
        time.sleep(1)
        self._nav.move_cursor_to(*nav_data["inv_tab"])
        self._nav.click()
        time.sleep(1)

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

        current_sort_method = self._screenshot.screenshot_sort(strategy.SCAN_TYPE)
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
        num_times_scrolled = 0
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

                    if self._interrupt_event.is_set():
                        return tasks

                    # Next item
                    self._nav.move_cursor_to(x, y)
                    time.sleep(0.05)
                    self._nav.click()
                    time.sleep(0.1)
                    quantity_remaining -= 1

                    # Get stats
                    stats_dict = self._screenshot.screenshot_stats(strategy.SCAN_TYPE)
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
                    self.update_signal.emit(strategy.SCAN_TYPE.value)

                    task = asyncio.to_thread(strategy.parse, stats_dict)
                    tasks.add(task)

                # Next row
                x = nav_data["row_start_top"][0]
                y += nav_data["offset_y"]

            if quantity_remaining <= 0:
                break

            self._nav.scroll_page_down(num_times_scrolled)
            num_times_scrolled += 1

            time.sleep(0.5)

        self._nav.key_press(Key.esc)
        time.sleep(1.5)
        self._nav.key_press(Key.esc)
        return tasks

    def scan_characters(self) -> set[asyncio.Task]:
        """Scans the characters

        :raises ValueError: Thrown if the character count could not be parsed
        :return: The tasks to await
        """
        char_parser = CharacterParser(
            self._game_data, self.log_signal, self.update_signal, self._interrupt_event
        )
        nav_data = CHARACTER_NAV_DATA[self._aspect_ratio]

        # Assume ESC menu is open
        self._nav.bring_window_to_foreground()
        time.sleep(1)

        # Locate and click databank button
        haystack = self._screenshot.screenshot_screen()
        needle = self._databank_img.resize(
            # Scale image to match capture size
            (
                int(haystack.size[0] * 0.0296875),
                int(haystack.size[1] * 0.05625),
            )
        )
        self._nav.move_cursor_to_image(haystack, needle)
        time.sleep(0.1)
        self._nav.click()
        time.sleep(1)

        # Get character count
        character_total = self._screenshot.screenshot_character_count()
        character_total = image_to_string(
            character_total, "0123456789/", 7, True, preprocess_char_count_img
        )
        try:
            character_total, _ = character_total.split("/")
            character_count = character_total = int(character_total)
        except ValueError:
            raise ValueError(
                "Failed to parse character count from Data Bank screen."
                + (f' Got "{character_total}" instead.' if character_total else "")
                + " Did you start the scan from the ESC menu?"
            )

        # Update UI count
        for _ in range(character_count):
            self.update_signal.emit(IncrementType.CHARACTER_ADD.value)

        # Navigate to characters menu
        self._nav.key_press(Key.esc)
        time.sleep(1)
        self._nav.key_press(Key.esc)
        time.sleep(1)
        self._nav.key_press("1")
        time.sleep(0.2)
        self._nav.key_press(self._config["characters_key"])
        time.sleep(1)

        tasks = set()
        x, y = nav_data["char_start"]
        i = 0
        while character_count > 0:
            if self._interrupt_event.is_set():
                return tasks

            # Next character
            self._nav.move_cursor_to(x, y)
            time.sleep(0.2)
            self._nav.click()
            time.sleep(0.1)

            # Open details
            self._nav.move_cursor_to(*nav_data["details_button"])
            time.sleep(0.2)
            self._nav.click()
            time.sleep(0.2)

            # Get character name and path
            stats_dict = {}
            character_name = self._screenshot.screenshot_character_name()
            character_name = image_to_string(
                character_name,
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz/7",
                7,
            )
            try:
                path, character_name = map(str.strip, character_name.split("/")[:2])
                character_img = self._screenshot.screenshot_character()
                character_name, path = char_parser.get_closest_name_and_path(
                    character_name, path, character_img
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
                time.sleep(0.05)
                self._nav.click()
                time.sleep(0.5)

                traces_dict = self._screenshot.screenshot_character_traces(
                    path.lower().split(" ")[-1]
                )

                stats_dict["traces"] = {
                    "levels": traces_dict,
                    "unlocks": {},
                }
                path_key = path.split(" ")[-1].lower()
                for k, v in nav_data["traces"][path_key].items():
                    pixel = pyautogui.pixel(*self._nav.translate_percent_to_coords(*v))
                    dist = min(
                        sum([(a - b) ** 2 for a, b in zip(pixel, (255, 255, 255))]),
                        sum([(a - b) ** 2 for a, b in zip(pixel, (178, 200, 255))]),
                    )
                    stats_dict["traces"]["unlocks"][k] = dist < 3000

                # Get eidolons
                self._nav.move_cursor_to(*nav_data["eidolons_button"])
                time.sleep(0.1)
                self._nav.click()
                # First character's eidolons take longer to load
                time.sleep(1.5 if character_total == character_count else 0.9)
                eidolon_images = self._screenshot.screenshot_character_eidolons()

                task = asyncio.to_thread(char_parser.parse, stats_dict, eidolon_images)
                tasks.add(task)
            except Exception as e:
                self.log_signal.emit(
                    f'Failed to parse character {character_name}. Got "{e}" error. Skipping...'
                )

            if (
                character_count - 1 == nav_data["chars_per_scan"]
                or i == nav_data["chars_per_scan"] - 1
            ):
                x, y = nav_data["char_start"]
                i += 1
                x = x + nav_data["offset_x"] * i
                self._nav.move_cursor_to(x, y)
                time.sleep(0.05)
                self._nav.click()
                time.sleep(0.05)
                self._nav.drag_scroll(x, y, nav_data["char_start"][0] - 0.031, y)

                # Move mouse to avoid clicking anything on next iteration since
                # we're already on the correct character
                x, y = 0, 0
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

    def _ceildiv(self, a, b) -> int:
        """Divides a by b and rounds up

        :param a: The dividend
        :param b: The divisor
        :return: The quotient
        """
        return -(a // -b)
