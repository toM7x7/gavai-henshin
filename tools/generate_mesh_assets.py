"""Generate suit-like part meshes with UVs for viewer runtime.

Output format: mesh.v1 JSON
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MeshData:
    positions: list[float] = field(default_factory=list)
    normals: list[float] = field(default_factory=list)
    uvs: list[float] = field(default_factory=list)
    indices: list[int] = field(default_factory=list)

    def append_vertex(self, x: float, y: float, z: float, u: float, v: float) -> int:
        self.positions.extend([x, y, z])
        self.normals.extend([0.0, 0.0, 0.0])
        self.uvs.extend([u, v])
        return len(self.positions) // 3 - 1

    def append_triangle(self, a: int, b: int, c: int) -> None:
        self.indices.extend([a, b, c])


@dataclass(slots=True)
class ShellRing:
    y: float
    rx: float
    rz: float
    shift_z: float = 0.0
    front_bulge: float = 0.0
    back_flatten: float = 0.0
    front_pinch: float = 0.0
    back_pinch: float = 0.0
    side_bulge: float = 0.0
    power: float = 2.4


def ring(
    y: float,
    rx: float,
    rz: float,
    *,
    shift_z: float = 0.0,
    front_bulge: float = 0.0,
    back_flatten: float = 0.0,
    front_pinch: float = 0.0,
    back_pinch: float = 0.0,
    side_bulge: float = 0.0,
    power: float = 2.4,
) -> ShellRing:
    return ShellRing(
        y=y,
        rx=rx,
        rz=rz,
        shift_z=shift_z,
        front_bulge=front_bulge,
        back_flatten=back_flatten,
        front_pinch=front_pinch,
        back_pinch=back_pinch,
        side_bulge=side_bulge,
        power=power,
    )


def _normalize(x: float, y: float, z: float) -> tuple[float, float, float]:
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    return x / n, y / n, z / n


def _superellipse(value: float, power: float) -> float:
    p = max(power, 1.2)
    return math.copysign(abs(value) ** (2.0 / p), value)


def _ring_point(r: ShellRing, theta: float) -> tuple[float, float]:
    c = math.cos(theta)
    s = math.sin(theta)

    x = r.rx * _superellipse(c, r.power)
    z = r.rz * _superellipse(s, r.power)

    front = max(0.0, s)
    back = max(0.0, -s)
    side = abs(c)

    z += r.front_bulge * (front**1.5)
    z -= r.back_flatten * (back**1.35)
    z += r.shift_z

    x *= 1.0 - r.front_pinch * (front**1.2)
    x *= 1.0 - r.back_pinch * (back**1.2)
    x *= 1.0 + r.side_bulge * (side**1.4)

    return x, z


def recompute_normals(mesh: MeshData) -> None:
    count = len(mesh.positions) // 3
    normals = [0.0] * (count * 3)
    pos = mesh.positions
    idx = mesh.indices

    for i in range(0, len(idx), 3):
        ia = idx[i] * 3
        ib = idx[i + 1] * 3
        ic = idx[i + 2] * 3

        ax, ay, az = pos[ia], pos[ia + 1], pos[ia + 2]
        bx, by, bz = pos[ib], pos[ib + 1], pos[ib + 2]
        cx, cy, cz = pos[ic], pos[ic + 1], pos[ic + 2]

        abx, aby, abz = bx - ax, by - ay, bz - az
        acx, acy, acz = cx - ax, cy - ay, cz - az

        nx = aby * acz - abz * acy
        ny = abz * acx - abx * acz
        nz = abx * acy - aby * acx

        normals[ia] += nx
        normals[ia + 1] += ny
        normals[ia + 2] += nz
        normals[ib] += nx
        normals[ib + 1] += ny
        normals[ib + 2] += nz
        normals[ic] += nx
        normals[ic + 1] += ny
        normals[ic + 2] += nz

    for i in range(0, len(normals), 3):
        nx, ny, nz = _normalize(normals[i], normals[i + 1], normals[i + 2])
        normals[i] = nx
        normals[i + 1] = ny
        normals[i + 2] = nz

    mesh.normals = normals


def build_shell(
    rings: list[ShellRing],
    *,
    radial_segments: int = 72,
    theta_start: float = 0.0,
    theta_end: float = math.tau,
    cap_top: bool = False,
    cap_bottom: bool = False,
) -> MeshData:
    mesh = MeshData()
    if len(rings) < 2:
        return mesh

    ring_start: list[int] = []
    columns = radial_segments + 1
    theta_span = theta_end - theta_start

    for j, r in enumerate(rings):
        ring_start.append(len(mesh.positions) // 3)
        v = j / (len(rings) - 1)
        for i in range(columns):
            u = i / radial_segments
            theta = theta_start + theta_span * u
            x, z = _ring_point(r, theta)
            mesh.append_vertex(x, r.y, z, u, v)

    for j in range(len(rings) - 1):
        a0 = ring_start[j]
        b0 = ring_start[j + 1]
        for i in range(radial_segments):
            a = a0 + i
            b = a0 + i + 1
            c = b0 + i
            d = b0 + i + 1
            mesh.append_triangle(a, c, b)
            mesh.append_triangle(b, c, d)

    if cap_bottom:
        bottom = rings[0]
        center = mesh.append_vertex(0.0, bottom.y, bottom.shift_z, 0.5, 0.5)
        base = ring_start[0]
        for i in range(radial_segments):
            mesh.append_triangle(center, base + i + 1, base + i)

    if cap_top:
        top = rings[-1]
        center = mesh.append_vertex(0.0, top.y, top.shift_z, 0.5, 0.5)
        base = ring_start[-1]
        for i in range(radial_segments):
            mesh.append_triangle(center, base + i, base + i + 1)

    recompute_normals(mesh)
    return mesh


def scale_mesh(mesh: MeshData, sx: float, sy: float, sz: float) -> MeshData:
    out = MeshData(indices=list(mesh.indices), uvs=list(mesh.uvs))
    for i in range(0, len(mesh.positions), 3):
        out.positions.extend(
            [
                mesh.positions[i] * sx,
                mesh.positions[i + 1] * sy,
                mesh.positions[i + 2] * sz,
            ]
        )
    out.normals = list(mesh.normals)
    recompute_normals(out)
    return out


def translate_mesh(mesh: MeshData, tx: float, ty: float, tz: float) -> MeshData:
    out = MeshData(indices=list(mesh.indices), uvs=list(mesh.uvs), normals=list(mesh.normals))
    for i in range(0, len(mesh.positions), 3):
        out.positions.extend(
            [
                mesh.positions[i] + tx,
                mesh.positions[i + 1] + ty,
                mesh.positions[i + 2] + tz,
            ]
        )
    return out


def build_helmet() -> MeshData:
    return build_shell(
        [
            ring(-0.56, 0.10, 0.10, shift_z=-0.02, power=2.2),
            ring(-0.43, 0.22, 0.20, shift_z=-0.01, front_bulge=0.02, power=2.6),
            ring(-0.18, 0.31, 0.28, shift_z=0.04, front_bulge=0.08, back_flatten=0.05, front_pinch=0.08, power=3.0),
            ring(0.10, 0.35, 0.31, shift_z=0.05, front_bulge=0.10, back_flatten=0.08, front_pinch=0.06, power=3.2),
            ring(0.34, 0.30, 0.24, shift_z=0.02, front_bulge=0.06, back_flatten=0.03, power=2.8),
            ring(0.50, 0.20, 0.15, shift_z=-0.02, power=2.4),
        ],
        radial_segments=84,
        cap_top=True,
        cap_bottom=False,
    )


def build_chest() -> MeshData:
    return build_shell(
        [
            ring(-0.60, 0.20, 0.16, shift_z=0.05, front_bulge=0.06, front_pinch=0.14, power=2.8),
            ring(-0.42, 0.33, 0.24, shift_z=0.09, front_bulge=0.12, front_pinch=0.10, power=3.0),
            ring(-0.12, 0.46, 0.31, shift_z=0.12, front_bulge=0.16, front_pinch=0.06, side_bulge=0.06, power=3.2),
            ring(0.14, 0.49, 0.32, shift_z=0.11, front_bulge=0.16, front_pinch=0.06, side_bulge=0.05, power=3.2),
            ring(0.38, 0.42, 0.27, shift_z=0.08, front_bulge=0.12, front_pinch=0.09, power=3.0),
            ring(0.56, 0.26, 0.19, shift_z=0.04, front_bulge=0.07, front_pinch=0.12, power=2.8),
        ],
        radial_segments=72,
        theta_start=0.07 * math.pi,
        theta_end=0.93 * math.pi,
        cap_top=True,
        cap_bottom=True,
    )


def build_back() -> MeshData:
    return build_shell(
        [
            ring(-0.58, 0.18, 0.15, shift_z=-0.06, back_flatten=0.04, back_pinch=0.12, power=2.7),
            ring(-0.40, 0.31, 0.23, shift_z=-0.10, back_flatten=0.08, back_pinch=0.08, power=2.9),
            ring(-0.12, 0.43, 0.29, shift_z=-0.13, back_flatten=0.12, back_pinch=0.06, side_bulge=0.04, power=3.1),
            ring(0.14, 0.45, 0.30, shift_z=-0.12, back_flatten=0.12, back_pinch=0.06, side_bulge=0.03, power=3.1),
            ring(0.36, 0.39, 0.25, shift_z=-0.09, back_flatten=0.08, back_pinch=0.08, power=2.9),
            ring(0.54, 0.24, 0.18, shift_z=-0.05, back_flatten=0.04, back_pinch=0.12, power=2.7),
        ],
        radial_segments=72,
        theta_start=1.07 * math.pi,
        theta_end=1.93 * math.pi,
        cap_top=True,
        cap_bottom=True,
    )


def build_waist() -> MeshData:
    return build_shell(
        [
            ring(-0.34, 0.28, 0.21, shift_z=0.00, front_bulge=0.05, back_flatten=0.04, power=2.8),
            ring(-0.16, 0.38, 0.29, shift_z=0.01, front_bulge=0.07, back_flatten=0.06, side_bulge=0.05, power=3.0),
            ring(0.00, 0.42, 0.31, shift_z=0.01, front_bulge=0.08, back_flatten=0.08, side_bulge=0.06, power=3.2),
            ring(0.16, 0.37, 0.28, shift_z=0.00, front_bulge=0.06, back_flatten=0.06, side_bulge=0.04, power=3.0),
            ring(0.32, 0.28, 0.21, shift_z=0.00, front_bulge=0.04, back_flatten=0.04, power=2.8),
        ],
        radial_segments=72,
        cap_top=False,
        cap_bottom=False,
    )


def build_shoulder() -> MeshData:
    return build_shell(
        [
            ring(-0.25, 0.30, 0.28, shift_z=0.01, front_bulge=0.05, back_flatten=0.03, side_bulge=0.08, power=3.0),
            ring(-0.12, 0.28, 0.27, shift_z=0.01, front_bulge=0.04, side_bulge=0.08, power=3.0),
            ring(0.03, 0.24, 0.22, shift_z=0.01, front_bulge=0.03, side_bulge=0.07, power=2.8),
            ring(0.16, 0.16, 0.15, shift_z=0.00, front_bulge=0.02, power=2.6),
            ring(0.24, 0.08, 0.08, shift_z=0.00, power=2.4),
        ],
        radial_segments=64,
        cap_top=True,
        cap_bottom=False,
    )


def build_upperarm() -> MeshData:
    return build_shell(
        [
            ring(-0.52, 0.15, 0.13, shift_z=0.01, front_bulge=0.02, power=2.6),
            ring(-0.32, 0.17, 0.14, shift_z=0.01, front_bulge=0.03, power=2.8),
            ring(-0.06, 0.20, 0.16, shift_z=0.01, front_bulge=0.04, side_bulge=0.03, power=3.0),
            ring(0.20, 0.19, 0.15, shift_z=0.01, front_bulge=0.03, power=2.8),
            ring(0.40, 0.16, 0.13, shift_z=0.00, front_bulge=0.02, power=2.6),
            ring(0.52, 0.14, 0.12, shift_z=0.00, power=2.4),
        ],
        radial_segments=64,
        cap_top=False,
        cap_bottom=False,
    )


def build_forearm() -> MeshData:
    return build_shell(
        [
            ring(-0.54, 0.13, 0.11, shift_z=0.00, power=2.5),
            ring(-0.34, 0.14, 0.11, shift_z=0.01, front_bulge=0.03, power=2.8),
            ring(-0.10, 0.16, 0.12, shift_z=0.02, front_bulge=0.05, side_bulge=0.03, power=3.0),
            ring(0.14, 0.18, 0.14, shift_z=0.03, front_bulge=0.06, side_bulge=0.04, power=3.0),
            ring(0.36, 0.19, 0.15, shift_z=0.03, front_bulge=0.06, side_bulge=0.03, power=2.9),
            ring(0.54, 0.17, 0.14, shift_z=0.02, front_bulge=0.05, power=2.7),
        ],
        radial_segments=64,
        cap_top=False,
        cap_bottom=False,
    )


def build_thigh() -> MeshData:
    return build_shell(
        [
            ring(-0.56, 0.16, 0.13, shift_z=0.00, front_bulge=0.02, power=2.6),
            ring(-0.30, 0.19, 0.15, shift_z=0.01, front_bulge=0.04, side_bulge=0.03, power=2.9),
            ring(0.00, 0.22, 0.18, shift_z=0.02, front_bulge=0.06, side_bulge=0.05, power=3.1),
            ring(0.30, 0.21, 0.17, shift_z=0.02, front_bulge=0.05, side_bulge=0.04, power=3.0),
            ring(0.50, 0.18, 0.14, shift_z=0.01, front_bulge=0.03, power=2.8),
            ring(0.58, 0.15, 0.12, shift_z=0.00, power=2.5),
        ],
        radial_segments=64,
        cap_top=False,
        cap_bottom=False,
    )


def build_shin() -> MeshData:
    return build_shell(
        [
            ring(-0.58, 0.14, 0.11, shift_z=0.00, power=2.5),
            ring(-0.34, 0.15, 0.12, shift_z=0.01, front_bulge=0.03, power=2.7),
            ring(-0.08, 0.17, 0.14, shift_z=0.02, front_bulge=0.06, side_bulge=0.03, power=3.0),
            ring(0.16, 0.18, 0.15, shift_z=0.03, front_bulge=0.08, side_bulge=0.04, power=3.1),
            ring(0.38, 0.16, 0.13, shift_z=0.02, front_bulge=0.06, power=2.8),
            ring(0.58, 0.12, 0.10, shift_z=0.01, front_bulge=0.04, power=2.5),
        ],
        radial_segments=64,
        cap_top=False,
        cap_bottom=False,
    )


def build_boot() -> MeshData:
    return build_shell(
        [
            ring(-0.44, 0.16, 0.21, shift_z=0.06, front_bulge=0.06, back_flatten=0.04, power=2.6),
            ring(-0.24, 0.18, 0.28, shift_z=0.09, front_bulge=0.10, back_flatten=0.04, side_bulge=0.03, power=2.9),
            ring(0.00, 0.19, 0.33, shift_z=0.10, front_bulge=0.13, back_flatten=0.03, side_bulge=0.04, power=3.1),
            ring(0.20, 0.18, 0.30, shift_z=0.08, front_bulge=0.11, back_flatten=0.03, side_bulge=0.03, power=3.0),
            ring(0.38, 0.16, 0.24, shift_z=0.04, front_bulge=0.08, back_flatten=0.02, power=2.8),
            ring(0.50, 0.14, 0.19, shift_z=0.01, front_bulge=0.05, power=2.6),
        ],
        radial_segments=70,
        cap_top=True,
        cap_bottom=True,
    )


def build_hand() -> MeshData:
    return build_shell(
        [
            ring(-0.26, 0.10, 0.14, shift_z=0.03, front_bulge=0.03, back_flatten=0.02, side_bulge=0.03, power=2.8),
            ring(-0.14, 0.13, 0.18, shift_z=0.05, front_bulge=0.05, back_flatten=0.03, side_bulge=0.04, power=3.0),
            ring(0.00, 0.14, 0.21, shift_z=0.06, front_bulge=0.06, back_flatten=0.03, side_bulge=0.05, power=3.2),
            ring(0.14, 0.13, 0.18, shift_z=0.04, front_bulge=0.05, back_flatten=0.03, side_bulge=0.04, power=3.0),
            ring(0.26, 0.10, 0.13, shift_z=0.02, front_bulge=0.03, back_flatten=0.02, side_bulge=0.03, power=2.8),
        ],
        radial_segments=56,
        cap_top=True,
        cap_bottom=True,
    )


def write_mesh(path: Path, mesh: MeshData, name: str) -> None:
    payload = {
        "format": "mesh.v1",
        "name": name,
        "positions": [round(v, 6) for v in mesh.positions],
        "normals": [round(v, 6) for v in mesh.normals],
        "uv": [round(v, 6) for v in mesh.uvs],
        "indices": mesh.indices,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    out_dir = Path("viewer/assets/meshes")
    out_dir.mkdir(parents=True, exist_ok=True)

    base = {
        "helmet": build_helmet(),
        "chest": build_chest(),
        "back": build_back(),
        "waist": build_waist(),
        "shoulder": build_shoulder(),
        "upperarm": build_upperarm(),
        "forearm": build_forearm(),
        "thigh": build_thigh(),
        "shin": build_shin(),
        "boot": scale_mesh(build_boot(), 1.0, 0.94, 1.08),
        "hand": translate_mesh(scale_mesh(build_hand(), 1.0, 0.95, 1.0), 0.0, 0.0, 0.01),
    }

    mapping = {
        "helmet": "helmet",
        "chest": "chest",
        "back": "back",
        "left_shoulder": "shoulder",
        "right_shoulder": "shoulder",
        "left_upperarm": "upperarm",
        "right_upperarm": "upperarm",
        "left_forearm": "forearm",
        "right_forearm": "forearm",
        "waist": "waist",
        "left_thigh": "thigh",
        "right_thigh": "thigh",
        "left_shin": "shin",
        "right_shin": "shin",
        "left_boot": "boot",
        "right_boot": "boot",
        "left_hand": "hand",
        "right_hand": "hand",
    }

    for part, template in mapping.items():
        write_mesh(out_dir / f"{part}.mesh.json", base[template], part)

    print(f"Generated {len(mapping)} meshes into {out_dir}")


if __name__ == "__main__":
    main()
