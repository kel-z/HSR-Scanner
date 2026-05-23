from collections.abc import Callable
from typing import TypeVar

from enums.log_level import LogLevel

Stats = TypeVar("Stats")
MAX_DUPLICATE_CAPTURE_RETRIES = 2


def recover_duplicate_capture(
    capture_stats: Callable[[], tuple[Stats, bytes]],
    previous_panel_bytes: bytes | None,
    item_id: int,
    log: Callable[[str, LogLevel], None],
    sleep: Callable[[float], None],
    retry_delay: float,
) -> tuple[Stats, bytes]:
    """Capture stats and retry when the panel is byte-identical to the previous item."""
    stats, panel_bytes = capture_stats()
    if previous_panel_bytes is None or panel_bytes != previous_panel_bytes:
        return stats, panel_bytes

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

    log(
        f"Item UID {item_id}: Duplicate stats capture persisted after retries. "
        "Continuing with latest capture.",
        LogLevel.WARNING,
    )
    return stats, panel_bytes
