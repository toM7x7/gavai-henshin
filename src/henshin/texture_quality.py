"""Warning-only texture quality probes for generated armor UV atlases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageStat


def _round(value: float) -> float:
    return round(float(value), 4)


def analyze_texture_quality(path: str | Path, *, texture_mode: str = "mesh_uv") -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "texture_quality.v0",
        "mode": "warning_only",
        "probe_scope": "image_probe_not_generation_status",
        "texture_mode": texture_mode,
        "status": "ok",
        "warnings": [],
    }
    try:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            rgba.thumbnail((256, 256))
            width, height = image.size
            result["width"] = width
            result["height"] = height
            result["aspect_ratio"] = _round(width / max(height, 1))

            pixels = list(rgba.getdata())
            total = max(len(pixels), 1)
            visible = [pixel for pixel in pixels if pixel[3] > 10]
            blank = [
                pixel
                for pixel in pixels
                if pixel[3] <= 10 or (pixel[0] >= 246 and pixel[1] >= 246 and pixel[2] >= 246 and max(pixel[:3]) - min(pixel[:3]) <= 8)
            ]
            quantized = {
                (pixel[0] // 32, pixel[1] // 32, pixel[2] // 32)
                for pixel in visible
            }
            grayscale = rgba.convert("L")
            stat = ImageStat.Stat(grayscale)
            edge_hits = 0
            edge_total = 0
            sample = grayscale.load()
            w, h = grayscale.size
            for y in range(h):
                for x in range(w):
                    if x + 1 < w:
                        edge_total += 1
                        if abs(sample[x, y] - sample[x + 1, y]) > 18:
                            edge_hits += 1
                    if y + 1 < h:
                        edge_total += 1
                        if abs(sample[x, y] - sample[x, y + 1]) > 18:
                            edge_hits += 1

            result.update(
                {
                    "visible_ratio": _round(len(visible) / total),
                    "blank_ratio": _round(len(blank) / total),
                    "color_bin_count": len(quantized),
                    "luma_stddev": _round(stat.stddev[0] if stat.stddev else 0.0),
                    "edge_density": _round(edge_hits / max(edge_total, 1)),
                }
            )

            warnings: list[str] = result["warnings"]
            if texture_mode == "mesh_uv" and width != height:
                warnings.append("not_square")
            if result["blank_ratio"] > 0.25:
                warnings.append("blank_area_high")
            if result["visible_ratio"] < 0.75:
                warnings.append("visible_area_low")
            if result["color_bin_count"] < 3:
                warnings.append("low_color_variety")
            if result["edge_density"] < 0.008:
                warnings.append("low_panel_detail")
            if warnings:
                result["status"] = "warn"
            return result
    except Exception as exc:  # noqa: BLE001
        result["status"] = "warn"
        result["warnings"] = ["unreadable_image"]
        result["error"] = str(exc)
        return result


__all__ = ["analyze_texture_quality"]
