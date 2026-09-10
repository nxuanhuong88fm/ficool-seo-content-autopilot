from __future__ import annotations
import re
from functools import lru_cache
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
LUAT_CAM = ROOT / 'config/forbidden-claims.yaml'

# Từ chức năng tiếng Việt. `primary_keyword` của repo này là NGUYÊN TIÊU ĐỀ viết
# thường — trung bình 7,7 từ, 71/108 chủ đề từ 7 từ trở lên. Đòi nó xuất hiện
# nguyên văn thì hoặc chặn gần hết bài, hoặc ép model nhồi cả câu vào bài. Nên
# đo ĐỘ PHỦ của các từ mang nghĩa thay vì so chuỗi.
TU_CHUC_NANG = {
    'khi', 'nào', 'nên', 'và', 'thì', 'để', 'trong', 'ngoài', 'cho', 'của', 'vì',
    'thay', 'chỉ', 'có', 'là', 'những', 'các', 'một', 'với', 'từ', 'được', 'bị',
    'do', 'mà', 'này', 'đó', 'ra', 'vào', 'lên', 'xuống', 'hay', 'hoặc', 'sau',
    'trước', 'gì', 'sao', 'bao', 'nhiêu', 'phải', 'cần', 'làm', 'khác', 'nhau',
}
NGUONG_PHU = 0.7


@lru_cache(maxsize=1)
def _luat_cam():
    du_lieu = yaml.safe_load(LUAT_CAM.read_text(encoding='utf-8'))
    return [(l['ten'], re.compile(l['mau'], re.I)) for l in du_lieu['luat']]


def tu_mang_nghia(cum: str):
    return [t for t in re.findall(r'\w+', cum.casefold(), flags=re.UNICODE) if t not in TU_CHUC_NANG]


def do_phu_tu_khoa(tu_khoa: str, than_bai: str) -> float:
    tu = tu_mang_nghia(tu_khoa)
    if not tu:
        return 1.0
    kho = than_bai.casefold()
    return sum(1 for t in tu if t in kho) / len(tu)


def khang_dinh_bi_cam(van_ban: str):
    """Trả danh sách (tên luật, đoạn khớp). Rỗng nghĩa là sạch."""
    return [(ten, m.group(0)) for ten, mau in _luat_cam() for m in [mau.search(van_ban)] if m]


class QAPipeline:
    def run(self, topic, article, html_body, images, research, geo=None):
        than = article['body']
        vi_pham = khang_dinh_bi_cam(than)
        phu = do_phu_tu_khoa(topic['primary_keyword'], than)
        so_h1 = len(re.findall(r'<h1\b', html_body, re.I))
        neo = re.findall(r'<a\s+href="([^"]+)"', html_body, re.I)
        so_tu = len(re.findall(r'\w+', than, flags=re.UNICODE))

        checks = {
            # KHÔNG h1 nào trong post_content: theme đã render tiêu đề thành
            # H1 rồi (Bricks #268 `ps1h1` = {post_title}). Bản cũ khẳng định
            # `== 1` trong khi ghi chú ngay trên nó nói "hai h1 là lỗi cấu trúc"
            # — ghi chú đúng, khẳng định ngược, và cổng bảo đảm đúng cái nó định
            # chặn. Đo được trên 20/20 bài đã đăng ngày 10/09.
            'h1_duy_nhat': so_h1 == 0,
            'phu_tu_khoa': phu >= NGUONG_PHU,
            'faq': bool(re.search(r'faq|câu hỏi thường gặp', than, re.I)),
            'khong_khang_dinh_cam': not vi_pham,
            'anh_du_va_co_alt': len(images) >= 3 and all(i.get('alt') for i in images),
            'anh_da_chen': html_body.count('ficool-article-image') >= len(images),
            'co_nguon': bool(research.get('serp') or research.get('ai_research', {}).get('sources')),
            'boi_canh_dia_phuong': bool(re.search(r'TP\.?\s?HCM|Hồ Chí Minh|Sài Gòn', than, re.I)),
            # liên kết nội bộ phải PHÂN GIẢI được, không còn chú thích thô
            'lien_ket_noi_bo': bool(neo) and all(a.startswith(('/', 'https://ficool.top')) for a in neo),
            'khong_con_chu_thich_tho': '<!-- INTERNAL' not in html_body and '<!-- IMAGE' not in html_body,
            # đường dẫn máy lọt vào bài là dấu hiệu ảnh chưa được thay bằng URL WP
            'khong_lo_duong_dan_may': not re.search(r'file://|[A-Za-z]:\\|/tmp/|/var/folders/', html_body),
            'do_dai_title': 0 < len(str(article.get('seo', {}).get('title', ''))) <= 60,
            'do_dai_meta': 0 < len(str(article.get('seo', {}).get('meta_description', ''))) <= 160,
            'du_dai_bai': so_tu >= 800,
        }
        # Phép đo GEO gộp thẳng vào cùng một cổng — không dựng cổng thứ hai.
        # Hai cổng song song là cách chúng lệch nhau (xem scripts/production_draft.py cũ).
        checks.update(geo or {})
        # MỌI phép đều chặn. Bản cũ tính điểm 11 phép nhưng chỉ chặn 7 — bốn phép
        # còn lại (kể cả độ dài title/meta) chỉ để nhìn cho đẹp.
        return {
            'status': 'PASS' if all(checks.values()) else 'BLOCK',
            'overall': round(100 * sum(checks.values()) / len(checks)),
            'checks': checks,
            'blockers': [k for k, v in checks.items() if not v],
            'chi_tiet': {'do_phu_tu_khoa': round(phu, 2), 'so_tu': so_tu,
                         'vi_pham_luat_cam': vi_pham, 'so_h1': so_h1},
        }
