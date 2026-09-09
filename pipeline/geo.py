"""Chặng GEO — Generative Engine Optimization.

Mục tiêu: bài viết dễ được máy trả lời (ChatGPT, Perplexity, AI Overviews) TRÍCH
DẪN. Khác SEO cổ điển ở chỗ đích không phải thứ hạng mà là khả năng lấy ra một
đoạn đứng độc lập, đúng và gán được nguồn.

Ranh giới schema — đo trên ficool.top ngày 09/09/2026: Rank Math đã phát sẵn
@graph gồm LocalBusiness/Organization, WebSite, ImageObject, WebPage, Person,
BlogPosting. Phát lại những type đó là tự tạo mâu thuẫn. Ta CHỈ phát FAQPage và
HowTo — đúng hai thứ Rank Math bỏ trống.

Lưu ý trung thực: rich result cho FAQPage trên Google SERP đã bị thu hẹp từ
8/2023 (gần như chỉ còn cho trang chính phủ và y tế). Lý do phát ở đây không
phải để lấy rich result mà để máy trả lời phân giải được cặp hỏi–đáp.
"""
from __future__ import annotations
import json
import re
import statistics

# Rank Math sở hữu những type này. Không đụng vào.
TYPE_RANK_MATH_GIU = {'Article', 'BlogPosting', 'NewsArticle', 'WebPage', 'WebSite',
                      'Organization', 'LocalBusiness', 'Person', 'ImageObject', 'BreadcrumbList'}

MO_DAU_THAM_CHIEU = re.compile(
    r'^\s*(như (?:trên|đã|vừa)|điều (?:này|đó)|việc (?:này|đó)|nó\b|chúng\b|vấn đề (?:này|đó)|ngoài ra|bên cạnh đó)',
    re.I)
DAU_CAU_HOI = re.compile(r'(\?|^\s*(khi nào|tại sao|vì sao|làm sao|làm thế nào|có nên|bao lâu|bao nhiêu|nên|cách)\b)', re.I)


def tach_faq(than_bai: str):
    """Lấy cặp hỏi–đáp từ mục FAQ. Câu hỏi là H3 nằm dưới H2 chứa 'FAQ'."""
    dong = than_bai.splitlines()
    trong_faq = False
    cap, hoi, dap = [], None, []
    for d in dong:
        if d.startswith('## '):
            if hoi:
                cap.append((hoi, ' '.join(dap).strip())); hoi, dap = None, []
            trong_faq = bool(re.search(r'faq|câu hỏi thường gặp', d, re.I))
            continue
        if not trong_faq:
            continue
        if d.startswith('### '):
            if hoi:
                cap.append((hoi, ' '.join(dap).strip()))
            hoi, dap = d[4:].strip(), []
        elif hoi and d.strip():
            dap.append(d.strip())
    if hoi:
        cap.append((hoi, ' '.join(dap).strip()))
    return [(h, a) for h, a in cap if h and a]


def tach_buoc(than_bai: str):
    """Lấy các bước của bài hướng dẫn: danh sách đánh số dưới một H2."""
    buoc = [re.sub(r'^\d+\.\s*', '', d).strip()
            for d in than_bai.splitlines() if re.match(r'^\d+\.\s+\S', d)]
    return [b for b in buoc if len(b) >= 15]


def dung_schema(topic, article, than_bai, url: str) -> dict:
    """Trả {'json_ld': <chuỗi script>, 'types': [...], 'faq': n, 'buoc': n}."""
    node = []
    faq = tach_faq(than_bai)
    if len(faq) >= 2:
        node.append({
            '@type': 'FAQPage',
            '@id': f'{url}#faq',
            'inLanguage': 'vi-VN',
            'mainEntity': [{'@type': 'Question', 'name': h,
                            'acceptedAnswer': {'@type': 'Answer', 'text': a}} for h, a in faq],
        })

    buoc = tach_buoc(than_bai)
    if topic.get('content_type') == 'how_to' and len(buoc) >= 3:
        node.append({
            '@type': 'HowTo',
            '@id': f'{url}#howto',
            'inLanguage': 'vi-VN',
            'name': article['seo'].get('title') or topic['title'],
            'step': [{'@type': 'HowToStep', 'position': i, 'text': b} for i, b in enumerate(buoc, 1)],
        })

    if not node:
        return {'json_ld': '', 'types': [], 'faq': len(faq), 'buoc': len(buoc)}

    do_thi = {'@context': 'https://schema.org', '@graph': node}
    ra = json.dumps(do_thi, ensure_ascii=False, separators=(',', ':'))
    return {'json_ld': f'<script type="application/ld+json">{ra}</script>',
            'types': [n['@type'] for n in node], 'faq': len(faq), 'buoc': len(buoc)}


def _cau(than_bai: str):
    van = re.sub(r'^#{1,6}\s.*$', '', than_bai, flags=re.M)
    van = re.sub(r'<!--.*?-->', '', van, flags=re.S)
    return [c for c in re.split(r'(?<=[.!?])\s+', van) if len(c.split()) >= 3]


def do_geo(topic, article, than_bai, html_body, schema) -> dict:
    """Các phép đo GEO. Mỗi phép đều phải có khả năng đỏ."""
    faq = tach_faq(than_bai)
    cau = _cau(than_bai)
    do_dai = [len(c.split()) for c in cau] or [0]

    # đoạn đầu sau H1: máy trả lời hay lấy nguyên đoạn này
    sau_h1 = re.split(r'^#\s.*$', than_bai, maxsplit=1, flags=re.M)
    mo_dau = next((d.strip() for d in (sau_h1[1] if len(sau_h1) > 1 else than_bai).split('\n\n')
                   if d.strip() and not d.strip().startswith(('#', '<!--', '-', '|'))), '')

    tieu_de = re.findall(r'^#{2,3}\s+(.+)$', than_bai, flags=re.M)

    return {
        # câu trả lời đứng độc lập ngay đầu bài, đủ dài để có nghĩa, đủ ngắn để trích
        'tra_loi_som': 40 <= len(mo_dau) <= 400 and not MO_DAU_THAM_CHIEU.match(mo_dau),
        # câu dài thì không trích được nguyên vẹn
        'cau_du_ngan': statistics.median(do_dai) <= 28,
        'tieu_de_dang_cau_hoi': sum(1 for t in tieu_de if DAU_CAU_HOI.search(t)) >= 2,
        'faq_du_cap': len(faq) >= 2,
        # câu trả lời FAQ phải TỰ CHỨA: máy trích một đáp án mà không có ngữ cảnh trước đó
        'faq_tu_chua': bool(faq) and all(len(a) >= 40 and not MO_DAU_THAM_CHIEU.match(a) for _, a in faq),
        'thuc_the_ro_rang': bool(re.search(r'\bFicool\b', than_bai)) and
                            bool(re.search(r'TP\.?\s?HCM|Hồ Chí Minh|Sài Gòn', than_bai, re.I)),
        'co_dinh_dang_trich_duoc': bool(re.search(r'<(ul|ol|table)\b', html_body, re.I)),
        'co_schema': bool(schema['types']),
        # không lấn sang type Rank Math đã phát
        'khong_trung_rank_math': not (set(schema['types']) & TYPE_RANK_MATH_GIU),
    }
