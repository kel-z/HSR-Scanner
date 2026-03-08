import re

import numpy as np
from PIL import Image as PILImage
from PIL.Image import Image
from pyautogui import locate, ImageNotFoundException

from config.const import EQUIPPED, EQUIPPED_AVATAR, EQUIPPED_AVATAR_OFFSET, LOCK
from config.relic_scan import RELIC_NAV_DATA
from enums.increment_type import IncrementType
from enums.log_level import LogLevel
from models.const import (
    FILTER_MAX,
    FILTER_MIN,
    RELIC_DISCARD,
    RELIC_LEVEL,
    RELIC_LOCATION,
    RELIC_MAINSTAT,
    RELIC_NAME,
    RELIC_RARITY,
    MIN_LEVEL,
    MIN_RARITY,
    RELIC_FILTERS,
    RELIC_SET,
    RELIC_SET_ID,
    RELIC_SLOT,
    RELIC_SUBSTAT_NAME,
    RELIC_UNACTIVATED_SUBSTATS,
    RELIC_SUBSTAT_VALUE,
    RELIC_SUBSTAT_VALUES,
    RELIC_SUBSTATS,
    RELIC_SUBSTAT_NAMES,
    SORT_LV,
    SORT_RARITY,
)
from models.substat_vals import SUBSTAT_ROLL_VALS
from services.scanner.parsers.parse_strategy import BaseParseStrategy
from type_defs.stats_dict import RelicDict
from utils.data import filter_images_from_dict, resource_path
from utils.ocr import (
    DIN_ALTERNATE,
    image_to_string,
    preprocess_equipped_img,
    preprocess_level_img,
    preprocess_main_stat_img,
    preprocess_sub_stat_img,
)


