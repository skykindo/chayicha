"""layout.json 多机位配置：按 profile 解析坐标。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PROFILE_KEYS = (
    "windowTitleKeyword",
    "wishlistPageScan",
    "wishlistListRegion",
    "points",
    "productPage",
    "screenshotRegion",
)


def list_layout_profiles(data: dict) -> list[str]:
    profiles = data.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        return ["default"]
    return list(profiles.keys())


def resolve_layout_data(data: dict, profile: str | None = None) -> dict:
    """
    将 layout.json 解析为 RPA 使用的扁平结构。
    - 含 profiles：合并指定 profile 的坐标字段
    - 无 profiles：兼容旧版扁平 layout.json
    """
    profiles = data.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        return dict(data)

    name = (profile or data.get("activeProfile") or "").strip()
    if not name:
        name = next(iter(profiles))
    if name not in profiles:
        available = ", ".join(profiles.keys())
        raise KeyError(
            f"layout profile {name!r} 不存在，可选: {available}"
        )

    merged: dict[str, Any] = {
        k: v
        for k, v in data.items()
        if k not in ("profiles", "activeProfile", "_profiles说明")
    }
    prof = profiles[name]
    if not isinstance(prof, dict):
        raise ValueError(f"profiles.{name} 必须是对象")

    for key in PROFILE_KEYS:
        if key in prof:
            merged[key] = prof[key]

    merged["_layoutProfile"] = name
    return merged


def load_layout_file(path: Path, profile: str | None = None) -> dict:
    import json

    if not path.is_file():
        raise FileNotFoundError(
            f"缺少 {path}。请复制 layout.example.json 为 layout.json 并校准坐标。"
        )
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    return resolve_layout_data(raw, profile)
