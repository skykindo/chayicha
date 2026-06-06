"""从 vision-channels.csv 读取 gridSlot，与心愿单 4×3 格位对齐。"""

from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = REPO_ROOT / "vision-channels.csv"


def load_grid_slot_map(csv_path: Path | None = None) -> dict[str, int]:
    """
    返回 assetKey → 0-based 格位索引（grid_01 = 0）。
    CSV 列 gridSlot 为 1～12；无该列时按数据行顺序 1、2、3…
    """
    path = csv_path or DEFAULT_CSV
    if not path.is_file():
        raise FileNotFoundError(f"缺少 {path}，无法解析心愿单格位。")

    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames or "assetKey" not in reader.fieldnames:
        raise ValueError(f"{path} 缺少 assetKey 列")

    has_grid = "gridSlot" in reader.fieldnames
    slot_map: dict[str, int] = {}
    row_num = 0

    for row in reader:
        asset_key = (row.get("assetKey") or "").strip()
        if not asset_key or asset_key.startswith("#"):
            continue
        row_num += 1

        if has_grid:
            raw = (row.get("gridSlot") or "").strip()
            if not raw:
                raise ValueError(f"{path} 中 {asset_key} 缺少 gridSlot")
            slot_1 = int(raw)
            if slot_1 < 1 or slot_1 > 12:
                raise ValueError(f"gridSlot 须在 1～12，{asset_key} 为 {slot_1}")
            index = slot_1 - 1
        else:
            index = row_num - 1

        if asset_key in slot_map:
            raise ValueError(f"重复 assetKey: {asset_key}")
        if index in slot_map.values():
            dup = next(k for k, v in slot_map.items() if v == index)
            raise ValueError(f"gridSlot 冲突: {asset_key} 与 {dup} 同为 grid_{index + 1:02d}")

        slot_map[asset_key] = index

    return slot_map
