import asyncio
import time

import pyautogui
import win32gui
from PIL import Image as PILImage
from pynput.keyboard import Key
from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from config.character_scan import CHARACTER_NAV_DATA
from config.const import (
    ASCENSION_OFFSET_X,
    ASCENSION_START,
    ASPECT_16_9,
    DETAILS_BUTTON,
    EIDOLONS_BUTTON,
    INV_TAB,
    SORT_BUTTON,
    TRACES,
    TRACES_BUTTON,
)
from enums.increment_type import IncrementType
from enums.log_level import LogLevel
from enums.scan_mode import ScanMode
from models.const import (
    CHAR_FILTERS,
    CHAR_LEVEL,
    CHAR_NAME,
    CHAR_PATH,
    CHAR_TRACES,
    CONFIG_CHARACTERS_KEY,
    CONFIG_DEBUG,
    CONFIG_DEBUG_OUTPUT_LOCATION,
    CONFIG_INCLUDE_UID,
    CONFIG_INVENTORY_KEY,
    CONFIG_NAV_DELAY,
    CONFIG_RECENT_RELICS_NUM,
    CONFIG_SCAN_CHARACTERS,
    CONFIG_SCAN_DELAY,
    CONFIG_SCAN_LC,
    CONFIG_SCAN_RELICS,
    EIDOLON_IMAGES,
    FILTERS,
    HSR_SCANNER,
    KEL_Z,
    LEVEL,
    MIN_LEVEL,
    MIN_RARITY,
    RARITY,
    SORT_DATE,
    SORT_LV,
    SORT_RARITY,
    TRACES_LEVELS,
    TRACES_UNLOCKS,
)
from models.game_data import GameData
from services.scanner.parsers.parse_strategy import BaseParseStrategy
from utils.data import resource_path
from utils.navigation import Navigation
from utils.ocr import image_to_string, preprocess_char_count_img, preprocess_uid_img
from utils.screenshot import Screenshot
from utils.window import bring_window_to_foreground

from .parsers.character_parser import CharacterParser
from .parsers.light_cone_strategy import LightConeStrategy
from .parsers.relic_strategy import RelicStrategy

SUPPORTED_ASPECT_RATIOS = [ASPECT_16_9]


class InterruptedScanException(Exception):
    """Exception raised when the scan is interrupted"""

    pass


