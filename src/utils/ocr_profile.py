import contextlib
import contextvars
import statistics
import threading
import time
from collections import Counter
from typing import Callable, Iterator

from enums.log_level import LogLevel

_enabled = False
_detail_logs_enabled = True
_log_callback: Callable[[str, LogLevel], None] | None = None
_lock = threading.Lock()
_ocr_calls: list[dict] = []
_ocr_batches: list[dict] = []
_attempts: list[dict] = []
_parse_tasks: list[dict] = []
_session_started_at = time.perf_counter()

_context = contextvars.ContextVar("ocr_profile_context", default={})


def configure_ocr_profile(
    enabled: bool,
    log_callback: Callable[[str, LogLevel], None] | None = None,
    detail_logs_enabled: bool = True,
) -> None:
    """Enable or disable OCR profiling for the current scan.

    Profile rows are always recorded in memory while enabled (they feed the
    end-of-scan summary); ``detail_logs_enabled`` additionally emits a log
    line per OCR event, which is expensive at full-scan volume.
    """
    global _enabled, _detail_logs_enabled, _log_callback
    _enabled = enabled
    _detail_logs_enabled = detail_logs_enabled
    _log_callback = log_callback


def reset_ocr_profile() -> None:
    """Clear all collected OCR profile data."""
    global _session_started_at
    with _lock:
        _ocr_calls.clear()
        _ocr_batches.clear()
        _attempts.clear()
        _parse_tasks.clear()
        _session_started_at = time.perf_counter()


def is_ocr_profile_enabled() -> bool:
    return _enabled


@contextlib.contextmanager
def ocr_profile_context(**kwargs) -> Iterator[None]:
    """Attach item/field context to OCR work running in this scope."""
    if not _enabled:
        yield
        return

    current = dict(_context.get({}))
    current.update({k: v for k, v in kwargs.items() if v is not None})
    token = _context.set(current)
    try:
        yield
    finally:
        _context.reset(token)


def get_ocr_profile_context() -> dict:
    if not _enabled:
        return {}
    return dict(_context.get({}))


def log_ocr_profile_detail(message: str) -> None:
    if _enabled and _detail_logs_enabled and _log_callback:
        _log_callback(message, LogLevel.DEBUG)


def record_ocr_attempt(
    call_id: int,
    attempt_index: int,
    config_lang: str,
    config: str,
    target: str,
    elapsed_ms: float,
    result: str,
    error: Exception | None = None,
) -> None:
    if not _enabled:
        return

    context = get_ocr_profile_context()
    row = {
        "call_id": call_id,
        "attempt_index": attempt_index,
        "config_lang": config_lang,
        "config": config,
        "target": target,
        "elapsed_ms": elapsed_ms,
        "result_len": len(result or ""),
        "result_preview": _preview(result),
        "error": f"{type(error).__name__}: {error}" if error else "",
        **context,
    }
    with _lock:
        _attempts.append(row)

    status = "error" if error else ("text" if result.strip() else "empty")
    log_ocr_profile_detail(
        "OCR attempt: "
        f"call={call_id}, attempt={attempt_index}, status={status}, "
        f"target={target}, lang={config_lang}, elapsed_ms={elapsed_ms:.3f}, "
        f"result_len={row['result_len']}, result={row['result_preview']}, "
        f"context={_format_context(context)}"
        + (f", error={row['error']}" if error else "")
    )


def record_ocr_call(
    call_id: int,
    image_size: tuple[int, int] | None,
    whitelist: str,
    psm: int,
    force_preprocess: bool,
    remove_newline: bool,
    lang: str,
    final_lang: str,
    attempts_count: int,
    direct_ms: float,
    preprocess_ms: float,
    preprocessed_ocr_ms: float,
    total_ms: float,
    used_preprocess: bool,
    result: str,
) -> None:
    if not _enabled:
        return

    context = get_ocr_profile_context()
    row = {
        "call_id": call_id,
        "image_size": image_size,
        "whitelist_len": len(whitelist),
        "psm": psm,
        "force_preprocess": force_preprocess,
        "remove_newline": remove_newline,
        "lang": lang,
        "final_lang": final_lang,
        "attempts_count": attempts_count,
        "direct_ms": direct_ms,
        "preprocess_ms": preprocess_ms,
        "preprocessed_ocr_ms": preprocessed_ocr_ms,
        "total_ms": total_ms,
        "used_preprocess": used_preprocess,
        "result_len": len(result or ""),
        "result_preview": _preview(result),
        **context,
    }
    with _lock:
        _ocr_calls.append(row)

    log_ocr_profile_detail(
        "OCR call: "
        f"call={call_id}, total_ms={total_ms:.3f}, direct_ms={direct_ms:.3f}, "
        f"preprocess_ms={preprocess_ms:.3f}, preprocessed_ocr_ms={preprocessed_ocr_ms:.3f}, "
        f"used_preprocess={used_preprocess}, psm={psm}, lang={lang}, "
        f"final_lang={final_lang}, attempts={attempts_count}, "
        f"image_size={image_size}, whitelist_len={len(whitelist)}, "
        f"result_len={row['result_len']}, result={row['result_preview']}, "
        f"context={_format_context(context)}"
    )


