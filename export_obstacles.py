"""
障碍物坐标导出工具
运行后自动生成 CSV 表格，供算法直接读取
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from map_city_quake import Map as CityMap
from map_flood import Map as MountainMap
import numpy as np


def export_obstacles_csv(out_dir):
    cm = CityMap()
    mm = MountainMap()

    # ── 城市场景 ──
    city_rows = []
    for i, o in enumerate(cm.get_obstacles()):
        cx, cy, cz = o["center"]
        w, h, d = o["size"]
        city_rows.append({
            "id": i + 1,
            "type": o["type"],
            "center_x": cx,
            "center_y": cy,
            "center_z": cz,
            "size_w": w,
            "size_h": h,
            "size_z": d,
            "x_min": round(cx - w / 2, 1),
            "x_max": round(cx + w / 2, 1),
            "y_min": round(cy - h / 2, 1),
            "y_max": round(cy + h / 2, 1),
            "z_max": d,
        })

    city_path = os.path.join(out_dir, "obstacles_city.csv")
    with open(city_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=city_rows[0].keys())
        writer.writeheader()
        writer.writerows(city_rows)
    print(f"城市障碍物: {len(city_rows)} 条 -> {city_path}")

    # ── 山区场景 ──
    mount_rows = []
    for i, o in enumerate(mm.get_obstacles()):
        cx, cy, cz = o["center"]
        w, h, d = o["size"]
        mount_rows.append({
            "id": i + 1,
            "type": o["type"],
            "center_x": cx,
            "center_y": cy,
            "center_z": cz,
            "size_w": w,
            "size_h": h,
            "size_z": d,
            "x_min": round(cx - w / 2, 1),
            "x_max": round(cx + w / 2, 1),
            "y_min": round(cy - h / 2, 1),
            "y_max": round(cy + h / 2, 1),
            "z_max": d,
        })

    mount_path = os.path.join(out_dir, "obstacles_mountain.csv")
    with open(mount_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=mount_rows[0].keys())
        writer.writeheader()
        writer.writerows(mount_rows)
    print(f"山区障碍物: {len(mount_rows)} 条 -> {mount_path}")

    # ── 山区地形高程网格 ──
    gx = np.linspace(-320, 320, 65)
    gy = np.linspace(-300, 300, 61)
    GX, GY = np.meshgrid(gx, gy)
    GZ = mm.get_terrain_height(GX, GY)

    terrain_rows = []
    for yi in range(len(gy)):
        for xi in range(len(gx)):
            terrain_rows.append({
                "x": round(float(gx[xi]), 1),
                "y": round(float(gy[yi]), 1),
                "z": round(float(GZ[yi][xi]), 2),
            })

    terrain_path = os.path.join(out_dir, "terrain_grid_mountain.csv")
    with open(terrain_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["x", "y", "z"])
        writer.writeheader()
        writer.writerows(terrain_rows)
    print(f"地形网格: {len(terrain_rows)} 点 -> {terrain_path}")

    # ── 合并 JSON（算法可直接 import） ──
    data = {
        "city": {
            "bounds": {"x_min": -420, "x_max": 420, "y_min": -390, "y_max": 390, "z_min": 0, "z_max": 160},
            "obstacles": city_rows,
            "service_areas": cm.get_service_areas(),
            "rescue_points": cm.get_rescue_points(),
        },
        "mountain": {
            "bounds": {"x_min": -320, "x_max": 320, "y_min": -300, "y_max": 300, "z_min": 0, "z_max": 220},
            "obstacles": mount_rows,
            "service_areas": mm.get_service_areas(),
            "rescue_points": mm.get_rescue_points(),
            "terrain_grid_x": [round(float(v), 1) for v in gx],
            "terrain_grid_y": [round(float(v), 1) for v in gy],
            "terrain_grid_z": [[round(float(GZ[yi][xi]), 2) for xi in range(len(gx))] for yi in range(len(gy))],
        },
    }

    json_path = os.path.join(out_dir, "obstacles_all.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"合并JSON:  -> {json_path}")

    # ── 打印预览 ──
    print("\n" + "=" * 70)
    print("城市障碍物 (obstacles_city.csv)")
    print("=" * 70)
    print(f"{'ID':>3} {'类型':<10} {'X范围':>14} {'Y范围':>14} {'Z高度':>6}")
    print("-" * 70)
    for r in city_rows:
        print(f"{r['id']:3d} {r['type']:<10} [{r['x_min']:6.0f},{r['x_max']:6.0f}] [{r['y_min']:6.0f},{r['y_max']:6.0f}] {r['z_max']:6.0f}")

    print("\n" + "=" * 70)
    print("山区障碍物 (obstacles_mountain.csv)")
    print("=" * 70)
    print(f"{'ID':>3} {'类型':<10} {'X范围':>14} {'Y范围':>14} {'Z高度':>6}")
    print("-" * 70)
    for r in mount_rows:
        print(f"{r['id']:3d} {r['type']:<10} [{r['x_min']:6.0f},{r['x_max']:6.0f}] [{r['y_min']:6.0f},{r['y_max']:6.0f}] {r['z_max']:6.0f}")


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    export_obstacles_csv(out_dir)
