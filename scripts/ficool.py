#!/usr/bin/env python
"""Vỏ mỏng cho `pipeline.cli`.

`python scripts/ficool.py` đặt scripts/ lên sys.path chứ KHÔNG đặt gốc repo, nên
`import connectors` nổ ModuleNotFoundError — đó chính là lỗi đã làm hỏng 29/29
lượt CI. Chèn gốc repo vào sys.path là xong.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