class RelicStrategy(BaseParseStrategy):
    """RelicStrategy class for parsing relic data from screenshots."""

    SCAN_TYPE = IncrementType.RELIC_ADD
    NAV_DATA = RELIC_NAV_DATA

    def __init__(self, *args, **kwargs) -> None:
        """Constructor"""
        super().__init__(*args, **kwargs)
        self._discard_icon = PILImage.open(resource_path("assets/images/discard.png"))

    def _parse_level_int(self, level: str | int | Image | None) -> int | None:
        """Extract integer level from OCR text.

        Returns None when OCR did not contain any digits.
        """
        if isinstance(level, int):
            return level
        if level is None or isinstance(level, Image):
            return None

        level_digits = re.sub(r"\D", "", str(level))
        if not level_digits:
            return None

        return int(level_digits)

    def _save_debug_image(self, img: Image, uid: int, suffix: str) -> None:
        """Saves a debug image for a failed parse.

        :param img: The PIL Image to save
        :param uid: The relic UID
        :param suffix: A descriptive suffix for the filename (e.g. 'level_failed')
        """
        if not self._debug:
            return

        import os
        from datetime import datetime

        # Save into the active scan debug folder when available.
        # Fallback to cwd so parser-only runs still work.
        base_dir = self._debug_output_location or os.getcwd()
        debug_dir = os.path.join(base_dir, "failures")
        os.makedirs(debug_dir, exist_ok=True)

        filename = f"relic_{uid}_{suffix}_{datetime.now().strftime('%H%M%S_%f')}.png"
        path = os.path.join(debug_dir, filename)

        try:
            img.save(path)
            self._log(f"Saved failure image for Relic UID {uid}: {path}", LogLevel.DEBUG)
        except Exception as e:
            self._log(f"Failed to save debug image: {e}", LogLevel.ERROR)

    def _parse_icon_flag(
        self,
        uid: int,
        key: str,
        haystack: Image,
        icon: Image,
    ) -> bool:
        """Parse lock/discard icon with guarded image matching.

        Returns False on any parsing error and logs details for diagnostics.
        """
        if not isinstance(haystack, Image):
            self._log(
                f"Relic UID {uid}: Failed to parse {key}. Input is not an image (type={type(haystack).__name__}). Setting to False.",
                LogLevel.ERROR,
            )
            return False

        if haystack.size[0] <= 0 or haystack.size[1] <= 0:
            self._log(
                f"Relic UID {uid}: Failed to parse {key}. Invalid image size {haystack.size}. Setting to False.",
                LogLevel.ERROR,
            )
            return False

        min_dim = min(haystack.size)
        try:
            # Normalize mode to avoid locate failures on palette/alpha edge cases.
            icon_img = icon.convert("RGB").resize((min_dim, min_dim))
            haystack_img = haystack.convert("RGB")
            return locate(icon_img, haystack_img, confidence=0.3) is not None
        except ImageNotFoundException:
            return False
        except Exception as e:
            self._log(
                f"Relic UID {uid}: Failed to parse {key}. Setting to False. Exception: {type(e).__name__}: {e}",
                LogLevel.ERROR,
            )
            self._save_debug_image(haystack, uid, f"{key}_parse_failed")
            return False

    def get_optimal_sort_method(self, filters: dict) -> str:
        """Gets the optimal sort method based on the filters

        :param filters: The filters
        :return: The optimal sort method
        """
        if filters[RELIC_FILTERS][MIN_LEVEL] > 0:
            return SORT_LV
        else:
            return SORT_RARITY

    def check_filters(
        self, stats_dict: RelicDict, filters: dict, uid: int
    ) -> tuple[dict, RelicDict]:
        """Checks if the relic passes the filters

        :param stats_dict: The stats dict
        :param filters: The filters
        :param uid: The relic UID
        :raises ValueError: Thrown if the filter key does not have an int value
        :return: A tuple of the filter results and the stats dict
        """
        filters = filters[RELIC_FILTERS]

        filter_results = {}
        for key in filters:
            filter_type, filter_key = key.split("_")

            val = stats_dict[filter_key] if filter_key in stats_dict else None

            if not val or isinstance(val, Image):
                if key == MIN_RARITY:
                    # Trivial case
                    if filters[key] <= 2:
                        filter_results[key] = True
                        continue
                    val = stats_dict[RELIC_RARITY] = self.extract_stats_data(  # type: ignore
                        filter_key, stats_dict[RELIC_RARITY]
                    )
                elif key == MIN_LEVEL:
                    # Trivial case
                    if filters[key] <= 0:
                        filter_results[key] = True
                        continue
                    level = self.extract_stats_data(
                        RELIC_LEVEL, stats_dict[RELIC_LEVEL]
                    )
                    if not level or isinstance(level, Image):
                        self._log(
                            f"Relic UID {uid}: Failed to extract level for filtering. Raw OCR was: {repr(level)}",
                            LogLevel.ERROR,
                        )
                        if isinstance(stats_dict[RELIC_LEVEL], Image):
                            self._save_debug_image(
                                stats_dict[RELIC_LEVEL], uid, "level_filter_failed"
                            )
                        stats_dict[RELIC_LEVEL] = 0
                        filter_results[key] = True
                        continue

                    parsed_level = self._parse_level_int(level)
                    if parsed_level is None:
                        self._log(
                            f"Relic UID {uid}: Failed to parse level digits for filtering. Raw OCR was: {repr(level)}",
                            LogLevel.ERROR,
                        )
                        if isinstance(stats_dict[RELIC_LEVEL], Image):
                            self._save_debug_image(
                                stats_dict[RELIC_LEVEL], uid, "level_filter_digits_failed"
                            )
                        stats_dict[RELIC_LEVEL] = 0
                        # Do not fail filter on OCR parse errors; avoid early scan termination.
                        filter_results[key] = True
                        continue

                    val = stats_dict[RELIC_LEVEL] = parsed_level

            if not isinstance(val, int):
                raise ValueError(f"Filter key {key} does not have an int value.")

            if filter_type == FILTER_MIN:
                filter_results[key] = val >= filters[key]
            elif filter_type == FILTER_MAX:
                filter_results[key] = val <= filters[key]

        return (filter_results, stats_dict)

    def extract_stats_data(
        self, key: str, data: str | int | Image
    ) -> str | int | Image:
        """Extracts the stats data from the image

        :param key: The key
        :param data: The data
        :return: The extracted data, or the image if the key is not relevant
        """
        if not isinstance(data, Image):
            return data

        if key == RELIC_NAME:
            res = image_to_string(
                data,
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ \\'abcedfghijklmnopqrstuvwxyz-",
                6,
                lang=f"eng+{DIN_ALTERNATE}",
            )
            if res.endswith(" O"):
                res = res[:-2].strip()
            return res
        elif key == RELIC_LEVEL:
            return (
                image_to_string(
                    data,
                    "0123456789S+",
                    13,
                    True,
                    preprocess_level_img,
                    lang=f"eng+{DIN_ALTERNATE}",
                )
                .replace("S", "5")
                .replace("+", "")
            )
        elif key == RELIC_MAINSTAT:
            return image_to_string(
                data,
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz+",
                7,
                True,
                preprocess_main_stat_img,
            )
        elif key == EQUIPPED:
            return image_to_string(data, "Equiped", 7, True, preprocess_equipped_img)
        elif key == RELIC_RARITY:
            # Get rarity by color matching
            rarity_sample = np.array(data)
            rarity_sample = rarity_sample[int(rarity_sample.shape[0] / 2)][
                int(rarity_sample.shape[1] / 2)
            ]
            return self._game_data.get_closest_rarity(rarity_sample)
        elif key == RELIC_SUBSTAT_NAMES:
            return image_to_string(
                data,
                " ABCDEFGHIKMPRSTacefikrt()+0123456789ov",
                6,
                True,
                preprocess_sub_stat_img,
                False,
            )
        elif key == RELIC_SUBSTAT_VALUES:
            return (
                image_to_string(
                    data, "0123456789S.%,", 6, True, preprocess_sub_stat_img, False
                )
                .replace("S", "5")
                .replace(",", ".")
                .replace("..", ".")
            )
        else:
            return data

    def parse(self, stats_dict: RelicDict, uid: int) -> dict:
        """Parses the relic data

        :param stats_dict: The stats dict
        :param uid: The relic UID
        :return: The parsed relic data
        """
        if self._interrupt_event.is_set():
            return {}

        try:
            # Keep a copy of raw images for debug saving before they are OCRed into strings
            raw_stats = stats_dict.copy()
            for key in stats_dict:
                stats_dict[key] = self.extract_stats_data(key, stats_dict[key])

            (
                self._log(
                    f"Relic UID {uid}: Raw data: {filter_images_from_dict(stats_dict)}",
                    LogLevel.DEBUG,
                )
                if self._debug
                else None
            )

            name = stats_dict[RELIC_NAME]
            level = stats_dict[RELIC_LEVEL]
            main_stat_key = stats_dict[RELIC_MAINSTAT]
            lock = stats_dict[LOCK]
            discard = stats_dict[RELIC_DISCARD]
            rarity = stats_dict[RELIC_RARITY]
            equipped = stats_dict[EQUIPPED]
            substat_names = stats_dict[RELIC_SUBSTAT_NAMES]
            substat_vals = stats_dict[RELIC_SUBSTAT_VALUES]

            # Fix OCR errors
            name, _ = self._game_data.get_closest_relic_name(name)  # type: ignore
            main_stat_key, _ = self._game_data.get_closest_relic_main_stat(main_stat_key)  # type: ignore

            parsed_level = self._parse_level_int(level)
            if parsed_level is None:
                self._log(
                    f"Relic UID {uid}: Failed to extract level. Setting to 0. Raw OCR was: {repr(level)}",
                    LogLevel.ERROR,
                )
                if isinstance(raw_stats.get(RELIC_LEVEL), Image):
                    self._save_debug_image(
                        raw_stats[RELIC_LEVEL], uid, "level_parse_failed"
                    )
                level = 0
            else:
                level = parsed_level

            if not name:
                self._log(
                    f'Relic UID {uid}: Failed to extract name. Setting to "Musketeer\'s Wild Wheat Felt Hat".',
                    LogLevel.ERROR,
                )
                if isinstance(raw_stats.get(RELIC_NAME), Image):
                    self._save_debug_image(
                        raw_stats[RELIC_NAME], uid, "name_extract_failed"
                    )
                name = "Musketeer's Wild Wheat Felt Hat"

            # Substats
            while "\n\n" in substat_names:  # type: ignore
                substat_names = substat_names.replace("\n\n", "\n")  # type: ignore
            while "\n\n" in substat_vals:  # type: ignore
                substat_vals = substat_vals.replace("\n\n", "\n")  # type: ignore
            substat_names = substat_names.split("\n")  # type: ignore
            substat_vals = substat_vals.split("\n")  # type: ignore

            substats_res, unactivated_substats_res = self._parse_substats(
                substat_names, substat_vals, uid, raw_stats
            )
            self._validate_substats(substats_res, rarity, level, uid, raw_stats)  # type: ignore

            # Set and slot
            metadata = self._game_data.get_relic_meta_data(name)
            set_id = str(metadata[RELIC_SET_ID])
            set_name = metadata[RELIC_SET]
            slot_key = metadata[RELIC_SLOT]
            if slot_key == "Hands":
                main_stat_key = "ATK"
            elif slot_key == "Head":
                main_stat_key = "HP"
            elif not main_stat_key:
                self._log(
                    f"Relic UID {uid}: Failed to extract main stat. Setting to ATK.",
                    LogLevel.ERROR,
                )
                main_stat_key = "ATK"

            # Check if locked/discarded by image matching
            lock = self._parse_icon_flag(uid, "lock", lock, self._lock_icon)
            discard = self._parse_icon_flag(uid, "discard", discard, self._discard_icon)

            location = ""
            outfit_id = None
            if equipped == "Equipped":
                equipped_avatar = stats_dict[EQUIPPED_AVATAR]
                location, outfit_id = self._game_data.get_equipped_character(
                    equipped_avatar
                )
            elif (
                equipped == "Equippe"
            ):  # https://github.com/kel-z/HSR-Scanner/issues/88
                equipped_avatar = stats_dict[EQUIPPED_AVATAR_OFFSET]
                location, outfit_id = self._game_data.get_equipped_character(
                    equipped_avatar
                )

            if outfit_id:
                self._log(
                    f"Relic UID {uid}: Equipped character is {location} with outfit ID {outfit_id}.",
                    LogLevel.DEBUG,
                )

            result = {
                RELIC_SET_ID: set_id,
                RELIC_NAME: set_name,
                RELIC_SLOT: slot_key,
                RELIC_RARITY: rarity,
                RELIC_LEVEL: level,
                RELIC_MAINSTAT: main_stat_key,
                RELIC_SUBSTATS: substats_res,
                RELIC_UNACTIVATED_SUBSTATS: unactivated_substats_res,
                RELIC_LOCATION: location,
                LOCK: lock,
                RELIC_DISCARD: discard,
                "_uid": f"relic_{uid}",
            }

            self._update_signal.emit(IncrementType.RELIC_SUCCESS.value)

            return result
        except Exception as e:
            self._log(
                f"Failed to parse relic {uid}. stats_dict={stats_dict}, exception={e}",
                LogLevel.ERROR,
            )
            return {}

    def _parse_substats(
        self,
        names: list[str],
        vals: list[str],
        uid: int,
        stats_dict: RelicDict | None = None,
    ) -> tuple[list[dict[str, int | float]], list[dict[str, int | float]]]:
        """Parses the substats

        :param names: The substat names
        :param vals: The substat values
        :param uid: The relic UID
        :param stats_dict: The stats dictionary (optional, for debug images)
        :return: A tuple of active and unactivated substats
        """
        self._log(
            f"Relic UID {uid}: Parsing substats. Substats: {names}, Values: {vals}",
            LogLevel.TRACE,
        )

        # Clean lists of empty strings from OCR artifacts (extra newlines)
        names = [n.strip() for n in names if n.strip()]
        vals = [v.strip() for v in vals if v.strip()]

        active_substats = []
        unactivated_substats = []
        # Only non-ambiguous percent stats can be inferred without an explicit '%' symbol.
        percentage_name_hints = {
            "HP_",
            "ATK_",
            "DEF_",
            "CRIT Rate",
            "CRIT DMG",
            "Effect Hit Rate",
            "Effect RES",
            "Break Effect",
            "CRIT Rate_",
            "CRIT DMG_",
            "Effect Hit Rate_",
            "Effect RES_",
            "Break Effect_",
        }
        for i in range(len(names)):
            raw_name = names[i]
            is_unactivated = "(" in raw_name
            # Strip inactive/grayed-out text from game update (e.g. " (+3 to activate)")
            name = raw_name
            if "(" in name:
                name = name[:name.index("(")].strip()

            name, dist = self._game_data.get_closest_relic_sub_stat(name)
            if dist > 3:
                self._log(
                    f"Relic UID {uid}: Substat name matching failed for '{raw_name}' (Index {i}, Distance {dist}).",
                    LogLevel.ERROR,
                )
                if stats_dict and isinstance(stats_dict.get(RELIC_SUBSTAT_NAMES), Image):
                    self._save_debug_image(stats_dict[RELIC_SUBSTAT_NAMES], uid, f"substat_name_{i}_failed")
                continue

            if i >= len(vals):
                self._log(
                    f"Relic UID {uid}: Missing value for substat '{name}' (Index {i}). All values found: {vals}",
                    LogLevel.ERROR,
                )
                if stats_dict and isinstance(stats_dict.get(RELIC_SUBSTAT_VALUES), Image):
                    self._save_debug_image(stats_dict[RELIC_SUBSTAT_VALUES], uid, f"substat_value_{i}_missing")
                continue
            val = vals[i]

            try:
                # Cleanup common OCR value issues
                val = val.replace("S", "5").replace(",", ".")

                # Heuristic: if a value ends in .30, .40, .10 etc, it's likely a misread percentage (e.g. 4.3% -> 4.30)
                # But ONLY apply this if we already know the stat is a percentage based on the name from game database.
                name_is_percentage = name in percentage_name_hints

                # OCR often drops '%' for gray inactive HP/ATK/DEF lines and leaves values like "4.8".
                # Flat HP/ATK/DEF substats are integers in-game, so a single-digit decimal strongly indicates percent.
                missing_percent_on_flat = (
                    name in {"HP", "ATK", "DEF"} and re.fullmatch(r"\d\.\d", val) is not None
                )

                is_percentage = (
                    "%" in val
                    or missing_percent_on_flat
                    or (name_is_percentage and len(val) > 3 and val.endswith("0") and "." in val)
                )

                if is_percentage:
                    # Strip everything after and including the % or the suspect trailing zero
                    clean_val = val
                    if "%" in clean_val:
                        clean_val = clean_val[: clean_val.index("%")]
                    elif clean_val.endswith("0") and not val.endswith(".0"):
                        # Avoid converting 16.0 -> 1.6
                        clean_val = clean_val[:-1]

                    val = float(clean_val)
                    if not name.endswith("_"):
                        name += "_"
                else:
                    val = int(float(val))  # float then int handles "16.0" strings

                parsed_substat = {"key": name, "value": val}
                if is_unactivated:
                    unactivated_substats.append(parsed_substat)
                else:
                    active_substats.append(parsed_substat)
            except (ValueError, TypeError):
                self._log(
                    f"Relic UID {uid}: Failed to parse value '{val}' for substat '{name}' (Index {i}). Full value list: {vals}",
                    LogLevel.ERROR,
                )
                if stats_dict and isinstance(stats_dict.get(RELIC_SUBSTAT_VALUES), Image):
                    self._save_debug_image(stats_dict[RELIC_SUBSTAT_VALUES], uid, f"substat_value_{i}_failed")

        return active_substats, unactivated_substats

    def _validate_substat(self, substat: dict[str, int | float], rarity: int) -> bool:
        """Validates the substat

        :param substat: The substat
        :param rarity: The rarity of the relic
        :return: True if the substat is valid, False otherwise
        """
        try:
            name = substat[RELIC_SUBSTAT_NAME]
            val = substat[RELIC_SUBSTAT_VALUE]
            if name not in SUBSTAT_ROLL_VALS[str(rarity)]:
                return False
            if str(val) not in SUBSTAT_ROLL_VALS[str(rarity)][name]:
                return False
        except KeyError:
            return False

        return True

    def _validate_substats(
        self,
        substats: list[dict[str, int | float]],
        rarity: int,
        level: int,
        uid: int,
        stats_dict: RelicDict | None = None,
    ) -> None:
        """Rudimentary substat validation on number of substats based on rarity and level

        :param substats: The substats
        :param rarity: The rarity of the relic
        :param level: The level of the relic
        :param uid: The relic UID
        :param stats_dict: The stats dictionary (for debug images)
        """
        seen_substats = set()

        # check valid number of substats
        substats_len = len(substats)
        min_substats = min(rarity - 2 + int(level / 3), 4)
        if substats_len < min_substats:
            self._log(
                f"Relic UID {uid} has {substats_len} substat(s), but the minimum for rarity {rarity} and level {level} is {min_substats}.",
                LogLevel.ERROR,
            )
            return

        # check valid roll value total
        min_roll_value = round(min_substats * 0.8, 1)
        max_roll_value = round(rarity - 1 + int(level / 3), 1)
        total = 0
        for substat in substats:
            if substat[RELIC_SUBSTAT_NAME] in seen_substats:
                self._log(
                    f"Relic UID {uid}: More than one substat with key {substat[RELIC_SUBSTAT_NAME]} parsed.",
                    LogLevel.ERROR,
                )
                if stats_dict and isinstance(stats_dict.get(RELIC_SUBSTAT_NAMES), Image):
                    self._save_debug_image(stats_dict[RELIC_SUBSTAT_NAMES], uid, "duplicate_substat_name")
                return
            if not self._validate_substat(substat, rarity):
                self._log(
                    f'Relic UID {uid}: Substat {substat[RELIC_SUBSTAT_NAME]} has illegal value "{substat[RELIC_SUBSTAT_VALUE]}" for rarity {rarity}.',
                    LogLevel.ERROR,
                )
                if stats_dict and isinstance(stats_dict.get(RELIC_SUBSTAT_VALUES), Image):
                    self._save_debug_image(stats_dict[RELIC_SUBSTAT_VALUES], uid, "illegal_substat_value")
                return

            roll_value = SUBSTAT_ROLL_VALS[str(rarity)][
                str(substat[RELIC_SUBSTAT_NAME])
            ][str(substat[RELIC_SUBSTAT_VALUE])]
            if isinstance(roll_value, list):
                # assume minimum
                roll_value = roll_value[0]
            total += roll_value

        total = round(total, 1)
        if total < min_roll_value:
            self._log(
                f"Relic UID {uid} has a roll value of {total}, but the minimum for rarity {rarity} and level {level} is {min_roll_value}.",
                LogLevel.ERROR,
            )
        elif total > max_roll_value:
            self._log(
                f"Relic UID {uid} has a roll value of {total}, but the maximum for rarity {rarity} and level {level} is {max_roll_value}.",
                LogLevel.ERROR,
            )

    def _log(self, msg: str, level: LogLevel = LogLevel.INFO) -> None:
        """Logs a message

        :param msg: The message to log
        :param level: The log level
        """
        if self._debug or level in [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
            self._log_signal.emit((msg, level))