class HSRScanner(QObject):
    """HSRScanner class is responsible for scanning the game for light cones, relics, and characters"""

    update_signal = pyqtSignal(int)
    log_signal = pyqtSignal(object)
    complete_signal = pyqtSignal()

    def __init__(self, config: dict, game_data: GameData, scan_mode: int = 0):
        """Constructor

        :param config: The config dict
        :param game_data: The GameData class instance
        :raises Exception: Thrown if the game is not found
        :raises Exception: Thrown if no scan options are selected
        """
        super().__init__()
        for i, game_name in enumerate(
            [
                "Honkai: Star Rail",
                "崩坏：星穹铁道",
                "崩壞：星穹鐵道",
                "붕괴:\u00a0스타레일",
                "崩壊：スターレイル",
                "Honkai\u00a0: Star Rail",
            ]
        ):
            self._hwnd = win32gui.FindWindow("UnityWndClass", game_name)
            if self._hwnd:
                self._is_en = i == 0
                break
        if not self._hwnd:
            raise Exception(
                "Honkai: Star Rail not found. Please open the game and try again."
            )
        self._config = config
        self._game_data = game_data
        self._scan_mode = scan_mode

        self._nav = Navigation(self._hwnd)

        self._aspect_ratio = self._nav.get_aspect_ratio()
        if self._aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
            raise Exception(
                f"Aspect ratio {self._aspect_ratio} not supported. Supported aspect ratios: {SUPPORTED_ASPECT_RATIOS}"
            )

        self._screenshot = Screenshot(
            self._hwnd,
            self.log_signal,
            self._aspect_ratio,
            config[CONFIG_DEBUG],
            config[CONFIG_DEBUG_OUTPUT_LOCATION],
        )
        self._databank_img = PILImage.open(resource_path("assets/images/databank.png"))

        self._interrupt_event = asyncio.Event()

    async def start_scan(self) -> dict:
        """Starts the scan

        :raises InterruptedScanException: Thrown if the scan is interrupted
        :return: The scan results
        """
        self._log("Config: " + str(self._config), LogLevel.DEBUG)

        if not self._is_en:
            self._log(
                "Non-English game name detected. The scanner only works with English text.",
                LogLevel.WARNING,
            )
        bring_window_to_foreground(self._hwnd)

        uid = None
        if self._config[CONFIG_INCLUDE_UID] and not self._interrupt_event.is_set():
            self._nav_sleep(1)
            uid_img = self._screenshot.screenshot_uid()
            uid = image_to_string(uid_img, "0123456789", 7, False, preprocess_uid_img)[
                :9
            ]
            if len(uid) != 9:
                uid = image_to_string(
                    uid_img, "0123456789", 7, True, preprocess_uid_img
                )[:9]
            if len(uid) != 9:
                self._log(f"Failed to parse UID. Got '{uid}' instead.", LogLevel.ERROR)
                uid = None
            else:
                self._log(f"UID: {uid}.")

        light_cones = []
        if self._config[CONFIG_SCAN_LC] and not self._interrupt_event.is_set():
            self._log("Scanning light cones...")
            light_cones = self.scan_inventory(
                LightConeStrategy(
                    self._game_data,
                    self.log_signal,
                    self.update_signal,
                    self._interrupt_event,
                    self._config[CONFIG_DEBUG],
                )
            )
            (
                self._log("Finished scanning light cones.")
                if not self._interrupt_event.is_set()
                else None
            )

        relics = []
        if self._config[CONFIG_SCAN_RELICS] and not self._interrupt_event.is_set():
            self._log("Scanning relics...")
            relics = self.scan_inventory(
                RelicStrategy(
                    self._game_data,
                    self.log_signal,
                    self.update_signal,
                    self._interrupt_event,
                    self._config[CONFIG_DEBUG],
                )
            )
            (
                self._log("Finished scanning relics.")
                if not self._interrupt_event.is_set()
                else None
            )

        characters = []
        if self._config[CONFIG_SCAN_CHARACTERS] and not self._interrupt_event.is_set():
            self._log("Scanning characters...")
            characters = self.scan_characters()
            (
                self._log("Finished scanning characters.")
                if not self._interrupt_event.is_set()
                else None
            )

        if self._interrupt_event.is_set():
            await asyncio.gather(*light_cones, *relics, *characters)
            return {}

        self.complete_signal.emit()
        self._log("Starting OCR process. Please wait...")

        return {
            "source": "HSR-Scanner",
            "build": "v1.4.0",
            "version": 4,
            "metadata": {
                "uid": int(uid) if uid else None,
                "trailblazer": (
                    "Stelle"
                    if QSettings(KEL_Z, HSR_SCANNER).value("is_stelle", True) == "true"
                    else "Caelus"
                ),
            },
            "light_cones": await asyncio.gather(*light_cones),
            "relics": await asyncio.gather(*relics),
            "characters": await asyncio.gather(*characters),
        }

    def stop_scan(self) -> None:
        """Stops the scan"""
        self._interrupt_event.set()

    def scan_inventory(self, strategy: BaseParseStrategy) -> set[asyncio.Task]:
        """Scans the inventory for light cones or relics

        :param strategy: The strategy to use
        :raises InterruptedScanException: Thrown if the scan is interrupted
        :raises ValueError: Thrown if the quantity could not be parsed
        :return: The tasks to await
        """
        nav_data = strategy.NAV_DATA[self._aspect_ratio]

        # Navigate to correct tab from cellphone menu
        self._nav_sleep(1)
        self._nav.key_tap(Key.esc)
        self._nav_sleep(2)
        self._nav.key_tap(self._config[CONFIG_INVENTORY_KEY])
        self._nav_sleep(1.5)

        # Get quantity
        max_retry = 5
        retry = 0
        while True:
            self._nav.move_cursor_to(*nav_data[INV_TAB])
            time.sleep(0.05)
            self._nav.click()
            self._nav_sleep(1.5)

            # TODO: using quantity to know when to scan the bottom row is not ideal
            #       because it will not work for tabs that do not have a quantity
            #       (i.e. materials).
            #
            #       for now, it will work for light cones and relics.
            quantity = self._screenshot.screenshot_quantity()
            quantity = image_to_string(quantity, "0123456789/", 7)

            try:
                self._log(f"Quantity: {quantity}.")
                quantity = quantity_remaining = int(quantity.split("/")[0])
                break
            except ValueError:
                retry += 1
                if retry > max_retry:
                    raise ValueError(
                        "Failed to parse quantity from inventory screen."
                        + (f' Got "{quantity}" instead.' if quantity else "")
                    )
                else:
                    self._log(
                        f"Failed to parse quantity. Retrying... ({retry}/{max_retry})",
                        LogLevel.WARNING,
                    )
                self._nav_sleep(1)

        current_sort_method = image_to_string(
            self._screenshot.screenshot_sort(), "RarityLvDate obtained", 7
        )
        optimal_sort_method = SORT_DATE
        if self._scan_mode != ScanMode.RECENT_RELICS.value:
            optimal_sort_method = strategy.get_optimal_sort_method(
                self._config[FILTERS]
            )

        if optimal_sort_method != current_sort_method:
            self._log(f"Sorting by {optimal_sort_method} (was {current_sort_method}).")
            self._nav.move_cursor_to(*nav_data[SORT_BUTTON])
            time.sleep(0.05)
            self._nav.click()
            self._nav_sleep(0.5)
            self._nav.move_cursor_to(*nav_data[optimal_sort_method])
            self._nav.click()
            current_sort_method = optimal_sort_method
            self._nav_sleep(0.5)

        tasks = set()
        scanned = 0

        def should_stop():
            if self._scan_mode == ScanMode.RECENT_RELICS.value:
                return (
                    quantity_remaining <= 0
                    or scanned >= self._config[CONFIG_RECENT_RELICS_NUM]
                )
            return quantity_remaining <= 0

        while not should_stop():
            quantity_remaining -= 1

            # Get stats
            stats_dict = self._screenshot.screenshot_stats(strategy.SCAN_TYPE)
            item_id = quantity - quantity_remaining

            # Check if item satisfies filters
            if FILTERS in self._config:
                filter_results, stats_dict = strategy.check_filters(
                    stats_dict,
                    self._config[FILTERS],
                    item_id,
                )
                if (
                    current_sort_method == SORT_LV
                    and MIN_LEVEL in filter_results
                    and not filter_results[MIN_LEVEL]
                ):
                    quantity_remaining = 0
                    self._log(
                        f"Reached minimum level filter (got level {stats_dict[LEVEL]})."
                    )
                    break
                if (
                    current_sort_method == SORT_RARITY
                    and MIN_RARITY in filter_results
                    and not filter_results[MIN_RARITY]
                ):
                    quantity_remaining = 0
                    self._log(
                        f"Reached minimum rarity filter (got rarity {stats_dict[RARITY]})."
                    )
                    break
                if (
                    self._scan_mode == ScanMode.RECENT_RELICS.value
                    and current_sort_method == SORT_DATE
                    and MIN_RARITY in filter_results
                    and filter_results[MIN_RARITY]
                ):
                    scanned += 1
                if not all(filter_results.values()):
                    self._nav.key_tap("d")
                    self._scan_sleep(0.05)
                    continue

            # Update UI count
            self.update_signal.emit(strategy.SCAN_TYPE.value)

            task = asyncio.to_thread(strategy.parse, stats_dict, item_id)
            tasks.add(task)

            # Next item
            self._nav.key_tap("d")
            self._scan_sleep(0.05)

        self._nav.key_tap(Key.esc)
        self._nav_sleep(2)
        self._nav.key_tap(Key.esc)
        self._nav_sleep(1)
        return tasks

    def scan_characters(self) -> set[asyncio.Task]:
        """Scans the characters

        :raises InterruptedScanException: Thrown if the scan is interrupted
        :raises ValueError: Thrown if the character count could not be parsed
        :return: The tasks to await
        """
        char_parser = CharacterParser(
            self._game_data,
            self.log_signal,
            self.update_signal,
            self._interrupt_event,
            self._config[CONFIG_DEBUG],
        )
        nav_data = CHARACTER_NAV_DATA[self._aspect_ratio]

        # Assume ESC menu is open
        bring_window_to_foreground(self._hwnd)
        self._nav_sleep(1)

        # Locate and click databank button
        self._log("Locating Data Bank button...", LogLevel.DEBUG)
        haystack = self._screenshot.screenshot_screen()
        needle = self._databank_img.resize(
            # Scale image to match capture size
            (
                int(haystack.size[0] * 0.0296875),
                int(haystack.size[1] * 0.05625),
            )
        )
        self._nav.move_cursor_to_image(haystack, needle)
        self._log(
            f"Data Bank button found at {self._nav.get_mouse_position()}.",
            LogLevel.DEBUG,
        )
        time.sleep(0.05)
        self._nav.click()
        self._nav_sleep(1)

        # Get character count
        max_retry = 5
        retry = 0
        while True:
            character_total = self._screenshot.screenshot_character_count()
            character_total = image_to_string(
                character_total, "0123456789/", 7, True, preprocess_char_count_img
            )
            try:
                self._log(f"Character total: {character_total}.")
                character_total = int(character_total.split("/")[0])
                break
            except ValueError:
                retry += 1
                if retry > max_retry:
                    raise ValueError(
                        "Failed to parse character count from Data Bank screen."
                        + (
                            f' Got "{character_total}" instead.'
                            if character_total
                            else ""
                        )
                    )
                else:
                    self._log(
                        f"Failed to parse character count. Retrying... ({retry}/{max_retry})",
                        LogLevel.WARNING,
                    )
                self._nav_sleep(1)

        # Navigate to characters menu
        self._nav.key_tap(Key.esc)
        self._nav_sleep(1)
        self._nav.key_tap(Key.esc)
        self._nav_sleep(1.5)
        self._nav.key_tap("1")
        self._nav_sleep(0.2)
        self._nav.key_tap(self._config[CONFIG_CHARACTERS_KEY])
        self._nav_sleep(1)

        tasks = set()
        characters_seen = set()

        res = [{} for _ in range(character_total)]

        # Details tab
        i = 0
        self._nav.move_cursor_to(*nav_data[DETAILS_BUTTON])
        time.sleep(0.05)
        self._nav.click()
        self._nav_sleep(0.5)
        self._nav.enter_gamepad()

        prev_trailblazer = False  # https://github.com/kel-z/HSR-Scanner/issues/49#issuecomment-1936613741
        while i < character_total:
            # Get name and path
            character_name = ""
            retry = 0
            while retry < max_retry and (
                not character_name or character_name in characters_seen
            ):
                try:
                    (self._scan_sleep(0.7) if prev_trailblazer else None)
                    character_name = (
                        # this has a small delay, can basically be treated as a sleep
                        self._get_character_name()
                    )
                    character_img = self._screenshot.screenshot_character()

                    # Trailblazer is the most prone to errors, need to ensure
                    # that all the elements have loaded before taking screenshots
                    # at the cost of small delay on Trailblazer
                    is_trailblazer = char_parser.is_trailblazer(character_img)
                    if is_trailblazer:
                        self._scan_sleep(0.7)

                    path, character_name = map(str.strip, character_name.split("/")[:2])
                    character_name, path = char_parser.get_closest_name_and_path(
                        character_name, path, is_trailblazer
                    )

                    if character_name in characters_seen:
                        self._log(
                            f"Parsed duplicate character '{character_name}'. Retrying... ({retry + 1}/{max_retry})",
                            LogLevel.WARNING,
                        )
                        self._scan_sleep(1)
                except Exception as e:
                    self._log(
                        f"Failed to parse character name. Got error: {e}. Retrying... ({retry + 1}/{max_retry})",
                        LogLevel.WARNING,
                    )
                    character_name = ""
                    self._scan_sleep(1)
                retry += 1

            if not character_name:
                self._log(
                    f"Failed to parse character name. Got '{character_name}' instead. Ending scan early.",
                    LogLevel.ERROR,
                )
                return tasks

            if character_name in characters_seen:
                self._log(
                    f"Duplicate character '{path} / {character_name}' scanned. Continuing scan anyway.",
                    LogLevel.ERROR,
                )
            else:
                characters_seen.add(character_name)
                self._log(
                    f"Character {i + 1}: {path} / {character_name}", LogLevel.TRACE
                )
            prev_trailblazer = character_name.startswith("Trailblazer")

            # Get ascension by counting ascension stars
            ascension_pos = nav_data[ASCENSION_START]
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
                    ascension_pos[0] + nav_data[ASCENSION_OFFSET_X],
                    ascension_pos[1],
                )

            res[i] = {
                "name": character_name,
                "path": path,
                "ascension": ascension,
                "level": self._screenshot.screenshot_character_level(),
            }

            # Check if character satisfies level filter
            min_level = self._config[FILTERS][CHAR_FILTERS].get(MIN_LEVEL, 1)
            if min_level > 1:
                res[i][CHAR_LEVEL] = character_level = char_parser.get_level(
                    res[i][CHAR_LEVEL]
                )
                if character_level < min_level and i < 4:
                    self._log(
                        f"{character_name} is below minimum level filter (got level {character_level}). Skipping...",
                        LogLevel.TRACE,
                    )
                    res[i] = {}

                    # Don't go right if we are on the last character
                    if i == character_total - 1:
                        break
                    i += 1
                    self._nav.press_gamepad_rb()
                    self._scan_sleep(0.1)
                    continue
                elif character_level < min_level:
                    self._log(
                        f"Reached minimum level filter (got level {character_level} for {character_name}).",
                    )
                    res = res[:i]
                    i -= 1
                    self._nav.press_gamepad_lb()
                    self._scan_sleep(0.1)
                    break

            # Update UI count
            self.update_signal.emit(IncrementType.CHARACTER_ADD.value)

            # Don't go right if we are on the last character
            if i == character_total:
                break
            i += 1
            self._nav.press_gamepad_rb()
            self._scan_sleep(0.1)
        self._nav.exit_gamepad()

        # Traces tab
        self._nav.move_cursor_to(*nav_data[TRACES_BUTTON])
        time.sleep(0.05)
        self._nav.click()
        self._nav_sleep(2)
        self._nav.enter_gamepad()
        while i >= 0:
            if not res[i]:
                # Don't go left if we are on the first character
                if i == 0:
                    break
                i -= 1
                self._nav.press_gamepad_lb()
                self._scan_sleep(0.1)
                continue
            path_key = res[i][CHAR_PATH].split(" ")[-1].lower()
            traces_dict = self._screenshot.screenshot_character_traces(path_key)
            res[i][CHAR_TRACES] = {
                TRACES_LEVELS: traces_dict,
                TRACES_UNLOCKS: {},
            }
            for k, v in nav_data[TRACES][path_key].items():
                # Trace is unlocked if pixel is white
                pixel = pyautogui.pixel(*self._nav.translate_percent_to_coords(*v))
                dist = min(
                    sum([(a - b) ** 2 for a, b in zip(pixel, (255, 255, 255))]),
                    sum([(a - b) ** 2 for a, b in zip(pixel, (178, 200, 255))]),
                )
                res[i][CHAR_TRACES][TRACES_UNLOCKS][k] = dist < 3000

            # Don't go left if we are on the first character
            if i == 0:
                break
            i -= 1
            self._nav.press_gamepad_lb()
            self._scan_sleep(0.6)
        self._nav.exit_gamepad()

        # Eidolons tab
        self._nav.move_cursor_to(*nav_data[EIDOLONS_BUTTON])
        time.sleep(0.05)
        self._nav.click()
        self._nav_sleep(1.5)
        self._nav.enter_gamepad()
        while i < len(res):
            if not res[i]:
                i += 1
                self._nav.press_gamepad_rb()
                self._scan_sleep(0.1)
                continue
            res[i][EIDOLON_IMAGES] = self._screenshot.screenshot_character_eidolons()
            i += 1
            self._nav.press_gamepad_rb()
            self._scan_sleep(0.5)
        self._nav.exit_gamepad()

        # Queue character data for parsing
        for stats_dict in res:
            if not stats_dict:
                continue
            task = asyncio.to_thread(char_parser.parse, stats_dict)
            tasks.add(task)

        self._nav_sleep(1)
        self._nav.key_tap(Key.esc)
        self._nav_sleep(2)
        self._nav.key_tap(Key.esc)
        self._nav_sleep(1)
        return tasks

    def _log(self, msg: str, level: LogLevel = LogLevel.INFO) -> None:
        """Logs a message

        :param msg: The message to log
        :param level: The log level
        """
        if self._config[CONFIG_DEBUG] or level in [
            LogLevel.INFO,
            LogLevel.WARNING,
            LogLevel.ERROR,
        ]:
            self.log_signal.emit((msg, level))

    def _get_character_name(self) -> str:
        """Gets the character name

        :return: The character name
        """
        character_name_img = self._screenshot.screenshot_character_name()
        return image_to_string(
            character_name_img,
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz/7&",
            7,
        )

    def _nav_sleep(self, seconds: float) -> None:
        """Sleeps for the specified amount of time with navigation delay

        :param seconds: The amount of time to sleep
        :raises InterruptedScanException: Thrown if the scan is interrupted
        """
        time.sleep(seconds + self._config[CONFIG_NAV_DELAY])
        if self._interrupt_event.is_set():
            raise InterruptedScanException()

    def _scan_sleep(self, seconds: float) -> None:
        """Sleeps for the specified amount of time with scan delay

        :param seconds: The amount of time to sleep
        :raises InterruptedScanException: Thrown if the scan is interrupted
        """
        time.sleep(seconds + self._config[CONFIG_SCAN_DELAY])
        if self._interrupt_event.is_set():
            raise InterruptedScanException()

    def _ceildiv(self, a, b) -> int:
        """Divides a by b and rounds up

        :param a: The dividend
        :param b: The divisor
        :return: The quotient
        """
        return -(a // -b)
