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
    RELIC_PREVIEW_SUBSTATS,
    RELIC_SET,
    RELIC_SET_ID,
    RELIC_SLOT,
    RELIC_SUBSTAT_NAME,
    RELIC_SUBSTAT_VALUE,
    RELIC_SUBSTAT_VALUES,
    RELIC_SUBSTATS,
    RELIC_SUBSTAT_NAMES,
    SORT_LV,
    SORT_RARITY,
)
from models.game_data import RELIC_MAIN_STATS, RELIC_SUB_STATS
from services.scanner.parsers.parse_strategy import BaseParseStrategy
from type_defs.stats_dict import RelicDict
from utils.data import filter_images_from_dict, resource_path
from utils.ocr import (
    preprocess_relic_name_img,
    preprocess_relic_main_stat_img,
    preprocess_sub_stat_value_img,
    image_to_string,
    preprocess_equipped_img,
    preprocess_level_img,
    preprocess_sub_stat_img,
)
from utils.ocr_batch import batch_image_to_strings_chunked
from utils.ocr_profile import ocr_profile_context
from utils.scan_integrity import ScanIntegrityError
from utils.substat_validation import validate_substat_rolls
from utils.recognition_validation import validated_match, validate_main_stat_slot, normalize_text
from utils.avatar_matching import equipped_frame_present


