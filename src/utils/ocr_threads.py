import math
import os


def get_host_thread_count() -> int:
    """Return the number of logical threads available on the host."""
    return max(1, os.cpu_count() or 1)


def clamp_thread_count(
    thread_count: int | None, host_threads: int | None = None
) -> int:
    """Clamp an OCR thread count to the valid host range."""
    resolved_host_threads = host_threads or get_host_thread_count()

    try:
        parsed_thread_count = int(thread_count) if thread_count is not None else 1
    except (TypeError, ValueError):
        parsed_thread_count = 1

    return max(1, min(parsed_thread_count, resolved_host_threads))


def threads_from_percent(percent: int, host_threads: int | None = None) -> int:
    """Convert a percentage of host threads to an absolute thread count."""
    resolved_host_threads = host_threads or get_host_thread_count()
    clamped_percent = max(1, min(int(percent), 100))
    return clamp_thread_count(
        math.ceil(resolved_host_threads * clamped_percent / 100),
        resolved_host_threads,
    )


def percent_from_threads(thread_count: int, host_threads: int | None = None) -> int:
    """Convert an absolute thread count to a percentage of host threads."""
    resolved_host_threads = host_threads or get_host_thread_count()
    clamped_thread_count = clamp_thread_count(thread_count, resolved_host_threads)
    return max(1, min(round(clamped_thread_count * 100 / resolved_host_threads), 100))
