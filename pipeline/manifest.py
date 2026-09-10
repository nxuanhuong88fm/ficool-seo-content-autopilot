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
    # ⚠️ PHIÊN BẢN BẢN ĐỒ phải nằm cạnh mã bài. `ML-01` của hạt giống cũ là "máy
    # lạnh chảy nước", của bản đồ funnel v2 là "máy lạnh không lạnh". Sổ chỉ ghi
    # mã bài thì bài chưa viết bị bỏ qua, còn bài đã đăng bị viết lại.
    from pipeline.topic_selector import TopicSelector
    duong.write_text(json.dumps({
        'run_id': run_id,
        'topic_id': topic['id'], 'topic': topic['title'], 'category': topic['category'],
        'phien_ban_ban_do': TopicSelector().phien_ban_ban_do,
        'slug': article['slug'], 'wp_slug': wp.get('slug'),
        'wp_post_id': wp.get('post_id'), 'wp_status': wp.get('status'), 'wp_link': wp.get('link'),
        'qa': qa, 'media_ids': [m.get('media_id') for m in wp.get('media', [])],
        'created_at': datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    return duong


def dang_cho() -> list:
    """Các lượt đã dựng gói nhưng CHƯA lên WordPress.

    Đường `ho-so` ghi sổ ngay lúc dựng gói — cố ý, vì sổ nghĩa là "đã tiêu ngân
    sách API cho chủ đề này", và chạy lại là tiêu lần nữa. Nhưng thế thì phải có
    chỗ nhìn ra gói nào còn nợ chưa đăng, nếu không nó lặng lẽ mất.
    """
    ra = []
    THU_MUC.mkdir(parents=True, exist_ok=True)
    for p in sorted(THU_MUC.glob('*.json')):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            continue
        if d.get('wp_status') == 'cho_tac_nhan' and not d.get('wp_post_id'):
            ra.append(d)
    return ra


def danh_dau_da_dang(run_id: str, post_id: int, link: str = '') -> Path:
    """Đóng sổ sau khi tác nhân đã đăng gói lên WordPress."""
    duong = THU_MUC / (run_id + '.json')
    if not duong.exists():
        raise FileNotFoundError('khong thay so cua luot %s' % run_id)
    d = json.loads(duong.read_text(encoding='utf-8'))
    d['wp_post_id'] = int(post_id)
    d['wp_status'] = 'draft'
    d['wp_link'] = link or d.get('wp_link')
    d['dang_luc'] = datetime.now(timezone.utc).isoformat()
    duong.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    return duong
