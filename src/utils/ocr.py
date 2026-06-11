import os
import sys
import threading
import time

import cv2
import numpy as np
from utils import patched_pytesseract as pytesseract
from PIL import Image as PILImage
from PIL.Image import Image

from models.const import DEFAULT_OCR_CONCURRENCY
from utils.data import resource_path
from utils.ocr_profile import (
    is_ocr_profile_enabled,
    record_ocr_attempt,
    record_ocr_call,
)
from utils.ocr_threads import clamp_thread_count

# set environment variables for Tesseract
os.environ["TESSDATA_PREFIX"] = resource_path("assets/tesseract/tessdata")
if sys.platform == "win32":
    pytesseract.tesseract_cmd = resource_path("assets/tesseract/tesseract.exe")
else:
    pytesseract.tesseract_cmd = "tesseract"
DIN_ALTERNATE = "DIN-Alternate"

# Limit concurrent Tesseract processes to prevent system overload
OCR_SEMAPHORE = threading.Semaphore(DEFAULT_OCR_CONCURRENCY)
OCR_CALL_COUNTER = 0
OCR_CALL_COUNTER_LOCK = threading.Lock()

# Languages whose traineddata failed to load, so fallback attempts that can
# never succeed are not retried with a fresh Tesseract process on every call.
_MISSING_LANGS: set[str] = set()
_MISSING_LANGS_LOCK = threading.Lock()
_MISSING_LANG_ERROR_MARKERS = (
    "Failed loading language",
    "Error opening data file",
    "Could not initialize tesseract",
)


def _is_lang_marked_missing(lang: str) -> bool:
    with _MISSING_LANGS_LOCK:
        return lang in _MISSING_LANGS


def _mark_lang_missing_if_unloadable(lang: str, exc: Exception) -> None:
    if any(marker in str(exc) for marker in _MISSING_LANG_ERROR_MARKERS):
        with _MISSING_LANGS_LOCK:
            _MISSING_LANGS.add(lang)


def set_ocr_concurrency(limit: int | None) -> int:
    """Set the maximum number of concurrent OCR calls."""
    global OCR_SEMAPHORE
    resolved_limit = DEFAULT_OCR_CONCURRENCY if limit is None else limit
    parsed_limit = clamp_thread_count(resolved_limit)
    OCR_SEMAPHORE = threading.Semaphore(parsed_limit)

    return parsed_limit


def preprocess_img(img: Image) -> Image:
    """Generic image preprocessing function

    :param img: The image to preprocess
    :return: The preprocessed image
    """

    return _preprocess_img_by_colour_filter(img, (255, 255, 255), 80)


