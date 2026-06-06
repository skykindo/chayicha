#!/usr/bin/env python3
"""已迁移至 cleanup_vision_prices.py。保留此入口兼容旧命令。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "cleanup_vision_prices.py"


def main() -> int:
    print("[delete_prices] 请改用: python apps/vision/cleanup_vision_prices.py --delete-all")
    return subprocess.call([sys.executable, str(SCRIPT), "--delete-all"])


if __name__ == "__main__":
    raise SystemExit(main())
