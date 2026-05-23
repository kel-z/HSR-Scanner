import time
from dataclasses import dataclass

from PIL import Image as PILImage
from PIL.Image import Image

from utils import patched_pytesseract as pytesseract
from utils.data import resource_path
from utils.ocr import DIN_ALTERNATE, preprocess_img
from utils.ocr_profile import is_ocr_profile_enabled, record_ocr_batch


@dataclass(frozen=True)
class BatchOcrResult:
    """OCR result for one source image inside a batched Tesseract call."""

    index: int
    text: str
    words: list[str]


@dataclass(frozen=True)
class BatchOcrProfile:
    """Timing details for one batched Tesseract call."""

    image_count: int
    compose_ms: float
    preprocess_ms: float
    ocr_ms: float
    total_ms: float
    composite_size: tuple[int, int]


def batch_image_to_strings(
    images: list[Image],
    whitelist: str,
    psm: int,
    force_preprocess: bool = False,
    preprocess_func=preprocess_img,
    remove_newline: bool = True,
    padding: int = 40,
    background: str | tuple[int, int, int] = "white",
) -> tuple[list[str], BatchOcrProfile]:
    """OCR multiple same-config crops with one Tesseract TSV call.

    This is intended for homogeneous fields, e.g. all relic levels or all relic
    main stats. It maps TSV words back to each source crop by vertical bounds.
    """
    if not images:
        return [], BatchOcrProfile(0, 0.0, 0.0, 0.0, 0.0, (0, 0))

    total_start = time.perf_counter()
    if preprocess_func is None:
        preprocess_func = preprocess_img

    preprocess_start = time.perf_counter()
    prepared_images = [
        preprocess_func(img) if force_preprocess else img for img in images
    ]
    preprocess_ms = (time.perf_counter() - preprocess_start) * 1000

    compose_start = time.perf_counter()
    composite, bounds = _compose_vertical_batch(prepared_images, padding, background)
    compose_ms = (time.perf_counter() - compose_start) * 1000

    ocr_start = time.perf_counter()
    rows = _run_tesseract_tsv(composite, whitelist, psm)
    ocr_ms = (time.perf_counter() - ocr_start) * 1000

    results = _map_tsv_rows_to_results(rows, bounds, remove_newline)
    result_texts = [result.text for result in results]
    profile = BatchOcrProfile(
        image_count=len(images),
        compose_ms=compose_ms,
        preprocess_ms=preprocess_ms,
        ocr_ms=ocr_ms,
        total_ms=(time.perf_counter() - total_start) * 1000,
        composite_size=composite.size,
    )
    if is_ocr_profile_enabled():
        record_ocr_batch(
            image_count=len(images),
            composite_size=composite.size,
            whitelist=whitelist,
            psm=psm,
            force_preprocess=force_preprocess,
            remove_newline=remove_newline,
            lang=DIN_ALTERNATE,
            final_lang=DIN_ALTERNATE,
            compose_ms=compose_ms,
            preprocess_ms=preprocess_ms,
            ocr_ms=ocr_ms,
            total_ms=profile.total_ms,
            result_lengths=[len(text or "") for text in result_texts],
        )
    return result_texts, profile


def batch_image_to_strings_chunked(
    images: list[Image],
    whitelist: str,
    psm: int,
    force_preprocess: bool = False,
    preprocess_func=preprocess_img,
    remove_newline: bool = True,
    padding: int = 40,
    chunk_size: int = 50,
    background: str | tuple[int, int, int] = "white",
) -> tuple[list[str], list[BatchOcrProfile]]:
    """OCR multiple same-config crops in bounded-size CLI batches."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    all_results = []
    profiles = []
    for start in range(0, len(images), chunk_size):
        chunk_results, profile = batch_image_to_strings(
            images[start : start + chunk_size],
            whitelist,
            psm,
            force_preprocess,
            preprocess_func,
            remove_newline,
            padding,
            background,
        )
        all_results.extend(chunk_results)
        profiles.append(profile)

    return all_results, profiles


def _compose_vertical_batch(
    images: list[Image], padding: int, background: str | tuple[int, int, int] = "white"
) -> tuple[Image, list[tuple[int, int]]]:
    widths = [img.size[0] for img in images]
    heights = [img.size[1] for img in images]
    width = max(widths)
    height = sum(heights) + padding * (len(images) + 1)
    composite = PILImage.new("RGB", (width, height), background)

    bounds = []
    y = padding
    for img in images:
        normalized = img.convert("RGB")
        composite.paste(normalized, (0, y))
        bounds.append((y, y + img.size[1]))
        y += img.size[1] + padding

    return composite, bounds


def _run_tesseract_tsv(
    image: Image,
    whitelist: str,
    psm: int,
) -> list[dict[str, str]]:
    tessdata_dir = resource_path("assets/tesseract/tessdata")
    config = (
        f'--tessdata-dir "{tessdata_dir}" '
        f'-c tessedit_char_whitelist="{whitelist}" '
        f"--psm {psm}"
    )
    tsv = pytesseract.image_to_data(image, config=config, lang=DIN_ALTERNATE)
    return _parse_tsv(tsv)


def _parse_tsv(tsv: str) -> list[dict[str, str]]:
    lines = [line for line in tsv.splitlines() if line.strip()]
    if len(lines) < 2:
        return []

    headers = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) < len(headers):
            values.extend([""] * (len(headers) - len(values)))
        rows.append(dict(zip(headers, values)))
    return rows


def _map_tsv_rows_to_results(
    rows: list[dict[str, str]],
    bounds: list[tuple[int, int]],
    remove_newline: bool,
) -> list[BatchOcrResult]:
    line_words: list[dict[tuple[int, int, int], list[tuple[int, str]]]] = [
        {} for _ in bounds
    ]

    for row in rows:
        text = row.get("text", "").strip()
        if not text:
            continue
        try:
            top = int(float(row.get("top", 0)))
            height = int(float(row.get("height", 0)))
            left = int(float(row.get("left", 0)))
            center_y = top + height // 2
        except ValueError:
            continue

        index = _find_bound_index(bounds, center_y)
        if index is None:
            continue

        line_key = (
            _safe_int(row.get("block_num", "0")),
            _safe_int(row.get("par_num", "0")),
            _safe_int(row.get("line_num", "0")),
        )
        line_words[index].setdefault(line_key, []).append((left, text))

    results = []
    for index, lines in enumerate(line_words):
        rendered_lines = []
        words = []
        for line_key in sorted(lines):
            line = [word for _, word in sorted(lines[line_key])]
            words.extend(line)
            rendered_lines.append(" ".join(line))
        text = "\n".join(rendered_lines).strip()
        if remove_newline:
            text = text.replace("\n", " ")
        results.append(BatchOcrResult(index=index, text=text, words=words))

    return results


def _find_bound_index(bounds: list[tuple[int, int]], y: int) -> int | None:
    for index, (start, end) in enumerate(bounds):
        if start <= y <= end:
            return index
    return None


def _safe_int(value: str) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0
