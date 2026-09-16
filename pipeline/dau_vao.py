"""Đầu vào do TÁC NHÂN cung cấp — nghiên cứu và/hoặc bài viết.

Phương án (a): người điều khiển, Claude Code viết. Hai chặng có thể chuyển từ
API sang tác nhân:

  --nghien-cuu=toi   bỏ Gemini research + Serper + GSC  -> rụng 3 phụ thuộc
  --viet=toi         bỏ Gemini text                     -> Gemini chỉ còn cho ảnh

Mỗi chủ đề một tệp `dau-vao/<TOPIC_ID>.yaml`. Một tệp chứa cả hai phần, phần nào
không dùng thì bỏ trống.

⚠️ KIỂM ĐẦU VÀO CHẶT, CỐ Ý. Tác nhân nộp bài cũng là một nguồn có thể sai — nộp
thiếu nguồn, nộp bài ngắn, nộp meta quá dài. Nếu ở đây dễ dãi thì cổng QA phía
sau mất căn cứ: phép `co_nguon` chỉ còn kiểm rằng trường `sources` TỒN TẠI, chứ
không kiểm nó có nội dung — đúng lỗi của `openai_research.py` cũ (luôn trả
`sources: []` mà không ai biết).
"""
from __future__ import annotations
import re
from pathlib import Path

import yaml

THU_MUC_MAC_DINH = 'dau-vao'

NGUON_TOI_THIEU = 2
CHU_TOI_THIEU_NGHIEN_CUU = 200
TU_TOI_THIEU_BAI = 900


class ThieuDauVao(FileNotFoundError):
    pass


class DauVaoSai(ValueError):
    pass


def duong_dan(topic_id: str, thu_muc=None) -> Path:
    return Path(thu_muc or THU_MUC_MAC_DINH) / (topic_id + '.yaml')


def _doc(topic_id, thu_muc):
    p = duong_dan(topic_id, thu_muc)
    if not p.exists():
        raise ThieuDauVao(
            'thieu %s — chay `ficool yeu-cau` de sinh mau, roi dien vao.' % p)
    d = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    if not isinstance(d, dict):
        raise DauVaoSai('%s: khong phai mot ban ghi YAML' % p)
    return p, d


# ── nghiên cứu ──────────────────────────────────────────────────────────────
def doc_nghien_cuu(topic, thu_muc=None) -> dict:
    p, d = _doc(topic['id'], thu_muc)
    nc = d.get('nghien_cuu') or {}
    loi = []

    van = str(nc.get('van_ban') or '').strip()
    if len(van) < CHU_TOI_THIEU_NGHIEN_CUU:
        loi.append('nghien_cuu.van_ban chi %d ky tu, can >= %d'
                   % (len(van), CHU_TOI_THIEU_NGHIEN_CUU))

    nguon = nc.get('nguon') or []
    hop_le = [n for n in nguon
              if isinstance(n, dict) and str(n.get('url', '')).startswith(('http://', 'https://'))]
    if len(hop_le) < NGUON_TOI_THIEU:
        loi.append('nghien_cuu.nguon co %d URL hop le, can >= %d'
                   % (len(hop_le), NGUON_TOI_THIEU))

    if loi:
        raise DauVaoSai('%s:\n  - %s' % (p, '\n  - '.join(loi)))

    # Dựng đúng hình dạng mà QAPipeline và ArticlePipeline đang chờ.
    return {'topic': topic, 'serp': nc.get('serp') or [],
            'ai_research': {'text': van, 'sources': hop_le},
            'nguon_goc': 'tac_nhan'}


# ── bài viết ────────────────────────────────────────────────────────────────
def doc_bai_viet(topic, thu_muc=None) -> dict:
    p, d = _doc(topic['id'], thu_muc)
    bv = d.get('bai_viet') or {}
    seo = bv.get('seo') or {}
    loi = []

    than = str(bv.get('than') or '').strip()
    so_tu = len(re.findall(r'\w+', than, flags=re.UNICODE))
    if so_tu < TU_TOI_THIEU_BAI:
        loi.append('bai_viet.than co %d tu, can >= %d' % (so_tu, TU_TOI_THIEU_BAI))
    if not re.search(r'^# ', than, re.M):
        loi.append('bai_viet.than thieu dong `# ` mo dau')

    tieu_de = str(seo.get('tieu_de') or '').strip()
    mo_ta = str(seo.get('mo_ta') or '').strip()
    slug = str(seo.get('slug') or '').strip()
    if not 0 < len(tieu_de) <= 60:
        loi.append('seo.tieu_de dai %d ky tu, can 1..60' % len(tieu_de))
    if not 0 < len(mo_ta) <= 160:
        loi.append('seo.mo_ta dai %d ky tu, can 1..160' % len(mo_ta))
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
        loi.append('seo.slug %r khong phai slug hop le' % slug)

    if loi:
        raise DauVaoSai('%s:\n  - %s' % (p, '\n  - '.join(loi)))

    return {'title': tieu_de, 'body': than, 'slug': slug,
            'seo': {'title': tieu_de, 'meta_description': mo_ta,
                    'secondary_keywords': seo.get('tu_khoa_phu') or [],
                    'faq': []}}


# ── mẫu để tác nhân điền ────────────────────────────────────────────────────
def ghi_mau(topic, thu_muc=None, can_bai_viet=True) -> Path:
    from pipeline.article import LUAT_VIET

    p = duong_dan(topic['id'], thu_muc)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        return p

    mau = {
        'chu_de': {'id': topic['id'], 'tieu_de': topic['title'],
                   'tu_khoa_chinh': topic['primary_keyword'],
                   'chuyen_muc': topic['category'], 'the': topic.get('tags', []),
                   'giai_doan_phieu': topic['funnel_stage'],
                   'loai_noi_dung': topic.get('content_type')},
        'nghien_cuu': {
            '_yeu_cau': 'van_ban >= %d ky tu; nguon >= %d URL that (http/https).'
                        % (CHU_TOI_THIEU_NGHIEN_CUU, NGUON_TOI_THIEU),
            'van_ban': '',
            'nguon': [{'url': '', 'title': ''}],
            'serp': [],
        },
    }
    if can_bai_viet:
        mau['bai_viet'] = {
            '_yeu_cau': 'than >= %d tu, dung MOT dong `# `. Xem _luat_viet ben duoi.'
                        % TU_TOI_THIEU_BAI,
            'than': '',
            'seo': {'tieu_de': '', 'mo_ta': '', 'slug': '', 'tu_khoa_phu': []},
        }
        mau['_luat_viet'] = LUAT_VIET

    p.write_text(yaml.safe_dump(mau, allow_unicode=True, sort_keys=False, width=100),
                 encoding='utf-8')
    return p
