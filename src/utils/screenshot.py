import datetime
import os
import time

import cv2
import numpy as np
import win32gui
try:
    import mss
except ImportError:  # pragma: no cover - exercised by PIL fallback environments
    mss = None
from PIL import Image as PILImage
from PIL import ImageChops, ImageGrab
from PIL.Image import Image
from PyQt6.QtCore import pyqtBoundSignal

from config.const import (
    ASPECT_16_9,
    CHARACTER,
    CHAR_EIDOLONS,
    CHEST,
    COUNT,
    QUANTITY,
    SORT,
    STATS,
    TRACES,
    UID,
)
from config.screenshot import SCREENSHOT_COORDS
from enums.log_level import LogLevel
from enums.increment_type import IncrementType
from models.const import CHAR_LEVEL, CHAR_NAME


class Screenshot:
    """Screenshot class for taking screenshots of the game window"""

    def __init__(
        self,
        hwnd: int,
        log_signal: pyqtBoundSignal,
        aspect_ratio: str = ASPECT_16_9,
        debug: bool = False,
        save_capture_png: bool = True,
        debug_output_location: str = "",
        verbose_logs: bool = True,
    ) -> None:
        """Constructor

        :param hwnd: The window handle of the game window
        :param aspect_ratio: The aspect ratio of the game window, defaults to "16:9"
        :param debug_mode: Whether to log screenshot timing, default False
        :param save_capture_png: Whether to save every capture as a PNG
        :param debug_output_location: Output location of saved screenshots
        :param verbose_logs: Whether to emit a timing log line per capture;
            timing is always aggregated in memory for the end-of-scan summary
        """
        self._aspect_ratio = aspect_ratio
        self._log_signal = log_signal

        self._window_width, self._window_height = win32gui.GetClientRect(hwnd)[2:]
        self._window_x, self._window_y = win32gui.ClientToScreen(hwnd, (0, 0))

        self._x_scaling_factor = self._window_width / 1920
        self._y_scaling_factor = self._window_height / 1080

        self._debug = debug
        self._save_capture_png = save_capture_png
        self._debug_output_location = debug_output_location
        self._verbose_logs = verbose_logs
        self._stats_capture_records: list[dict] = []
        # Diagnostics: polls where raw pixels changed but the text signature
        # didn't — non-text changes (icons loading, overlays) worth flagging.
        self._nontext_change_events: list[tuple[int, tuple]] = []
        self._last_panel_raw: Image | None = None
        self._mss = None
        self._mss_failed = False
        self._mss_fallback_logged = False

    def screenshot_screen(self) -> Image:
        """Takes a screenshot of the entire screen

        :return: The screenshot
        """
        do_not_save = True  # so users don't unintentionally reveal their UID when naively sharing debug folder
        return self._take_screenshot(0, 0, 1, 1, do_not_save)

    def screenshot_stats(self, scan_type: IncrementType) -> dict:
        """Takes a screenshot of the stats. Requires an item to be selected in the inventory.

        :param scan_type: The scan type
        :raises ValueError: Thrown if the scan type is invalid
        :return: A dict of the stats with the key being the stat name and the value being the screenshot
        """
        stats, _ = self.screenshot_stats_with_panel_bytes(scan_type)
        return stats

    def screenshot_stats_with_panel_bytes(
        self, scan_type: IncrementType
    ) -> tuple[dict, bytes]:
        """Takes a stats screenshot and returns its panel bytes for duplicate detection.

        :param scan_type: The scan type
        :raises ValueError: Thrown if the scan type is invalid
        :return: The cropped stats dict and the panel's text-band signature bytes
        """
        return self.screenshot_stats_on_panel_change(scan_type, None, 0.0)

    def screenshot_stats_on_panel_change(
        self,
        scan_type: IncrementType,
        previous_panel_bytes: bytes | None,
        timeout_s: float,
    ) -> tuple[dict, bytes]:
        """Takes a stats screenshot once the panel changes from the previous item.

        Polls until the panel's text-band signature differs from
        ``previous_panel_bytes``, then captures the accepted frame; falls through
        after ``timeout_s`` so identical adjacent items don't stall the scan.

        :param scan_type: The scan type
        :param previous_panel_bytes: Previous item's text-band signature bytes, or None
        :param timeout_s: Max time to wait for the panel to change
        :raises ValueError: Thrown if the scan type is invalid
        :return: The cropped stats dict and the panel's text-band signature bytes
        """
        match IncrementType(scan_type):
            case IncrementType.LIGHT_CONE_ADD:
                key = "light_cone"
            case IncrementType.RELIC_ADD:
                key = "relic"
            case _:
                raise ValueError(f"Invalid scan type: {scan_type.name}.")
        return self._screenshot_stats(key, previous_panel_bytes, timeout_s)

    def screenshot_sort(self) -> Image:
        """Takes a screenshot of the current sort option. Requires inventory to be open.

        :return: The screenshot
        """
        coords = SCREENSHOT_COORDS[self._aspect_ratio][SORT]
        return self._take_screenshot(*coords)

    def screenshot_quantity(self) -> Image:
        """Takes a screenshot of the quantity. Requires inventory to be open.

        :return: The screenshot
        """
        return self._take_screenshot(*SCREENSHOT_COORDS[self._aspect_ratio][QUANTITY])

    def screenshot_character_count(self) -> Image:
        """Takes a screenshot of the character count. Requires

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][COUNT]
        )

    def screenshot_character_name(self) -> Image:
        """Takes a screenshot of the character name

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][CHAR_NAME]
        )

    def screenshot_character_level(self) -> Image:
        """Takes a screenshot of the character level

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][CHAR_LEVEL]
        )

    def screenshot_character(self) -> Image:
        """Takes a screenshot of the character

        :return: The screenshot
        """
        return self._take_screenshot(
            *SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][CHEST]
        )

    def screenshot_character_eidolons(self) -> list[np.ndarray]:
        """Takes a screenshot of the character eidolons

        :return: A list of the screenshots
        """
        res = []

        screenshot = ImageGrab.grab(all_screens=True)
        offset, _, _ = PILImage.core.grabscreen_win32(False, True)  # type: ignore
        x0, y0 = offset
        dim = 81

        # Circle mask
        mask = np.zeros((dim, dim), dtype="uint8")
        cv2.circle(mask, (int(dim / 2), int(dim / 2)), int(dim / 2), 255, -1)  # type: ignore

        for c in SCREENSHOT_COORDS[self._aspect_ratio][CHARACTER][CHAR_EIDOLONS]:
            left = self._window_x + int(self._window_width * c[0])
            upper = self._window_y + int(self._window_height * c[1])
            right = left + self._window_width * 0.042
            lower = upper + self._window_height * 0.075
            img = screenshot.crop((left - x0, upper - y0, right - x0, lower - y0))

            # Apply circle mask
            img = np.array(img)
            img = cv2.resize(img, (dim, dim))  # type: ignore
            img = cv2.bitwise_and(img, img, mask=mask)  # type: ignore

            res.append(img)

        if self._debug and self._save_capture_png:
            for img in res:
                self._save_image(PILImage.fromarray(img))

        return res

    def screenshot_character_traces(self, key: str) -> dict:
        """Takes a screenshot of the character trace levels

        :param key: The key of the traces to screenshot
        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        return self._screenshot_traces(key)

    def screenshot_uid(self) -> Image:
        """Takes a screenshot of the UID. Requires ESC menu to be open.

        :return: The screenshot
        """
        return self._take_screenshot(*SCREENSHOT_COORDS[self._aspect_ratio][UID])

    def _take_screenshot(
        self, x: float, y: float, width: float, height: float, do_not_save: bool = False
    ) -> Image:
        """Takes a screenshot of the game window

        :param x: The x percent coordinate of the top left corner of the screenshot
        :param y: The y percent coordinate of the top left corner of the screenshot
        :param width: The width of the screenshot
        :param height: The height of the screenshot
        :return: The screenshot normalized to 1920x1080
        """
        timing_start = time.perf_counter()

        # adjust coordinates to window
        x = self._window_x + int(self._window_width * x)
        y = self._window_y + int(self._window_height * y)
        width = int(self._window_width * width)
        height = int(self._window_height * height)
        bbox = (int(x), int(y), int(x + width), int(y + height))

        grab_start = time.perf_counter()
        screenshot, backend = self._grab_screenshot(bbox)
        grab_end = time.perf_counter()

        resize_start = time.perf_counter()
        screenshot = screenshot.resize(
            (int(width / self._x_scaling_factor), int(height / self._y_scaling_factor))
        )
        resize_end = time.perf_counter()

        file_name = "not_saved"
        save_ms = 0.0
        if self._debug and self._save_capture_png and not do_not_save:
            file_name, save_ms = self._save_image(screenshot)

        if self._debug and self._verbose_logs:
            self._log_screenshot_timing(
                file_name=file_name,
                backend=backend,
                bbox=bbox,
                source_size=(width, height),
                normalized_size=screenshot.size,
                grab_ms=(grab_end - grab_start) * 1000,
                resize_ms=(resize_end - resize_start) * 1000,
                save_ms=save_ms,
                total_ms=(time.perf_counter() - timing_start) * 1000,
            )

        return screenshot

    def _grab_screenshot(self, bbox: tuple[int, int, int, int]) -> tuple[Image, str]:
        """Capture a cropped screenshot, preferring mss and falling back to PIL."""
        if mss is not None and not self._mss_failed:
            try:
                return self._grab_with_mss(bbox), "mss"
            except Exception as exc:  # pragma: no cover - depends on host capture stack
                self._mss_failed = True
                if not self._mss_fallback_logged:
                    self._mss_fallback_logged = True
                    self._log_signal.emit(
                        (
                            "mss capture failed; falling back to PIL ImageGrab. "
                            f"Error: {exc}",
                            LogLevel.WARNING,
                        )
                    )

        return ImageGrab.grab(bbox=bbox, all_screens=True), "pil"

    def _grab_with_mss(self, bbox: tuple[int, int, int, int]) -> Image:
        """Capture a cropped screenshot using mss."""
        left, top, right, bottom = bbox
        monitor = {
            "left": left,
            "top": top,
            "width": right - left,
            "height": bottom - top,
        }

        if self._mss is None:
            self._mss = mss.MSS()

        raw = self._mss.grab(monitor)
        return PILImage.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    def _screenshot_stats(
        self,
        key: str,
        previous_panel_bytes: bytes | None = None,
        timeout_s: float = 0.0,
    ) -> tuple[dict, bytes]:
        """Takes a screenshot of the stats

        :param key: The key of the stats to screenshot
        :param previous_panel_bytes: Previous item's text-band signature bytes, or None
        :param timeout_s: Max time to poll for the panel to change
        :return: The cropped stats dict and the panel's text-band signature bytes
        """
        coords = SCREENSHOT_COORDS[self._aspect_ratio]
        timing_start = time.perf_counter()

        x_pct, y_pct, w_pct, h_pct = coords[STATS]
        x = self._window_x + int(self._window_width * x_pct)
        y = self._window_y + int(self._window_height * y_pct)
        width = int(self._window_width * w_pct)
        height = int(self._window_height * h_pct)
        bbox = (int(x), int(y), int(x + width), int(y + height))

        # Grab raw until the text-band signature differs from the previous item
        # (the new panel has rendered); the ~10ms mss grab paces the loop.
        polls = 0
        poll_start = time.perf_counter()
        while True:
            polls += 1
            grab_start = time.perf_counter()
            raw_img, backend = self._grab_screenshot(bbox)
            grab_end = time.perf_counter()
            panel_bytes = self._panel_change_signature(raw_img, key)
            changed = (
                previous_panel_bytes is None or panel_bytes != previous_panel_bytes
            )
            if not changed and self._debug:
                self._record_nontext_change(raw_img)
            if changed or (time.perf_counter() - poll_start) >= timeout_s:
                break
        panel_wait_ms = (time.perf_counter() - poll_start) * 1000

        resize_start = time.perf_counter()
        img = raw_img.resize(
            (int(width / self._x_scaling_factor), int(height / self._y_scaling_factor))
        )
        resize_end = time.perf_counter()

        file_name = "not_saved"
        save_ms = 0.0
        if self._debug and self._save_capture_png:
            file_name, save_ms = self._save_image(img)

        adjusted_stat_coords = {
            k: (
                int(v[0] * img.width),
                int(v[1] * img.height),
                int(v[2] * img.width),
                int(v[3] * img.height),
            )
            for k, v in coords[key].items()
        }

        res = {k: img.crop(v) for k, v in adjusted_stat_coords.items()}

        if self._debug:
            # Diff bbox of the accepted frame: a real item swap repaints most
            # of the panel, so a tiny changed area flags a suspect accept.
            accept_bbox = None
            accept_area = None
            if (
                changed
                and previous_panel_bytes is not None
                and self._last_panel_raw is not None
                and self._last_panel_raw.size == raw_img.size
            ):
                diff_bbox = ImageChops.difference(
                    raw_img, self._last_panel_raw
                ).getbbox()
                if diff_bbox is not None:
                    rw, rh = raw_img.size
                    accept_bbox = tuple(
                        round(v / d, 3) for v, d in zip(diff_bbox, (rw, rh, rw, rh))
                    )
                    accept_area = round(
                        (diff_bbox[2] - diff_bbox[0])
                        * (diff_bbox[3] - diff_bbox[1])
                        / (rw * rh),
                        4,
                    )
            self._last_panel_raw = raw_img
            grab_ms = (grab_end - grab_start) * 1000
            resize_ms = (resize_end - resize_start) * 1000
            total_ms = (time.perf_counter() - timing_start) * 1000
            self._stats_capture_records.append(
                {
                    "polls": polls,
                    "panel_wait_ms": panel_wait_ms,
                    "changed": changed,
                    "grab_ms": grab_ms,
                    "resize_ms": resize_ms,
                    "save_ms": save_ms,
                    "total_ms": total_ms,
                    "accept_bbox": accept_bbox,
                    "accept_area": accept_area,
                }
            )
            if self._verbose_logs:
                self._log_signal.emit(
                    (
                        "Stats capture timing: "
                        f"file={file_name}, "
                        f"backend={backend}, "
                        f"polls={polls}, "
                        f"panel_wait_ms={panel_wait_ms:.3f}, "
                        f"changed={changed}, "
                        f"grab_ms={grab_ms:.3f}, "
                        f"resize_ms={resize_ms:.3f}, "
                        f"save_ms={save_ms:.3f}, "
                        f"total_ms={total_ms:.3f}",
                        LogLevel.DEBUG,
                    )
                )

        return res, panel_bytes

    def _screenshot_traces(self, key: str) -> dict:
        """Takes a screenshot of the trace levels

        :param key: The key of the traces to screenshot
        :return: A dict of the traces with the key being the trace name and the value being the screenshot
        """
        coords = SCREENSHOT_COORDS[self._aspect_ratio]

        res = {}

        screenshot = ImageGrab.grab(all_screens=True)
        offset, _, _ = PILImage.core.grabscreen_win32(False, True)  # type: ignore
        x0, y0 = offset

        for k, v in coords[CHARACTER][TRACES][key].items():
            left = self._window_x + int(self._window_width * v[0])
            upper = self._window_y + int(self._window_height * v[1])
            right = left + int(self._window_width * 0.04)
            lower = upper + int(self._window_height * 0.028)

            res[k] = screenshot.crop((left - x0, upper - y0, right - x0, lower - y0))

        if self._debug and self._save_capture_png:
            for img in res.values():
                self._save_image(img)

        return res

    def _log_screenshot_timing(
        self,
        file_name: str,
        backend: str,
        bbox: tuple[int, int, int, int],
        source_size: tuple[int, int],
        normalized_size: tuple[int, int],
        grab_ms: float,
        resize_ms: float,
        save_ms: float,
        total_ms: float,
    ) -> None:
        """Log screenshot timing details for real scan performance analysis."""
        self._log_signal.emit(
            (
                "Screenshot timing: "
                f"file={file_name}, "
                f"backend={backend}, "
                f"bbox={bbox}, "
                f"source={source_size[0]}x{source_size[1]}, "
                f"normalized={normalized_size[0]}x{normalized_size[1]}, "
                f"grab_ms={grab_ms:.3f}, "
                f"resize_ms={resize_ms:.3f}, "
                f"save_ms={save_ms:.3f}, "
                f"total_ms={total_ms:.3f}",
                LogLevel.DEBUG,
            )
        )

    # Text-only regions as (x0, y0, x1, y1) fractions. The poll compares only
    # these, so non-text pixels (scrollbar, icons, art) can't fake a change.
    _PANEL_SIGNATURE_BANDS = {
        "relic": (
            (0.06, 0, 1, 0.09),         # name
            (0.06, 0.09, 0.30, 0.15),   # slot text
            (0.06, 0.22, 0.30, 0.34),   # level
            (0.115, 0.34, 0.96, 0.90),  # mainstat/substat/set text
        ),
        "light_cone": ((0.06, 0, 1, 0.09), (0.115, 0.31, 0.96, 0.90)),
    }

    @classmethod
    def _panel_change_signature(cls, img: Image, key: str) -> bytes:
        """Bytes of the text-content regions of a raw stats panel."""
        w, h = img.size
        return b"".join(
            img.crop(
                (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
            ).tobytes()
            for x0, y0, x1, y1 in cls._PANEL_SIGNATURE_BANDS[key]
        )

    _NONTEXT_CHANGE_EVENT_CAP = 500

    def _record_nontext_change(self, raw_img: Image) -> None:
        """Record a poll where raw pixels changed but the text signature didn't.

        The diff bbox identifies what changed outside the text bands.
        """
        last = self._last_panel_raw
        if (
            last is None
            or last.size != raw_img.size
            or len(self._nontext_change_events) >= self._NONTEXT_CHANGE_EVENT_CAP
        ):
            return
        if raw_img.tobytes() == last.tobytes():
            return
        bbox = ImageChops.difference(raw_img, last).getbbox()
        if bbox is None:
            return
        w, h = raw_img.size
        bbox_frac = tuple(
            round(v / d, 3) for v, d in zip(bbox, (w, h, w, h))
        )
        self._nontext_change_events.append(
            (len(self._stats_capture_records), bbox_frac)
        )

    def get_capture_timing_summary_lines(self) -> list[str]:
        """Summarize stats-capture timing; available in debug mode even when
        verbose per-capture logging is off."""
        records = self._stats_capture_records
        if not records:
            return []

        lines = [f"Stats capture summary: count={len(records)}"]
        for metric in ("panel_wait_ms", "grab_ms", "resize_ms", "save_ms", "total_ms"):
            values = sorted(r[metric] for r in records)
            mid = len(values) // 2
            median = (
                values[mid]
                if len(values) % 2
                else (values[mid - 1] + values[mid]) / 2
            )
            p95 = values[min(len(values) - 1, int(len(values) * 0.95))]
            lines.append(
                f"Stats capture {metric}: "
                f"avg={sum(values) / len(values):.3f}, median={median:.3f}, "
                f"p95={p95:.3f}, max={values[-1]:.3f}"
            )

        buckets = [15, 25, 35, 45, 55, 70]
        counts = [0] * (len(buckets) + 1)
        for r in records:
            for i, upper in enumerate(buckets):
                if r["panel_wait_ms"] < upper:
                    counts[i] += 1
                    break
            else:
                counts[-1] += 1
        labels = ["<15"] + [
            f"{low}-{high}" for low, high in zip(buckets, buckets[1:])
        ] + [">=70"]
        lines.append(
            "Stats capture panel_wait_ms histogram: "
            + ", ".join(f"{label}={count}" for label, count in zip(labels, counts))
        )

        polls = [r["polls"] for r in records]
        timeouts = sum(1 for r in records if not r["changed"])
        lines.append(
            "Stats capture polls: "
            f"avg={sum(polls) / len(polls):.2f}, max={max(polls)}, "
            f"timeouts={timeouts}"
        )

        suspicious = [
            (i, r["accept_area"], r["accept_bbox"])
            for i, r in enumerate(records)
            if r.get("accept_area") is not None and r["accept_area"] < 0.02
        ]
        lines.append(
            f"Suspicious small-area accepts (<2% of panel): count={len(suspicious)}"
        )
        for i, area, bbox in suspicious[:15]:
            lines.append(
                f"Suspicious accept: capture={i}, area={area}, bbox={bbox}"
            )

        events = self._nontext_change_events
        if events:
            affected = sorted({idx for idx, _ in events})
            union = (
                min(b[0] for _, b in events),
                min(b[1] for _, b in events),
                max(b[2] for _, b in events),
                max(b[3] for _, b in events),
            )
            lines.append(
                "Non-text panel changes (raw pixels changed, text signature "
                f"didn't): events={len(events)}, captures_affected={len(affected)}, "
                f"union_bbox={union}"
            )
            for idx, bbox in events[:15]:
                lines.append(f"Non-text panel change: capture={idx}, bbox={bbox}")
        else:
            lines.append("Non-text panel changes: events=0")
        return lines

    def _save_image(self, img: Image) -> tuple[str, float]:
        """Save the image on disk.

        :param img: The image to save.
        :return: The saved image file name and PNG save duration in milliseconds.
        """
        file_name = f"{datetime.datetime.now().strftime('%H%M%S%f')}.png"
        output_location = os.path.join(self._debug_output_location, file_name)
        save_start = time.perf_counter()
        img.save(output_location)
        save_ms = (time.perf_counter() - save_start) * 1000
        self._log_signal.emit((f"Saving {file_name}."))
        return file_name, save_ms
