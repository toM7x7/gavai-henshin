"""Generate explicit mesh bounds sidecar for mesh.v1 viewer assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_MESH_DIR = Path("viewer/assets/meshes")
DEFAULT_OUTPUT = DEFAULT_MESH_DIR / "mesh-bounds.v1.json"


def compute_bounds(positions: list[int | float]) -> dict[str, Any]:
    if len(positions) < 9 or len(positions) % 3 != 0:
        raise ValueError("positions must contain complete vec3 vertices")
    xs = [float(positions[index]) for index in range(0, len(positions), 3)]
    ys = [float(positions[index]) for index in range(1, len(positions), 3)]
    zs = [float(positions[index]) for index in range(2, len(positions), 3)]
    minimum = [min(xs), min(ys), min(zs)]
    maximum = [max(xs), max(ys), max(zs)]
    size = [maximum[index] - minimum[index] for index in range(3)]
    return {
        "min": [round(value, 6) for value in minimum],
        "max": [round(value, 6) for value in maximum],
        "size": [round(value, 6) for value in size],
        "vertex_count": len(positions) // 3,
    }


def build_sidecar(mesh_dir: Path) -> dict[str, Any]:
    parts: dict[str, Any] = {}
    for mesh_path in sorted(mesh_dir.glob("*.mesh.json")):
        payload = json.loads(mesh_path.read_text(encoding="utf-8"))
        positions = payload.get("positions")
        if not isinstance(positions, list):
            raise ValueError(f"positions missing: {mesh_path}")
        part = mesh_path.name[: -len(".mesh.json")]
        parts[part] = compute_bounds(positions)
    return {
        "contract_version": "mesh-bounds.v1",
        "source_format": "mesh.v1",
        "source_dir": mesh_dir.as_posix(),
        "parts": parts,
    }


def main() -> int:
    mesh_dir = DEFAULT_MESH_DIR
    output = DEFAULT_OUTPUT
    sidecar = build_sidecar(mesh_dir)
    output.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": output.as_posix(), "part_count": len(sidecar["parts"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
