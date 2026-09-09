"""Sổ ghi các lượt đã chạy — chống viết trùng chủ đề.

Bê từ scripts/production_draft.py (commit 8648a28 "idempotent production draft
runner"). Đây là mảnh mà pipeline/ không có, và là lý do một bản cài đặt thứ hai
được viết ra thay vì sửa bản thứ nhất.

output/manifests/ KHÔNG nằm trong .gitignore và được workflow commit ngược lại
repo, nên sổ này sống qua các lượt chạy trên GitHub Actions.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THU_MUC = ROOT / 'output/manifests'


def da_lam() -> set:
    """Tập hợp topic_id và slug đã từng ra bản nháp."""
    ra = set()
    THU_MUC.mkdir(parents=True, exist_ok=True)
    for p in sorted(THU_MUC.glob('*.json')):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            continue  # sổ hỏng một dòng thì bỏ dòng đó, không làm sập cả lượt
        ra.update(x for x in (d.get('topic_id'), d.get('topic'), d.get('slug'), d.get('wp_slug')) if x)
    return ra


def ghi(run_id: str, topic: dict, article: dict, qa: dict, wp: dict) -> Path:
    THU_MUC.mkdir(parents=True, exist_ok=True)
    duong = THU_MUC / f'{run_id}.json'
    duong.write_text(json.dumps({
        'run_id': run_id,
        'topic_id': topic['id'], 'topic': topic['title'], 'category': topic['category'],
        'slug': article['slug'], 'wp_slug': wp.get('slug'),
        'wp_post_id': wp.get('post_id'), 'wp_status': wp.get('status'), 'wp_link': wp.get('link'),
        'qa': qa, 'media_ids': [m['media_id'] for m in wp.get('media', [])],
        'created_at': datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    return duong
