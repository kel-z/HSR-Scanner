import datetime
import csv
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
from utils.scan_integrity import ScanIntegrityError


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
        self._inventory_before_navigation = None
        self._diagnostic_panel = None
        self._mss = None
        self._mss_failed = False
        self._mss_fallback_logged = False
        self._pipeline_cache = None
        self._capture_trace = []
        self._capture_trace_dropped = 0
        self._overlap_evidence = []

    def configure_inventory_capture(self, uid, advance=None, interrupt=None):
        self._capture_uid = uid
        self._capture_advance = advance
        self._capture_interrupt = interrupt

    def reset_inventory_pipeline(self):
        self._pipeline_cache = None

    def _trace_capture(self, row):
        if not self._debug:
            return
        if not hasattr(self, '_capture_trace'):
            self._capture_trace = []
            self._capture_trace_dropped = 0
        if len(self._capture_trace) < 200000:
            self._capture_trace.append((getattr(self, '_capture_id', 0), *row))
        else:
            self._capture_trace_dropped += 1

    def flush_inventory_capture_trace(self):
        if not self._debug or not self._debug_output_location:
            return
        path = os.path.join(self._debug_output_location, 'capture_pipeline.csv')
        with open(path, 'w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(('capture_id', 'event', 'item_type', 'uid', 'target_uid', 'poll',
                             'grab_start_s', 'grab_end_s', 'signature_end_s',
                             'equals_previous', 'equals_candidate', 'transition_id',
                             'source', 'decision'))
            writer.writerows(getattr(self, '_capture_trace', []))
            dropped = getattr(self, '_capture_trace_dropped', 0)
            if dropped:
                writer.writerow(('', 'dropped', '', '', '', '', '', '', '', '', '', '', '', dropped))
                self._log_signal.emit((f'Capture trace limit reached: {dropped} rows dropped.', LogLevel.WARNING))
        for uid, before, following in getattr(self, '_overlap_evidence', []):
            before.save(os.path.join(self._debug_output_location, f'overlap-{uid}-unconfirmed.png'))
            following.save(os.path.join(self._debug_output_location, f'overlap-{uid}-following.png'))
        return path

    def close(self) -> None:
        """Close the cached mss backend if it was opened."""
        if self._mss is None:
            return
        self._mss.close()
        self._mss = None

    def screenshot_screen(self) -> Image:
        """Takes a screenshot of the entire screen

        :return: The screenshot
        """
        do_not_save = True  # so users don't unintentionally reveal their UID when naively sharing debug folder
        return self._take_screenshot(0, 0, 1, 1, do_not_save)

    def remember_inventory_before_navigation(self) -> None:
        """Retain the already captured panel by reference; never grab on navigation."""
        if self._debug:
            self._inventory_before_navigation = self._diagnostic_panel

    def save_inventory_transition_diagnostic(
        self, item_id: int, attempt: int
    ) -> str | None:
        """Save an image of the grid and panel for a failure, excluding the account UID."""
        if not self._debug or not self._debug_output_location:
            return None

        file_name = f"inventory-transition-item-{item_id}-attempt-{attempt}.png"
        output_location = os.path.join(self._debug_output_location, file_name)
        try:
            image = self._take_screenshot(0.045, 0.12, 0.925, 0.76, do_not_save=True)
            image.save(output_location)
            if attempt == 0 and self._inventory_before_navigation is not None:
                self._inventory_before_navigation.save(os.path.join(
                    self._debug_output_location, f"inventory-transition-item-{item_id}-before-panel.png"
                ))
            if self._diagnostic_panel is not None:
                self._diagnostic_panel.save(os.path.join(
                    self._debug_output_location, f"inventory-transition-item-{item_id}-attempt-{attempt}-exact-panel.png"
                ))
        except Exception as exc:
            self._log_signal.emit(
                (
                    f"Item UID {item_id}: Failed to save transition diagnostic: {exc}",
                    LogLevel.ERROR,
                )
            )
            return None
        self._log_signal.emit(
            (
                f"Item UID {item_id}: Saved transition diagnostic {file_name}. "
                "It shows the selected inventory tile and details panel; no "
                "additional navigation input was sent. Before-panel is the cached "
                "prior panel, not a prior selection image; selection movement "
                "cannot be proved from that image alone.",
                LogLevel.WARNING,
            )
        )
        return file_name

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
        settle_s: float = 0.0,
    ) -> tuple[dict, bytes]:
        """Takes a stats screenshot once the panel changes from the previous item.

        Polls until the panel's text-band signature differs from
        ``previous_panel_bytes`` and settles. On timeout returns the previous
        signature so the caller must retry or fail the scan.

        :param scan_type: The scan type
        :param previous_panel_bytes: Previous item's text-band signature bytes, or None
        :param timeout_s: Max time to wait for the panel to change
        :param settle_s: Optional minimum unchanged time. Zero requires two
            consecutive matching changed signatures without an added delay.
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
        return self._screenshot_stats(key, previous_panel_bytes, timeout_s, settle_s)

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
        settle_s: float = 0.0,
    ) -> tuple[dict, bytes]:
        """Takes a screenshot of the stats

        :param key: The key of the stats to screenshot
        :param previous_panel_bytes: Previous item's text-band signature bytes, or None
        :param timeout_s: Max time to poll for the panel to change
        :return: The cropped stats dict and the panel's text-band signature bytes
        """
        coords = SCREENSHOT_COORDS[self._aspect_ratio]
        self._capture_id = getattr(self, '_capture_id', 0) + 1
        timing_start = time.perf_counter()

        x_pct, y_pct, w_pct, h_pct = coords[STATS]
        x = self._window_x + int(self._window_width * x_pct)
        y = self._window_y + int(self._window_height * y_pct)
        width = int(self._window_width * w_pct)
        height = int(self._window_height * h_pct)
        bbox = (int(x), int(y), int(x + width), int(y + height))

        # Wait for the whole panel to settle; the name renders before the substats.
        polls = 0
        poll_start = time.perf_counter()
        changed_signature = None
        stable_since = None
        settled = previous_panel_bytes is None
        profile = self._debug
        grabs_s = signatures_s = nontext_s = 0.0
        first_change_at = None
        signature_changes = 0
        uid = getattr(self, '_capture_uid', 0)
        advance = getattr(self, '_capture_advance', None)
        interrupt = getattr(self, '_capture_interrupt', None)
        candidate_raw = None
        candidate_backend = None
        navigation_issued = False
        decision = 'timeout'
        pending_nav = None
        while True:
            polls += 1
            grab_start = time.perf_counter()
            cache = getattr(self, '_pipeline_cache', None)
            source = 'grab'
            try:
                if interrupt is not None:
                    interrupt()
                if cache is not None and cache[0] == uid and cache[1] == key:
                    _, _, raw_img, backend, panel_bytes, cached_times = cache
                    self._pipeline_cache = None
                    source = 'cache'
                else:
                    raw_img, backend = self._grab_screenshot(bbox)
            except BaseException:
                if profile and pending_nav is not None:
                    self._trace_capture(('nav', key, uid, uid + 1, polls - 1,
                                         *pending_nav, '', '', '', '', '', 'issued'))
                if profile:
                    self._trace_capture(('abort', key, uid, '', polls, '', '',
                                         time.perf_counter(), '', '', signature_changes, source, 'exception'))
                raise
            grab_end = time.perf_counter()
            if source == 'grab':
                panel_bytes = self._panel_change_signature(raw_img, key)
            changed = (
                previous_panel_bytes is None or panel_bytes != previous_panel_bytes
            )
            equals_candidate = panel_bytes == changed_signature
            if profile:
                signature_end = time.perf_counter()
                if source == 'grab':
                    grabs_s += grab_end - grab_start
                    signatures_s += signature_end - grab_end
                if changed and first_change_at is None:
                    first_change_at = signature_end
                if pending_nav is not None:
                    self._trace_capture(('nav', key, uid, uid + 1, polls - 1,
                                         *pending_nav, '', '', '', '', '', 'issued'))
                    pending_nav = None
                trace_times = cached_times if source == 'cache' else (grab_start, grab_end, signature_end)
                self._trace_capture(('poll', key, uid, '', polls, *trace_times, not changed,
                                     equals_candidate, signature_changes,
                                     source, ''))
            if not changed and self._debug and self._verbose_logs:
                self._record_nontext_change(raw_img)
            now = time.perf_counter()
            if profile and not changed:
                nontext_s += now - signature_end
            if not changed:
                changed_signature = None
                stable_since = None
            if changed:
                if previous_panel_bytes is None:
                    settled = True
                    decision = 'initial'
                    break
                if not equals_candidate:
                    if navigation_issued and signature_changes >= 2 and candidate_raw is not None:
                        self._pipeline_cache = (uid + 1, key, raw_img, backend, panel_bytes,
                                                (grab_start, grab_end, signature_end if profile else now))
                        if profile:
                            if not hasattr(self, '_overlap_evidence'):
                                self._overlap_evidence = []
                            if len(self._overlap_evidence) < 8:
                                self._overlap_evidence.append((uid, candidate_raw, raw_img))
                        raw_img, backend, panel_bytes = candidate_raw, candidate_backend, changed_signature
                        settled = True
                        decision = 'unconfirmed_overlap'
                        break
                    signature_changes += 1
                    changed_signature = panel_bytes
                    candidate_raw, candidate_backend = raw_img, backend
                    stable_since = now
                elif stable_since is not None and now - stable_since >= settle_s:
                    settled = True
                    decision = 'stable'
                    break
            if now - poll_start >= timeout_s:
                break
            if changed and advance is not None and not navigation_issued:
                # Keep this adjacent to the next grab: no logging, sleep or IO.
                self._diagnostic_panel = raw_img
                pending_nav = advance(raw_img, key)
                navigation_issued = pending_nav is not None
                if not navigation_issued:
                    advance = None
        poll_end = time.perf_counter()
        if profile:
            self._trace_capture(('accept' if settled else 'timeout', key, uid, '', polls,
                                 '', '', poll_end, '', '', signature_changes, '', decision))
        if navigation_issued and not settled:
            self._diagnostic_panel = raw_img
            if profile and getattr(self, '_debug_output_location', ''):
                self.save_inventory_transition_diagnostic(uid, 0)
            raise ScanIntegrityError(
                f'Item UID {uid}: panel did not settle after navigation to UID {uid + 1}; '
                'ownership is unresolved, scan aborted without recapture or export.')
        if decision == 'unconfirmed_overlap':
            self._log_signal.emit((
                f'Item UID {uid}: UNCONFIRMED overlap fallback; accepted preceding '
                f'candidate after {polls} polls, cached new observation for UID {uid + 1}.',
                LogLevel.WARNING))
        panel_wait_ms = (poll_end - poll_start) * 1000
        self._diagnostic_panel = raw_img
        if previous_panel_bytes is not None and not settled:
            # Report "unchanged" so the caller retries or aborts.
            panel_bytes = previous_panel_bytes
            changed = False

        resize_start = time.perf_counter()
        img = raw_img.resize(
            (int(width / self._x_scaling_factor), int(height / self._y_scaling_factor))
        )
        resize_end = time.perf_counter()

        file_name = "not_saved"
        save_ms = 0.0
        if self._debug and self._save_capture_png:
            file_name, save_ms = self._save_image(img)

        crop_start = time.perf_counter() if profile else 0.0
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
            crop_end = time.perf_counter()
            # Diff bbox of the accepted frame: a real item swap repaints most
            # of the panel, so a tiny changed area flags a suspect accept.
            accept_bbox = None
            accept_area = None
            if (
                self._verbose_logs
                and changed
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
                    "all_grabs_ms": grabs_s * 1000,
                    "signature_ms": signatures_s * 1000,
                    "nontext_diagnostic_ms": nontext_s * 1000,
                    "first_change_ms": ((first_change_at or poll_end) - poll_start) * 1000,
                    "confirmation_ms": (poll_end - first_change_at) * 1000 if first_change_at is not None else 0.0,
                    "first_change_seen": first_change_at is not None,
                    "signature_changes": signature_changes,
                    "crop_ms": (crop_end - crop_start) * 1000,
                    "accept_diagnostic_ms": total_ms - (crop_end - timing_start) * 1000,
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

    # Text regions only, as (x0, y0, x1, y1): animated art changes on its own.
    _PANEL_SIGNATURE_BANDS = {
        "relic": (
            (0.06, 0, 1, 0.09),
            (0.06, 0.09, 0.30, 0.15),
            (0.06, 0.22, 0.30, 0.34),
            (0.115, 0.34, 0.96, 0.90),
        ),
        "light_cone": (
            (0.06, 0, 1, 0.09), (0.115, 0.31, 0.96, 0.90),
        ),
    }

    @classmethod
    def _panel_change_signature(cls, img: Image, key: str) -> bytes:
        """Bytes of the text regions of a stats panel."""
        w, h = img.size
        return b"".join(
            img.crop(
                (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
            )
            .tobytes()
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
        for metric in ("panel_wait_ms", "grab_ms", "resize_ms", "save_ms", "total_ms",
                       "all_grabs_ms", "signature_ms", "nontext_diagnostic_ms",
                       "first_change_ms", "confirmation_ms", "crop_ms", "accept_diagnostic_ms"):
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
        lines.append(
            "Capture profile semantics: all_grabs_ms includes backend capture and RGB "
            "conversion across every poll; grab_ms is last poll only. first_change_ms "
            "and confirmation_ms partition panel_wait_ms approximately; signature_ms "
            "includes text-band copies and previous-buffer comparison. These overlap "
            "panel_wait_ms, so do not add them to it. "
            f"no_change_attempts={sum(not r['first_change_seen'] for r in records)}, "
            f"multiple_candidate_attempts={sum(r['signature_changes'] > 1 for r in records)}"
        )

        suspicious = [
            (i, r["accept_area"], r["accept_bbox"])
            for i, r in enumerate(records)
            if r.get("accept_area") is not None and r["accept_area"] < 0.02
        ]
        lines.append(
            f"Suspicious small-area accepts (<2% of panel): count={len(suspicious)}"
            if self._verbose_logs else
            "Full-panel difference diagnostics: disabled (enable verbose logging); "
            "basic timing and failure images remain enabled."
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
        elif self._verbose_logs:
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