def image_to_string(
    img: Image,
    whitelist: str,
    psm: int,
    force_preprocess=False,
    preprocess_func=preprocess_img,
    remove_newline=True,
    lang=None,
) -> str:
    """Convert image to string

    :param img: The image to convert
    :param whitelist: The whitelist of characters to use
    :param psm: The page segmentation mode to use
    :param force_preprocess: The flag to force preprocessing, defaults to False
    :param preprocess_func: The preprocessing function to use, defaults to None
    :return: The string representation of the image
    """
    if lang is None:
        lang = DIN_ALTERNATE
    requested_lang = lang
    profile_enabled = is_ocr_profile_enabled()
    call_id = _next_ocr_call_id() if profile_enabled else 0
    total_start = time.perf_counter() if profile_enabled else 0.0

    tessdata_dir = resource_path("assets/tesseract/tessdata")

    # Check which requested languages are bundled locally.
    available_langs = []
    for l in lang.split("+"):
        if os.path.exists(os.path.join(tessdata_dir, f"{l}.traineddata")):
            available_langs.append(l)

    # Local OCR attempt uses bundled tessdata first.
    final_lang = "+".join(available_langs) if available_langs else DIN_ALTERNATE
    local_config = f'--tessdata-dir "{tessdata_dir}" -c tessedit_char_whitelist="{whitelist}" --psm {psm}'
    system_config = f'-c tessedit_char_whitelist="{whitelist}" --psm {psm}'

    # If local tessdata is missing requested languages (e.g. eng), try system tessdata as fallback.
    # Skip languages that already failed to load this run; respawning Tesseract for them
    # costs ~160ms per attempt and can never succeed.
    attempts: list[tuple[str, str]] = [(local_config, final_lang)]
    if lang != final_lang and not _is_lang_marked_missing(lang):
        attempts.append((system_config, lang))
    if "eng" in lang.split("+") and not _is_lang_marked_missing("eng"):
        attempts.append((system_config, "eng"))

    # Keep original order while removing duplicates.
    dedup_attempts = []
    seen_attempts = set()
    for config, config_lang in attempts:
        key = (config, config_lang)
        if key not in seen_attempts:
            seen_attempts.add(key)
            dedup_attempts.append((config, config_lang))

    def _ocr_with_fallback(target_img: Image, target: str) -> str:
        last_res = ""
        for attempt_index, (config, config_lang) in enumerate(dedup_attempts, start=1):
            # Fallback languages may get marked missing mid-call (e.g. by the
            # direct pass); never skip the primary bundled attempt.
            if attempt_index > 1 and _is_lang_marked_missing(config_lang):
                continue
            attempt_start = time.perf_counter() if profile_enabled else 0.0
            try:
                last_res = pytesseract.image_to_string(
                    target_img, config=config, lang=config_lang
                )
            except Exception as exc:
                _mark_lang_missing_if_unloadable(config_lang, exc)
                if profile_enabled:
                    record_ocr_attempt(
                        call_id,
                        attempt_index,
                        config_lang,
                        config,
                        target,
                        (time.perf_counter() - attempt_start) * 1000,
                        "",
                        exc,
                    )
                # Continue to the next OCR source if this language/config is unavailable.
                continue

            if profile_enabled:
                record_ocr_attempt(
                    call_id,
                    attempt_index,
                    config_lang,
                    config,
                    target,
                    (time.perf_counter() - attempt_start) * 1000,
                    last_res,
                )

            if last_res.strip():
                return last_res

        return last_res

    res = ""
    direct_ms = 0.0
    preprocess_ms = 0.0
    preprocessed_ocr_ms = 0.0
    used_preprocess = force_preprocess
    with OCR_SEMAPHORE:
        if not force_preprocess:
            direct_start = time.perf_counter() if profile_enabled else 0.0
            res = _ocr_with_fallback(img, "direct")
            if profile_enabled:
                direct_ms = (time.perf_counter() - direct_start) * 1000

        if not res.strip():
            used_preprocess = True
            preprocess_start = time.perf_counter() if profile_enabled else 0.0
            preprocessed_img = preprocess_func(img)
            if profile_enabled:
                preprocess_ms = (time.perf_counter() - preprocess_start) * 1000
            preprocessed_start = time.perf_counter() if profile_enabled else 0.0
            res = _ocr_with_fallback(preprocessed_img, "preprocessed")
            if profile_enabled:
                preprocessed_ocr_ms = (time.perf_counter() - preprocessed_start) * 1000

    if remove_newline:
        res = res.replace("\n", " ")

    res = res.strip()
    if profile_enabled:
        record_ocr_call(
            call_id=call_id,
            image_size=img.size,
            whitelist=whitelist,
            psm=psm,
            force_preprocess=force_preprocess,
            remove_newline=remove_newline,
            lang=requested_lang,
            final_lang=final_lang,
            attempts_count=len(dedup_attempts),
            direct_ms=direct_ms,
            preprocess_ms=preprocess_ms,
            preprocessed_ocr_ms=preprocessed_ocr_ms,
            total_ms=(time.perf_counter() - total_start) * 1000,
            used_preprocess=used_preprocess,
            result=res,
        )

    return res


