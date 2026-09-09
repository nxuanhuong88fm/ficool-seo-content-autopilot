"""Kiểm kho trước khi chạy.

Bản cũ chỉ kiểm file có TỒN TẠI — nên pipeline/ đứt bảy chỗ mà cổng vẫn xanh.
Bản này IMPORT thật và gọi thật những thứ chạy được offline.
"""
from __future__ import annotations
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MODULE = [
    'pipeline.run', 'pipeline.cli', 'pipeline.chon', 'pipeline.qa', 'pipeline.assembly',
    'pipeline.article', 'pipeline.images', 'pipeline.research', 'pipeline.manifest',
    'pipeline.prioritize', 'pipeline.topic_selector', 'pipeline.utils',
    'connectors.gsc', 'connectors.wordpress', 'connectors.web_search', 'connectors.image_provider',
]
FILE = ['README.md', 'AGENTS.md', '.env.example', 'pyproject.toml',
        'knowledge/seo/topic-seed.json', 'config/forbidden-claims.yaml']

loi = []

for f in FILE:
    if not (ROOT / f).exists():
        loi.append(f'thieu file: {f}')

for m in MODULE:
    try:
        importlib.import_module(m)
    except Exception as e:
        loi.append(f'khong import duoc {m}: {type(e).__name__}: {e}')

if not loi:
    from pipeline.topic_selector import TopicSelector
    from pipeline.qa import _luat_cam

    seed = json.loads((ROOT / 'knowledge/seo/topic-seed.json').read_text(encoding='utf-8'))
    tong = sum(len(v) for v in seed.values())
    if tong != 108 or len(seed) != 6 or any(len(v) != 18 for v in seed.values()):
        loi.append(f'mong doi 6 nhom x 18 = 108 chu de, dang co {tong}')
    if len(TopicSelector().all()) != 108:
        loi.append('TopicSelector khong dung ra 108 chu de')
    if not _luat_cam():
        loi.append('config/forbidden-claims.yaml khong nap duoc luat nao')

if loi:
    raise SystemExit('KIEM KHO HONG:\n  - ' + '\n  - '.join(loi))

print(f'OK: {len(MODULE)} module import duoc, {len(FILE)} file co mat, 108 chu de, '
      f'{len(_luat_cam())} luat cam.')