def record_ocr_batch(
    image_count: int,
    composite_size: tuple[int, int] | None,
    whitelist: str,
    psm: int,
    force_preprocess: bool,
    remove_newline: bool,
    lang: str,
    final_lang: str,
    compose_ms: float,
    preprocess_ms: float,
    ocr_ms: float,
    total_ms: float,
    result_lengths: list[int],
) -> None:
    if not _enabled:
        return

    context = get_ocr_profile_context()
    row = {
        "image_count": image_count,
        "composite_size": composite_size,
        "whitelist_len": len(whitelist),
        "psm": psm,
        "force_preprocess": force_preprocess,
        "remove_newline": remove_newline,
        "lang": lang,
        "final_lang": final_lang,
        "compose_ms": compose_ms,
        "preprocess_ms": preprocess_ms,
        "ocr_ms": ocr_ms,
        "total_ms": total_ms,
        "result_count": len(result_lengths),
        "nonempty_results": sum(1 for length in result_lengths if length > 0),
        "result_chars": sum(result_lengths),
        **context,
    }
    with _lock:
        _ocr_batches.append(row)

    log_ocr_profile_detail(
        "OCR batch: "
        f"images={image_count}, total_ms={total_ms:.3f}, compose_ms={compose_ms:.3f}, "
        f"preprocess_ms={preprocess_ms:.3f}, ocr_ms={ocr_ms:.3f}, psm={psm}, "
        f"lang={lang}, final_lang={final_lang}, image_size={composite_size}, "
        f"whitelist_len={len(whitelist)}, nonempty_results={row['nonempty_results']}, "
        f"result_chars={row['result_chars']}, context={_format_context(context)}"
    )


def record_parse_task(
    item_type: str,
    uid: int | str | None,
    parser: str,
    queue_wait_ms: float,
    parse_ms: float,
    success: bool,
) -> None:
    if not _enabled:
        return

    row = {
        "item_type": item_type,
        "uid": uid,
        "parser": parser,
        "queue_wait_ms": queue_wait_ms,
        "parse_ms": parse_ms,
        "success": success,
    }
    with _lock:
        _parse_tasks.append(row)

    log_ocr_profile_detail(
        "OCR parse task: "
        f"item_type={item_type}, uid={uid}, parser={parser}, "
        f"queue_wait_ms={queue_wait_ms:.3f}, parse_ms={parse_ms:.3f}, success={success}"
    )


def get_ocr_profile_summary_lines() -> list[str]:
    if not _enabled:
        return []

    with _lock:
        calls = list(_ocr_calls)
        batches = list(_ocr_batches)
        attempts = list(_attempts)
        parse_tasks = list(_parse_tasks)
        session_ms = (time.perf_counter() - _session_started_at) * 1000

    lines = [
        "OCR profile summary: "
        f"session_ms={session_ms:.3f}, calls={len(calls)}, batches={len(batches)}, attempts={len(attempts)}, "
        f"parse_tasks={len(parse_tasks)}"
    ]

    if calls:
        totals = [x["total_ms"] for x in calls]
        direct = [x["direct_ms"] for x in calls]
        preprocess = [x["preprocess_ms"] for x in calls]
        pre_ocr = [x["preprocessed_ocr_ms"] for x in calls]
        lines.append("OCR profile calls total_ms: " + _stats_text(totals))
        lines.append("OCR profile direct_ocr_ms: " + _stats_text(direct))
        lines.append("OCR profile preprocess_ms: " + _stats_text(preprocess))
        lines.append("OCR profile preprocessed_ocr_ms: " + _stats_text(pre_ocr))
        lines.append(
            "OCR profile calls by field: "
            + _counter_text(Counter(str(x.get("field", "unknown")) for x in calls))
        )
        lines.append(
            "OCR profile calls by item_type: "
            + _counter_text(Counter(str(x.get("item_type", "unknown")) for x in calls))
        )
        lines.extend(_slowest_call_lines(calls, 10))

    if batches:
        totals = [x["total_ms"] for x in batches]
        compose = [x["compose_ms"] for x in batches]
        preprocess = [x["preprocess_ms"] for x in batches]
        ocr = [x["ocr_ms"] for x in batches]
        images = [float(x["image_count"]) for x in batches]
        lines.append("OCR profile batches total_ms: " + _stats_text(totals))
        lines.append("OCR profile batch compose_ms: " + _stats_text(compose))
        lines.append("OCR profile batch preprocess_ms: " + _stats_text(preprocess))
        lines.append("OCR profile batch ocr_ms: " + _stats_text(ocr))
        lines.append("OCR profile batch image_count: " + _stats_text(images))
        lines.append(
            "OCR profile batches by field: "
            + _counter_text(Counter(str(x.get("field", "unknown")) for x in batches))
        )
        lines.append(
            "OCR profile batches by item_type: "
            + _counter_text(Counter(str(x.get("item_type", "unknown")) for x in batches))
        )
        lines.extend(_slowest_batch_lines(batches, 10))

    if attempts:
        lines.append(
            "OCR profile attempts by lang: "
            + _counter_text(Counter(str(x.get("config_lang", "unknown")) for x in attempts))
        )
        lines.append(
            "OCR profile attempts by target: "
            + _counter_text(Counter(str(x.get("target", "unknown")) for x in attempts))
        )
        errors = [x for x in attempts if x.get("error")]
        lines.append(f"OCR profile attempt errors: count={len(errors)}")
        lines.extend(_slowest_attempt_lines(attempts, 10))

    if parse_tasks:
        parse_ms = [x["parse_ms"] for x in parse_tasks]
        queue_ms = [x["queue_wait_ms"] for x in parse_tasks]
        lines.append("OCR profile parse_ms: " + _stats_text(parse_ms))
        lines.append("OCR profile queue_wait_ms: " + _stats_text(queue_ms))
        lines.append(
            "OCR profile parse tasks by item_type: "
            + _counter_text(Counter(str(x.get("item_type", "unknown")) for x in parse_tasks))
        )
        lines.extend(_slowest_parse_lines(parse_tasks, 10))

    return lines


