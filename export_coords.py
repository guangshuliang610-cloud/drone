"""导出当前所有坐标到控制台"""
import sys, json, os
sys.path.insert(0, r'D:\Program Tools\python_project\drone')
from config import DEFAULT_SERVICE_AREAS, DEFAULT_RESCUE_POINTS, BASE_DIR

drones_file = os.path.join(BASE_DIR, "drones.json")
with open(drones_file, "r", encoding="utf-8") as f:
    drones_data = json.load(f)

print("=" * 60)
print("坐标导出报告")
print("=" * 60)

print("\n【城市地震场景】")
print("  服务区:")
for sa in DEFAULT_SERVICE_AREAS:
    if sa["scene"] == "城市地震场景":
        print("    %s: (%.0f, %.0f, %.0f)" % (sa["name"], sa["x"], sa["y"], sa["z"]))
print("  救援点:")
for rp in DEFAULT_RESCUE_POINTS:
    if rp["scene"] == "城市地震场景":
        print("    %s: (%.0f, %.0f, %.0f) [%s]" % (rp["name"], rp["x"], rp["y"], rp["z"], rp["priority_text"]))

print("\n【山区避障场景】")
print("  服务区:")
for sa in DEFAULT_SERVICE_AREAS:
    if sa["scene"] == "山区避障场景":
        print("    %s: (%.0f, %.0f, %.0f)" % (sa["name"], sa["x"], sa["y"], sa["z"]))
print("  救援点:")
for rp in DEFAULT_RESCUE_POINTS:
    if rp["scene"] == "山区避障场景":
        print("    %s: (%.0f, %.0f, %.0f) [%s]" % (rp["name"], rp["x"], rp["y"], rp["z"], rp["priority_text"]))

print("\n【无人机】")
for d in drones_data.get("drones", []):
    print("    %s: 型号=%s 载重=%.1fkg 航程=%.1fkm 速度=%.1fkm/h" % (
        d["name"], d["model"], d["max_payload"], d["max_range"], d["max_speed"]))
print("=" * 60)
