"""Nguồn chủ đề: BẢN ĐỒ FUNNEL của khách, không phải suy đoán từ tiêu đề.

Bản cũ đọc `knowledge/seo/topic-seed.json` — 108 tiêu đề TRẦN — rồi tự đoán tag,
intent, funnel stage và từ khoá bằng cách khớp chuỗi trên tiêu đề. Khách thì có
sẵn một tệp chiến lược ghi rõ từng thứ đó cho từng bài, cộng CTA, liên kết nội bộ
và thứ tự ưu tiên triển khai. Đoán trong khi đã có bản đồ là bỏ phí bản đồ.

`scripts/nhap_ban_do.py` nhập tệp .xlsx đó thành `knowledge/seo/ban-do-funnel.json`.
Nếu tệp ấy vắng mặt, lớp này lùi về hạt giống cũ để kho vẫn chạy được — nhưng
`nguon` sẽ ghi 'topic-seed' để chỗ nào cần biết thì biết.

⚠️ MÃ BÀI ĐỔI NGHĨA GIỮA HAI BẢN ĐỒ. `ML-01` của hạt giống cũ là "máy lạnh chảy
nước", của bản đồ v2 là "máy lạnh không lạnh". Manifest PHẢI ghi
`phien_ban_ban_do` cùng với mã bài, nếu không thì bài chưa viết bị bỏ qua còn bài
đã đăng bị viết lại.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEP_BAN_DO = ROOT / 'knowledge/seo/ban-do-funnel.json'
TEP_HAT_GIONG = ROOT / 'knowledge/seo/topic-seed.json'

SERVICE = {'ML': 'may-lanh', 'MG': 'may-giat', 'TL': 'tu-lanh',
           'TD': 'tu-mat-tu-dong', 'MN': 'may-nuoc-nong', 'TK': 'thiet-bi-khac'}
CATEGORY = {'ML': 'Máy lạnh', 'MG': 'Máy giặt', 'TL': 'Tủ lạnh',
            'TD': 'Tủ mát/Tủ đông', 'MN': 'Máy nước nóng', 'TK': 'Thiết bị khác'}


def _derive_tag(title):
    s = title.casefold()
    if any(x in s for x in ['vệ sinh', 'làm sạch']):
        return 'vệ sinh'
    if any(x in s for x in ['bảo trì', 'bảo dưỡng', 'thanh magie', 'chống giật',
                            'checklist kiểm tra']):
        return 'bảo trì'
    if any(x in s for x in ['lắp ', 'lắp đặt', 'vị trí đặt', 'kê chân']):
        return 'lắp đặt'
    if any(x in s for x in ['chi phí', 'nên chọn', 'khác nhau', 'khi nào nên',
                            'nhiệt độ', 'sắp xếp']):
        return 'kinh nghiệm hay'
    return 'lỗi thường gặp'


def _derive_intent(tag):
    return 'commercial' if tag in ('vệ sinh', 'bảo trì', 'lắp đặt') else 'informational'


def _derive_funnel(tag):
    return {'lỗi thường gặp': 'problem_aware',
            'kinh nghiệm hay': 'solution_aware'}.get(tag, 'service_aware')


def _loai_noi_dung(tags):
    """Tag của khách viết hoa chữ đầu; so sánh phải hạ chữ."""
    t = {x.casefold() for x in tags}
    if 'lỗi thường gặp' in t:
        return 'troubleshooting'
    if t & {'vệ sinh', 'lắp đặt'}:
        return 'how_to'
    return 'guide'


class TopicSelector:
    """`thu_tu`:

    'uu-tien' (mặc định) — P1 trước, theo nguyên tắc 1 của khách:
        "Không publish theo thứ tự STT — Ưu tiên P1 trước".
    'stt' — đúng thứ tự trong tệp của khách.
    """

    def __init__(self, thu_tu: str = 'uu-tien'):
        if thu_tu not in ('uu-tien', 'stt'):
            raise ValueError('thu_tu phai la uu-tien hoac stt, nhan %r' % thu_tu)

        if TEP_BAN_DO.exists():
            self.nguon = 'ban-do-funnel'
            d = json.loads(TEP_BAN_DO.read_text(encoding='utf-8'))
            self.phien_ban_ban_do = d['phien_ban']
            self.topics = [self._tu_ban_do(b) for b in d['bai']]
        else:
            self.nguon = 'topic-seed'
            self.phien_ban_ban_do = 'topic-seed-v1'
            self.topics = self._tu_hat_giong()

        if len(self.topics) != 108:
            raise RuntimeError('cho 108 chu de, nhan %d' % len(self.topics))

        if thu_tu == 'uu-tien':
            # `sorted` ổn định nên trong cùng một mức ưu tiên vẫn giữ thứ tự gốc.
            self.topics.sort(key=lambda t: 0 if t['priority'] == 'P1' else 1)
        self.thu_tu = thu_tu

    # ── nguồn giàu: bản đồ funnel ───────────────────────────────────────────
    @staticmethod
    def _tu_ban_do(b):
        prefix = b['id'].split('-')[0]
        return {
            'id': b['id'],
            'stt': b['stt'],
            'category': b['category'],
            'title': b['title'],
            'slug': b['slug'],
            'tags': b['tags'],
            'primary_keyword': b['primary_keyword'],
            'secondary_keywords': b['secondary_keywords'],
            'intent': b['intent'],
            'funnel_stage': b['funnel_stage'],
            'content_type': _loai_noi_dung(b['tags']),
            'pillar': b['category'],
            'related_topics': b['internal_links'],
            'service': SERVICE[prefix],
            'priority': b['uu_tien_trien_khai'] or b['uu_tien'],
            'status': 'planned',
            # ── phần chiến lược, bản cũ không có gì tương ứng ──
            'cta_chinh': b['cta_chinh'],
            'cta_chuyen_tang': b['cta_chuyen_tang'],
            'trang_dich_vu': b['trang_dich_vu'],
            'diem_chuyen_doi': b['diem_chuyen_doi'],
            'vai_tro': b['vai_tro'],
            'trang_thai_khach': b['trang_thai_khach'],
            'trigger': b['trigger'],
            'loi_hua': b['loi_hua'],
            'bai_tiep_theo': b['bai_tiep_theo'],
        }

    # ── nguồn nghèo: hạt giống cũ, chỉ để kho không chết khi thiếu bản đồ ────
    @staticmethod
    def _tu_hat_giong():
        seed = json.loads(TEP_HAT_GIONG.read_text(encoding='utf-8'))
        ra = []
        for prefix, titles in seed.items():
            for n, title in enumerate(titles, 1):
                tag = _derive_tag(title)
                primary = title.rstrip('?').split(':')[0].strip().casefold()
                ra.append({
                    'id': '%s-%02d' % (prefix, n), 'stt': None,
                    'category': CATEGORY[prefix], 'title': title, 'slug': None,
                    'tags': [tag], 'primary_keyword': primary,
                    'secondary_keywords': [title.casefold(),
                                           '%s tại TP.HCM' % primary],
                    'intent': _derive_intent(tag),
                    'funnel_stage': _derive_funnel(tag),
                    'content_type': _loai_noi_dung([tag]),
                    'pillar': CATEGORY[prefix],
                    'related_topics': ['%s-%02d' % (prefix, i)
                                       for i in range(1, 19) if i != n][:3],
                    'service': SERVICE[prefix],
                    'priority': 'P1' if tag == 'lỗi thường gặp' else 'P2',
                    'status': 'planned',
                })
        return ra

    def by_id(self, topic_id):
        for t in self.topics:
            if t['id'] == topic_id:
                return t
        raise KeyError(topic_id)

    def all(self):
        return self.topics

    def lo(self, so_luong=10, bo_qua=()):
        """Lượt kế tiếp: `so_luong` bài chưa viết, theo đúng thứ tự đang đặt."""
        bo = set(bo_qua)
        return [t for t in self.topics if t['id'] not in bo][:so_luong]
