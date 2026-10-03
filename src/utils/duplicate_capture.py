from collections.abc import Callable
from typing import TypeVar

from enums.log_level import LogLevel

Stats = TypeVar("Stats")
MAX_DUPLICATE_CAPTURE_RETRIES = 2


class UnresolvedDuplicateCaptureError(RuntimeError):
    """Raised when a new inventory item cannot be distinguished from the last."""

    def __init__(self, item_id: int, attempts: int) -> None:
        self.item_id = item_id
        self.attempts = attempts
        super().__init__(
            f"Item UID {item_id}: stats panel did not change after {attempts} "
            "capture attempts. The scan is incomplete and will not be exported."
        )


def recover_duplicate_capture(
    capture_stats: Callable[[], tuple[Stats, bytes]],
    previous_panel_bytes: bytes | None,
    item_id: int,
    log: Callable[[str, LogLevel], None],
    sleep: Callable[[float], None],
    retry_delay: float,
    on_duplicate: Callable[[int, Stats], None] | None = None,
) -> tuple[Stats, bytes]:
    """Capture stats, re-capturing while the panel matches the previous item.

    Retries never re-send navigation: the selection may already have moved.
    """
    stats, panel_bytes = capture_stats()
    if previous_panel_bytes is None or panel_bytes != previous_panel_bytes:
        return stats, panel_bytes

    if on_duplicate is not None:
        on_duplicate(0, stats)

    for retry in range(1, MAX_DUPLICATE_CAPTURE_RETRIES + 1):
        log(
            f"Item UID {item_id}: Duplicate stats capture detected. "
            f"Retrying... ({retry}/{MAX_DUPLICATE_CAPTURE_RETRIES})",
            LogLevel.WARNING,
        )
        sleep(retry_delay)

        stats, panel_bytes = capture_stats()
        if panel_bytes != previous_panel_bytes:
            log(
                f"Item UID {item_id}: Duplicate stats capture recovered on retry {retry}.",
                LogLevel.DEBUG,
            )
            return stats, panel_bytes
        if on_duplicate is not None:
            on_duplicate(retry, stats)

    log(
        f"Item UID {item_id}: Duplicate stats capture persisted after retries. "
        "Aborting incomplete scan; no export will be written.",
        LogLevel.ERROR,
    )
    raise UnresolvedDuplicateCaptureError(
        item_id, MAX_DUPLICATE_CAPTURE_RETRIES + 1
    )
