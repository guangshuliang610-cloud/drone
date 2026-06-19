"""
应急无人机调度系统 — 工具函数
文件：utils.py
"""

import json
import os
from PyQt5.QtGui import QColor


def load_json(path, default=None):
    """读取 JSON 文件，不存在则返回默认值"""
    if default is None:
        default = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    """写入 JSON 文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def hc(hex_color):
    """十六进制颜色转 QColor"""
    return QColor(hex_color)
