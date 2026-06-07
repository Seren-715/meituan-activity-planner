from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root() -> None:
    """把仓库根目录加入 sys.path，避免测试依赖固定绝对路径。"""
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