def _stats_text(values: list[float]) -> str:
    if not values:
        return "count=0"
    sorted_values = sorted(values)
    return (
        f"count={len(values)}, total={sum(values):.3f}, avg={statistics.mean(values):.3f}, "
        f"median={statistics.median(values):.3f}, p95={_percentile(sorted_values, 95):.3f}, "
        f"max={max(values):.3f}"
    )


def _percentile(sorted_values: list[float], percentile: int) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, min(len(sorted_values) - 1, round((percentile / 100) * len(sorted_values)) - 1))
    return sorted_values[index]


def _counter_text(counter: Counter) -> str:
    return ", ".join(f"{key}={value}" for key, value in counter.most_common()) or "none"


def _slowest_call_lines(calls: list[dict], limit: int) -> list[str]:
    lines = []
    for row in sorted(calls, key=lambda x: x["total_ms"], reverse=True)[:limit]:
        lines.append(
            "OCR profile slow call: "
            f"call={row['call_id']}, total_ms={row['total_ms']:.3f}, "
            f"field={row.get('field', 'unknown')}, item_type={row.get('item_type', 'unknown')}, "
            f"uid={row.get('uid', 'unknown')}, psm={row['psm']}, lang={row['lang']}, "
            f"used_preprocess={row['used_preprocess']}, result={row['result_preview']}"
        )
    return lines


def _slowest_batch_lines(batches: list[dict], limit: int) -> list[str]:
    lines = []
    for row in sorted(batches, key=lambda x: x["total_ms"], reverse=True)[:limit]:
        lines.append(
            "OCR profile slow batch: "
            f"field={row.get('field', 'unknown')}, item_type={row.get('item_type', 'unknown')}, "
            f"images={row['image_count']}, total_ms={row['total_ms']:.3f}, "
            f"ocr_ms={row['ocr_ms']:.3f}, preprocess_ms={row['preprocess_ms']:.3f}, "
            f"compose_ms={row['compose_ms']:.3f}, psm={row['psm']}, lang={row['lang']}, "
            f"nonempty_results={row['nonempty_results']}, result_chars={row['result_chars']}"
        )
    return lines


def _slowest_attempt_lines(attempts: list[dict], limit: int) -> list[str]:
    lines = []
    for row in sorted(attempts, key=lambda x: x["elapsed_ms"], reverse=True)[:limit]:
        lines.append(
            "OCR profile slow attempt: "
            f"call={row['call_id']}, attempt={row['attempt_index']}, elapsed_ms={row['elapsed_ms']:.3f}, "
            f"field={row.get('field', 'unknown')}, item_type={row.get('item_type', 'unknown')}, "
            f"uid={row.get('uid', 'unknown')}, target={row['target']}, lang={row['config_lang']}, "
            f"result={row['result_preview']}"
            + (f", error={row['error']}" if row.get("error") else "")
        )
    return lines


def _slowest_parse_lines(parse_tasks: list[dict], limit: int) -> list[str]:
    lines = []
    for row in sorted(parse_tasks, key=lambda x: x["parse_ms"], reverse=True)[:limit]:
        lines.append(
            "OCR profile slow parse: "
            f"item_type={row['item_type']}, uid={row['uid']}, parser={row['parser']}, "
            f"parse_ms={row['parse_ms']:.3f}, queue_wait_ms={row['queue_wait_ms']:.3f}, "
            f"success={row['success']}"
        )
    return lines


def _format_context(context: dict) -> str:
    if not context:
        return "{}"
    return "{" + ", ".join(f"{k}={v}" for k, v in sorted(context.items())) + "}"


def _preview(value: str, limit: int = 80) -> str:
    text = repr((value or "").replace("\n", "\\n"))
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text