class RelicStrategy(BaseParseStrategy):
    """RelicStrategy class for parsing relic data from screenshots."""

    SCAN_TYPE = IncrementType.RELIC_ADD
    NAV_DATA = RELIC_NAV_DATA
    BATCH_OCR_CHUNK_SIZE = 10

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

        level_digits = str(level).strip()
        if not re.fullmatch(r'\+?\d{1,2}', level_digits):
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

    def _parse_relic_lock_state(self, img: Image) -> bool:
        """Detect the active/gold relic lock state from the lock button crop."""
        arr = np.array(img.convert("RGB"))
        red = arr[:, :, 0]
        green = arr[:, :, 1]
        blue = arr[:, :, 2]

        white_ratio = np.mean((red > 220) & (green > 220) & (blue > 220))
        gold_ratio = np.mean((red > 145) & (green > 105) & (blue < 120))
        dark_ratio = np.mean((red < 80) & (green < 80) & (blue < 80))

        # Locked relics render as a gold button with a white lock; unlocked relics
        # render as a white button with a dark lock.
        return bool(gold_ratio >= 0.45 and white_ratio >= 0.05 and dark_ratio <= 0.03)

    def _parse_icon_flag(
        self,
        uid: int,
        key: str,
        haystack: Image,
        icon: Image,
    ) -> bool:
        """Parse lock/discard icon with guarded image matching.

        Known absent icons are false; processing failures invalidate the scan.
        """
        if not isinstance(haystack, Image):
            self._log(
                f"Relic UID {uid}: Failed to parse {key}. Input is not an image (type={type(haystack).__name__}). Setting to False.",
                LogLevel.ERROR,
            )
            raise ScanIntegrityError(f'Relic {uid}: invalid {key} image; incomplete scan, no export.')

        if haystack.size[0] <= 0 or haystack.size[1] <= 0:
            self._log(
                f"Relic UID {uid}: Failed to parse {key}. Invalid image size {haystack.size}. Setting to False.",
                LogLevel.ERROR,
            )
            raise ScanIntegrityError(f'Relic {uid}: empty {key} image; incomplete scan, no export.')

        min_dim = min(haystack.size)
        try:
            if key == LOCK:
                return self._parse_relic_lock_state(haystack)

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
            raise ScanIntegrityError(f'Relic {uid}: {key} recognition failed; incomplete scan, no export.') from e

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
                    with ocr_profile_context(
                        item_type="relic", uid=uid, field=filter_key, phase="filter"
                    ):
                        val = stats_dict[RELIC_RARITY] = self.extract_stats_data(  # type: ignore
                            filter_key, stats_dict[RELIC_RARITY]
                        )
                elif key == MIN_LEVEL:
                    # Trivial case
                    if filters[key] <= 0:
                        filter_results[key] = True
                        continue
                    with ocr_profile_context(
                        item_type="relic", uid=uid, field=RELIC_LEVEL, phase="filter"
                    ):
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
                        raise ScanIntegrityError(f'Relic {uid}: unreadable filter level; incomplete scan, no export.')
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
                        raise ScanIntegrityError(f'Relic {uid}: invalid filter level; incomplete scan, no export.')
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
            with ocr_profile_context(field=key):
                res = image_to_string(
                    data,
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ \\'abcedfghijklmnopqrstuvwxyz-",
                    6,
                    True,
                    preprocess_relic_name_img,
                )
            if res.endswith(" O"):
                res = res[:-2].strip()
            return res
        elif key == RELIC_LEVEL:
            with ocr_profile_context(field=key):
                return (
                    image_to_string(
                        data,
                        "0123456789S+",
                        13,
                        True,
                        preprocess_level_img,
                    )
                    .replace("S", "5")
                    .replace("+", "")
                )
        elif key == RELIC_MAINSTAT:
            with ocr_profile_context(field=key):
                return image_to_string(
                    data,
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz+",
                    7,
                    True,
                    preprocess_relic_main_stat_img,
                )
        elif key == EQUIPPED:
            with ocr_profile_context(field=key):
                return image_to_string(data, "Equiped", 7, True, preprocess_relic_name_img)
        elif key == RELIC_RARITY:
            # Get rarity by color matching
            rarity_sample = np.array(data)
            rarity_sample = rarity_sample[int(rarity_sample.shape[0] / 2)][
                int(rarity_sample.shape[1] / 2)
            ]
            return self._game_data.get_closest_rarity(rarity_sample)
        elif key == RELIC_SUBSTAT_NAMES:
            with ocr_profile_context(field=key):
                return image_to_string(
                    data,
                    " ABCDEFGHIKMPRSTacefikrt()+0123456789ov",
                    6,
                    True,
                    preprocess_sub_stat_img,
                    False,
                )
        elif key == RELIC_SUBSTAT_VALUES:
            with ocr_profile_context(field=key):
                return (
                    image_to_string(
                        data, "0123456789S.%,", 6, True, preprocess_sub_stat_value_img, False
                    )
                    .replace("S", "5")
                    .replace(",", ".")
                    .replace("..", ".")
                )
        else:
            return data

    def batch_parse(self, items: list[tuple[int, RelicDict]]) -> list[dict]:
        """Batch OCR relic text crops, then parse using the normal relic parser."""
        if not items:
            return []

        results = []
        for item_chunk in self._chunk_items(items, self.BATCH_OCR_CHUNK_SIZE):
            if self._interrupt_event.is_set():
                break
            raw_stats_by_uid = {
                uid: stats_dict.copy() for uid, stats_dict in item_chunk
            }
            self._batch_extract_stats_data([stats_dict for _, stats_dict in item_chunk])

            for uid, stats_dict in item_chunk:
                # Preserve original images so failure debug still saves useful crops.
                stats_dict["_raw_stats"] = raw_stats_by_uid[uid]  # type: ignore[typeddict-unknown-key]
                result = self.parse(stats_dict, uid)
                if result:
                    results.append(result)
                elif not self._interrupt_event.is_set():
                    raise ScanIntegrityError(f'Relic {uid}: empty parse result; incomplete scan, no export.')
        return results

    def _chunk_items(
        self, items: list[tuple[int, RelicDict]], chunk_size: int
    ) -> list[list[tuple[int, RelicDict]]]:
        """Split a worker shard so parsed relics can stream back during OCR."""
        chunk_size = max(1, chunk_size)
        return [
            items[index : index + chunk_size]
            for index in range(0, len(items), chunk_size)
        ]

    def _batch_extract_stats_data(self, stats_dicts: list[RelicDict]) -> None:
        """Run homogeneous relic OCR fields through Tesseract in bounded batches."""
        self._batch_extract_field(
            stats_dicts,
            RELIC_NAME,
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ \\'abcedfghijklmnopqrstuvwxyz-",
            6,
            True,
            preprocess_relic_name_img,
            True,
            "white",
            40,
            self._normalize_relic_name_ocr,
            True,
        )
        self._batch_extract_field(
            stats_dicts,
            RELIC_LEVEL,
            "0123456789S+",
            6,
            True,
            preprocess_level_img,
            True,
            "white",
            40,
            self._normalize_relic_level_ocr,
            True,
        )
        self._batch_extract_field(
            stats_dicts,
            RELIC_MAINSTAT,
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcedfghijklmnopqrstuvwxyz+",
            6,
            True,
            preprocess_relic_main_stat_img,
            True,
            "white",
            40,
            lambda text: text,
            True,
        )
        self._batch_extract_field(
            stats_dicts,
            EQUIPPED,
            "Equiped",
            6,
            True,
            preprocess_relic_name_img,
            True,
            "white",
            40,
            lambda text: text,
        )
        self._batch_extract_field(
            stats_dicts,
            RELIC_SUBSTAT_NAMES,
            " ABCDEFGHIKMPRSTacefikrt()+0123456789ov",
            6,
            True,
            preprocess_sub_stat_img,
            False,
            "white",
            5,
            lambda text: text,
        )
        self._batch_extract_field(
            stats_dicts,
            RELIC_SUBSTAT_VALUES,
            "0123456789S.%,",
            6,
            True,
            preprocess_sub_stat_value_img,
            False,
            "white",
            5,
            self._normalize_relic_substat_values_ocr,
        )

        for stats_dict in stats_dicts:
            if isinstance(stats_dict.get(RELIC_RARITY), Image):
                stats_dict[RELIC_RARITY] = self.extract_stats_data(
                    RELIC_RARITY, stats_dict[RELIC_RARITY]
                )

    def _batch_extract_field(
        self,
        stats_dicts: list[RelicDict],
        key: str,
        whitelist: str,
        psm: int,
        force_preprocess: bool,
        preprocess_func,
        remove_newline: bool,
        background: str | tuple[int, int, int],
        padding: int,
        normalize_func,
        fallback_empty_results: bool = False,
    ) -> None:
        indexed_images = [
            (index, stats_dict[key])
            for index, stats_dict in enumerate(stats_dicts)
            if key in stats_dict and isinstance(stats_dict[key], Image)
        ]
        if not indexed_images:
            return

        indexes = [index for index, _ in indexed_images]
        images = [img for _, img in indexed_images]
        with ocr_profile_context(
            item_type="relic", uid="batch", field=key, phase="batch_ocr"
        ):
            results, _ = batch_image_to_strings_chunked(
                images,
                whitelist,
                psm,
                force_preprocess,
                preprocess_func,
                remove_newline,
                padding,
                self.BATCH_OCR_CHUNK_SIZE,
                background,
            )

        if len(results) != len(indexed_images):
            raise ScanIntegrityError(f'OCR batch {key} returned wrong count; incomplete scan, no export.')
        if fallback_empty_results and any(not text.strip() for text in results):
            empty_count = sum(1 for text in results if not text.strip())
            self._log(
                f"Relic batch OCR field {key}: {empty_count}/{len(results)} results "
                "were empty. Falling back to individual OCR for blank results.",
                LogLevel.WARNING,
            )
            results = list(results)
            for result_index, (_, image) in enumerate(indexed_images):
                if results[result_index].strip():
                    continue
                with ocr_profile_context(
                    item_type="relic",
                    uid="batch",
                    field=key,
                    phase="batch_fallback",
                ):
                    results[result_index] = str(self.extract_stats_data(key, image))

        for index, text in zip(indexes, results):
            stats_dicts[index][key] = normalize_func(text)  # type: ignore[literal-required]

    def _normalize_relic_name_ocr(self, text: str) -> str:
        text = text.strip()
        if text.endswith(" O"):
            text = text[:-2].strip()
        return text

    def _normalize_relic_level_ocr(self, text: str) -> str:
        return text.replace("S", "5").replace("+", "").strip()

    def _normalize_relic_substat_values_ocr(self, text: str) -> str:
        return text.replace("S", "5").replace(",", ".").replace("..", ".").strip()

    def parse(self, stats_dict: RelicDict, uid: int) -> dict:
        """Re-read invalid fields from the cached crops, each field group at most once.

        A corrected name can expose a substat error that the first parse never reached.
        """
        saved = dict(stats_dict)
        raw = saved.get('_raw_stats')
        reread = {}
        try:
            return self._parse_once(stats_dict, uid)
        except ScanIntegrityError as exc:
            error = exc
        while True:
            message = str(error).lower()
            fields = ([RELIC_NAME] if 'relic name' in message else
                      [RELIC_MAINSTAT] if 'main stat' in message else
                      [RELIC_SUBSTAT_NAMES, RELIC_SUBSTAT_VALUES] if 'substat' in message else [])
            if (not raw or not fields or any(k in reread for k in fields)
                    or not all(isinstance(raw.get(k), Image) for k in fields)):
                raise error
            self._log(f'Relic {uid}: invalid batch OCR; retrying {fields} once from cached crops.', LogLevel.WARNING)
            for field in fields:
                reread[field] = self.extract_stats_data(field, raw[field])
            retry = dict(saved)
            retry.update(reread)
            retry['_raw_stats'] = raw
            try:
                return self._parse_once(retry, uid)
            except ScanIntegrityError as exc:
                error = exc

    def _parse_once(self, stats_dict: RelicDict, uid: int) -> dict:
        """Parses the relic data

        :param stats_dict: The stats dict
        :param uid: The relic UID
        :return: The parsed relic data
        """
        if self._interrupt_event.is_set():
            return {}

        try:
            # Keep a copy of raw images for debug saving before they are OCRed into strings
            raw_stats = stats_dict.pop("_raw_stats", None) or stats_dict.copy()  # type: ignore[typeddict-item]
            with ocr_profile_context(item_type="relic", uid=uid, phase="parse"):
                for key in stats_dict:
                    with ocr_profile_context(field=key):
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

            name = validated_match(name, self._game_data.RELIC_META_DATA, 'relic name')
            main_stat_key = validated_match(main_stat_key, RELIC_MAIN_STATS, 'main stat')

            parsed_level = self._parse_level_int(level)
            if parsed_level is None:
                self._log(
                    f"Relic UID {uid}: Failed to extract level. Raw OCR was: {repr(level)}",
                    LogLevel.ERROR,
                )
                if isinstance(raw_stats.get(RELIC_LEVEL), Image):
                    self._save_debug_image(
                        raw_stats[RELIC_LEVEL], uid, "level_parse_failed"
                    )
                raise ScanIntegrityError(f'Relic {uid}: unreadable level; cannot validate rolls. Incomplete scan, no export.')
            else:
                level = parsed_level

            # Substats
            while "\n\n" in substat_names:  # type: ignore
                substat_names = substat_names.replace("\n\n", "\n")  # type: ignore
            while "\n\n" in substat_vals:  # type: ignore
                substat_vals = substat_vals.replace("\n\n", "\n")  # type: ignore
            substat_names = substat_names.split("\n")  # type: ignore
            substat_vals = substat_vals.split("\n")  # type: ignore

            try:
                substats_res, unactivated_substats_res = self._parse_substats(
                    substat_names, substat_vals, uid, raw_stats
                )
                if (len(substats_res) + len(unactivated_substats_res)
                        != len([n for n in substat_names if n.strip()])
                        or len([n for n in substat_names if n.strip()])
                        != len([v for v in substat_vals if v.strip()])):
                    raise ScanIntegrityError(f'Relic {uid}: unparsed/misaligned substats; incomplete scan, no export.')
                validate_substat_rolls(substats_res, unactivated_substats_res, rarity, level, uid)
            except ScanIntegrityError:
                for field in (RELIC_SUBSTAT_NAMES, RELIC_SUBSTAT_VALUES):
                    if isinstance(raw_stats.get(field), Image):
                        try:
                            self._save_debug_image(raw_stats[field], uid, 'invalid_roll_' + field)
                        except Exception as exc:
                            self._log(f'Relic {uid}: could not save invalid-roll evidence: {exc}', LogLevel.ERROR)
                raise

            # Set and slot
            metadata = self._game_data.get_relic_meta_data(name)
            set_id = str(metadata[RELIC_SET_ID])
            set_name = metadata[RELIC_SET]
            slot_key = metadata[RELIC_SLOT]
            validate_main_stat_slot(main_stat_key, slot_key)

            # Check if locked/discarded by image matching
            lock = self._parse_icon_flag(uid, "lock", lock, self._lock_icon)
            discard = self._parse_icon_flag(uid, "discard", discard, self._discard_icon)

            location = ""
            outfit_id = None
            footer = raw_stats.get('_equipped_frame')
            if not isinstance(footer, Image):
                raise ScanIntegrityError(f'Relic {uid}: missing equipped-footer evidence; incomplete scan, no export.')
            # The footer frame decides whether the relic is equipped and the portrait
            # decides by whom. The label text only serves as a cross-check.
            if equipped_frame_present(footer):
                location, outfit_id = self._game_data.get_verified_equipped_character(
                    stats_dict[EQUIPPED_AVATAR], stats_dict[EQUIPPED_AVATAR_OFFSET]
                )
            elif normalize_text(equipped) in ('equipped', 'equippe'):
                raise ScanIntegrityError(f'Relic {uid}: equipped label/frame disagree; incomplete scan, no export.')

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
                RELIC_PREVIEW_SUBSTATS: unactivated_substats_res,
                RELIC_LOCATION: location,
                LOCK: lock,
                RELIC_DISCARD: discard,
                "_uid": f"relic_{uid}",
            }

            self._update_signal.emit(IncrementType.RELIC_SUCCESS.value)

            return result
        except ScanIntegrityError:
            for field, image in locals().get('raw_stats', {}).items():
                if isinstance(image, Image):
                    try:
                        self._save_debug_image(image, uid, 'recognition_' + str(field))
                    except Exception:
                        pass  # Don't mask the original error.
            raise
        except Exception as e:
            self._log(
                f"Failed to parse relic {uid}. stats_dict={stats_dict}, exception={e}",
                LogLevel.ERROR,
            )
            raise ScanIntegrityError(f'Relic {uid}: parser failure; incomplete scan, no export.') from e

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

            name = validated_match(name, RELIC_SUB_STATS, 'substat name')

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
                missing_percent_on_percentage_name = (
                    name_is_percentage and re.fullmatch(r"\d\.\d", val) is not None
                )

                is_percentage = (
                    "%" in val
                    or missing_percent_on_flat
                    or missing_percent_on_percentage_name
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
                    if not re.fullmatch(r"\d+(?:\.0+)?", val):
                        raise ScanIntegrityError(
                            f'Relic {uid}: invalid integer substat {name}={val!r}; '
                            'incomplete scan, no export.'
                        )
                    val = int(float(val))

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

    def _log(self, msg: str, level: LogLevel = LogLevel.INFO) -> None:
        """Logs a message

        :param msg: The message to log
        :param level: The log level
        """
        if self._debug or level in [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
            self._log_signal.emit((msg, level))