def preprocess_char_count_img(img: Image) -> Image:
    """Preprocess character count image in the Data Bank screen

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, [(218, 194, 145), (142, 135, 115)], 80)


def preprocess_lc_level_img(img: Image) -> Image:
    """Preprocess light cone level image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, [(255, 255, 255), (239, 160, 61)], 80)


def preprocess_trace_img(img: Image) -> Image:
    """Preprocess trace image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    img = _preprocess_img_by_colour_filter(
        img,
        [
            (255, 255, 255),
            (212, 214, 214),
            (160, 166, 175),
            (45, 240, 240),
            (26, 145, 150),
            (33, 180, 182),
            (38, 212, 206),
            (14, 77, 82),
            (0, 255, 255),
            (0, 160, 180),
        ],
        [50, 50, 20, 20, 30, 30, 15, 10, 50, 20],
    )
    return img


def preprocess_equipped_img(img: Image) -> Image:
    """Preprocess equipped image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, (202, 177, 134), 75)


def preprocess_level_img(img: Image) -> Image:
    """Preprocess level image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, (255, 255, 255), 100)


def preprocess_main_stat_img(img: Image) -> Image:
    """Preprocess main stat image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    return _preprocess_img_by_colour_filter(img, (226, 155, 61), 50)


def preprocess_sub_stat_img(img: Image) -> Image:
    """Preprocess sub stat image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    # Even wider range for grayed-out inactive substats
    img = _preprocess_img_by_colour_filter(
        img,
        [(255, 255, 255), (140, 140, 140)],
        [120, 80],
    )
    return img


def preprocess_superimposition_img(img: Image) -> Image:
    """Preprocess superimposition image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    img = _preprocess_img_by_colour_filter(img, (220, 196, 145), 70)
    return img


def preprocess_uid_img(img: Image) -> Image:
    """Preprocess UID image

    :param img: The image to preprocess
    :return: The preprocessed image
    """
    img = _preprocess_img_by_colour_filter(img, (180, 180, 180), 80)
    return img


def _preprocess_img_by_colour_filter(
    img: Image, colour: tuple | list[tuple], variance: int | list[int]
) -> Image:
    """Preprocess image by filtering out colours that are not within the variance of the colour

    :param img: The image to preprocess
    :param colour: The colour or list of colours to filter
    :param variance: The variance or list of variances to use for each colour
    :return: The preprocessed image
    """
    if isinstance(colour, tuple):
        colour = [colour]
    if isinstance(variance, int):
        variance = [variance] * len(colour)

    if len(colour) != len(variance):
        raise ValueError(
            f"Length of colour ({len(colour)}) and variance ({len(variance)}) must be the same"
        )

    img_arr = np.array(img)

    mask = np.zeros(img_arr.shape[:2], dtype="uint8")
    for c, v in zip(colour, variance):
        lower = np.array([max(0, c - v) for c in c], dtype="uint8")
        upper = np.array([min(255, c + v) for c in c], dtype="uint8")
        mask = cv2.bitwise_or(mask, cv2.inRange(img_arr, lower, upper))  # type: ignore

    img_arr = cv2.bitwise_and(img_arr, img_arr, mask=mask)  # type: ignore
    img_arr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)  # type: ignore

    # UPSCALE for better OCR
    height, width = img_arr.shape[:2]
    img_arr = cv2.resize(img_arr, (width * 3, height * 3), interpolation=cv2.INTER_CUBIC)

    # blur
    img_arr = cv2.GaussianBlur(img_arr, (3, 3), 1)  # type: ignore

    # better thresholding
    _, img_arr = cv2.threshold(img_arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # invert
    img_arr = 255 - img_arr

    return PILImage.fromarray(img_arr)


def _next_ocr_call_id() -> int:
    global OCR_CALL_COUNTER
    with OCR_CALL_COUNTER_LOCK:
        OCR_CALL_COUNTER += 1
        return OCR_CALL_COUNTER
