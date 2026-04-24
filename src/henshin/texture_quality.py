"""Lightweight rejection checks for generated UV texture atlases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image


TEXTURE_QUALITY_VERSION = "texture-quality-v1"


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _saturation(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    hi = max(r, g, b)
    lo = min(r, g, b)
    if hi <= 0:
        return 0.0
    return (hi - lo) / hi


def _resize_for_analysis(image: Image.Image, size: int = 256) -> Image.Image:
    converted = image.convert("RGB")
    if max(converted.size) <= size:
        return converted
    converted.thumbnail((size, size), Image.Resampling.LANCZOS)
    return converted


def _blank_ratio(image: Image.Image) -> float:
    pixels = list(image.getdata())
    if not pixels:
        return 0.0
    blank = 0
    for pixel in pixels:
        lum = _luminance(pixel)
        sat = _saturation(pixel)
        if lum >= 222 and sat <= 0.10:
            blank += 1
    return blank / len(pixels)


def _nonblank_bbox_area_ratio(image: Image.Image) -> float:
    width, height = image.size
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            pixel = image.getpixel((x, y))
            lum = _luminance(pixel)
            sat = _saturation(pixel)
            if lum < 222 or sat > 0.10:
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return 0.0
    bbox_w = max(xs) - min(xs) + 1
    bbox_h = max(ys) - min(ys) + 1
    return (bbox_w * bbox_h) / max(width * height, 1)


def _construction_orange_ratio(image: Image.Image) -> float:
    pixels = list(image.getdata())
    if not pixels:
        return 0.0
    orange = 0
    for r, g, b in pixels:
        if r >= 120 and 45 <= g <= 180 and b <= 115 and r - g >= 22 and g - b >= 8:
            orange += 1
    return orange / len(pixels)


def _line_leak_score(image: Image.Image, mode: str) -> float:
    gray = image.convert("L")
    width, height = gray.size
    if width < 12 or height < 12:
        return 0.0

    samples = 0
    hits = 0
    if mode == "vertical":
        x = width // 2
        points = [(x, y, (1, 0)) for y in range(6, height - 6)]
    elif mode == "horizontal":
        y = height // 2
        points = [(x, y, (0, 1)) for x in range(6, width - 6)]
    elif mode == "diag_down":
        span = min(width, height) - 12
        points = [(6 + i, 6 + i, (1, -1)) for i in range(span)]
    elif mode == "diag_up":
        span = min(width, height) - 12
        points = [(6 + i, height - 7 - i, (1, 1)) for i in range(span)]
    else:
        return 0.0

    for x, y, normal in points:
        nx, ny = normal
        center = gray.getpixel((x, y))
        a = gray.getpixel((max(0, min(width - 1, x + nx * 3)), max(0, min(height - 1, y + ny * 3))))
        b = gray.getpixel((max(0, min(width - 1, x - nx * 3)), max(0, min(height - 1, y - ny * 3))))
        neighbor = (a + b) / 2
        samples += 1
        if 35 <= center <= 225 and abs(center - neighbor) >= 16:
            hits += 1
    return hits / max(samples, 1)


def _micro_contrast_ratio(image: Image.Image) -> float:
    gray = image.convert("L").resize((128, 128), Image.Resampling.LANCZOS)
    width, height = gray.size
    hits = 0
    samples = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            center = gray.getpixel((x, y))
            neighbors = (
                gray.getpixel((x - 1, y)),
                gray.getpixel((x + 1, y)),
                gray.getpixel((x, y - 1)),
                gray.getpixel((x, y + 1)),
            )
            local_delta = max(abs(center - value) for value in neighbors)
            samples += 1
            if local_delta >= 68:
                hits += 1
    return hits / max(samples, 1)


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _corner_average(image: Image.Image) -> tuple[int, int, int]:
    width, height = image.size
    sample = max(4, min(width, height) // 20)
    pixels: list[tuple[int, int, int]] = []
    boxes = [
        (0, 0, sample, sample),
        (width - sample, 0, width, sample),
        (0, height - sample, sample, height),
        (width - sample, height - sample, width, height),
    ]
    for left, top, right, bottom in boxes:
        for y in range(top, bottom):
            for x in range(left, right):
                pixels.append(image.getpixel((x, y)))
    if not pixels:
        return (0, 0, 0)
    r = sum(pixel[0] for pixel in pixels) // len(pixels)
    g = sum(pixel[1] for pixel in pixels) // len(pixels)
    b = sum(pixel[2] for pixel in pixels) // len(pixels)
    return (r, g, b)


def _plain_border_ratio(image: Image.Image) -> float:
    width, height = image.size
    if width < 16 or height < 16:
        return 0.0
    bg = _corner_average(image)
    band = max(8, min(width, height) // 8)
    border_pixels = 0
    plain = 0
    for y in range(height):
        for x in range(width):
            if not (x < band or x >= width - band or y < band or y >= height - band):
                continue
            border_pixels += 1
            pixel = image.getpixel((x, y))
            if _color_distance(pixel, bg) <= 22:
                plain += 1
    return plain / max(border_pixels, 1)


def evaluate_texture_output(image_path: str | Path, *, guide_path: str | Path | None = None) -> dict[str, Any]:
    """Return pass/warn/reject metadata for a generated UV texture image.

    This is intentionally heuristic. It catches obvious failures without making
    generation brittle or depending on heavyweight OCR/CV packages.
    """

    path = Path(image_path)
    try:
        with Image.open(path) as source:
            image = _resize_for_analysis(source)
            original_size = list(source.size)
    except Exception as exc:  # noqa: BLE001
        return {
            "version": TEXTURE_QUALITY_VERSION,
            "status": "not_evaluated",
            "reject": False,
            "error": str(exc),
            "image_path": str(path),
            "guide_path": str(guide_path) if guide_path else None,
        }

    blank = _blank_ratio(image)
    bbox_area = _nonblank_bbox_area_ratio(image)
    orange = _construction_orange_ratio(image)
    vertical = _line_leak_score(image, "vertical")
    horizontal = _line_leak_score(image, "horizontal")
    diag_down = _line_leak_score(image, "diag_down")
    diag_up = _line_leak_score(image, "diag_up")
    micro = _micro_contrast_ratio(image)
    plain_border = _plain_border_ratio(image)
    guide_text = str(guide_path or "")
    topology_mask_reference = "uv_topology_mask" in guide_text or "uv-guides-mask" in guide_text

    reasons: list[str] = []
    warnings: list[str] = []
    if blank >= 0.42:
        reasons.append("large_unpainted_background")
    elif blank >= 0.30:
        warnings.append("moderate_unpainted_background")

    if blank >= 0.22 and bbox_area <= 0.68:
        reasons.append("object_silhouette_on_background")
    elif blank >= 0.16 and bbox_area <= 0.78:
        warnings.append("possible_object_silhouette")

    if orange >= 0.006:
        reasons.append("construction_orange_guide_leak")
    elif orange >= 0.0025:
        warnings.append("possible_orange_guide_leak")

    if max(diag_down, diag_up) >= 0.22 and not topology_mask_reference:
        reasons.append("diagonal_guide_line_leak")
    elif max(diag_down, diag_up) >= 0.14:
        warnings.append("possible_diagonal_guide_line_leak")

    if max(vertical, horizontal) >= 0.26:
        warnings.append("strong_center_axis_trace")

    if micro >= 0.20:
        reasons.append("text_or_qr_like_microcontrast")
    elif micro >= 0.12:
        warnings.append("possible_text_or_qr_like_microcontrast")

    if plain_border >= 0.76 and micro <= 0.10:
        reasons.append("plain_background_frame")
    elif plain_border >= 0.58:
        warnings.append("possible_plain_background_frame")

    reject = bool(reasons)
    status = "reject" if reject else ("warn" if warnings else "pass")
    return {
        "version": TEXTURE_QUALITY_VERSION,
        "status": status,
        "reject": reject,
        "reasons": reasons,
        "warnings": warnings,
        "image_path": str(path),
        "guide_path": str(guide_path) if guide_path else None,
        "metrics": {
            "blank_ratio": round(blank, 4),
            "nonblank_bbox_area_ratio": round(bbox_area, 4),
            "construction_orange_ratio": round(orange, 4),
            "vertical_line_score": round(vertical, 4),
            "horizontal_line_score": round(horizontal, 4),
            "diag_down_line_score": round(diag_down, 4),
            "diag_up_line_score": round(diag_up, 4),
            "micro_contrast_ratio": round(micro, 4),
            "plain_border_ratio": round(plain_border, 4),
        },
        "image_size": original_size,
    }


__all__ = ["TEXTURE_QUALITY_VERSION", "evaluate_texture_output"]
