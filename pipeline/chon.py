"""Chọn chủ đề tiếp theo cho lượt chạy tự động.

Ghép hai mảnh vốn nằm rời: pipeline/prioritize.py (có sẵn, chưa ai gọi) và cơ chế
chống trùng bê từ scripts/production_draft.py.
"""
from __future__ import annotations
import os

from pipeline import manifest
from pipeline.prioritize import prioritize_topics
from pipeline.topic_selector import TopicSelector


class HetChuDe(RuntimeError):
    pass


def chon_tiep_theo(gsc_rows=None):
    """Trả (topic, xep_hang). Ưu tiên theo tín hiệu GSC, bỏ chủ đề đã làm."""
    chu_de = TopicSelector().all()
    if gsc_rows is None:
        from connectors.gsc import GSCClient
        gsc_rows = GSCClient().last_n_days(int(os.getenv('GSC_LOOKBACK_DAYS', '90')))

    da_co = manifest.da_lam()
    xep_hang = prioritize_topics(chu_de, gsc_rows)
    con_lai = [t for t in xep_hang if t['id'] not in da_co and t['title'] not in da_co]
    if not con_lai:
        raise HetChuDe(f'Ca {len(chu_de)} chu de deu da co ban nhap.')
    return con_lai[0], xep_hang


THU_TU_HOP_LE = ('uu-tien', 'cum', 'luan-phien')


def chon_lo(so_luong: int, thu_tu: str = 'uu-tien'):
    """Chọn N chủ đề CHƯA LÀM, theo thứ tự cố định — không dùng tín hiệu GSC.

    Vì sao không dùng GSC lúc này: site đang `blog_public = 0`, chưa từng được
    lập chỉ mục, nên MỌI chủ đề cùng một điểm nền. Xếp hạng theo GSC khi không
    có dữ liệu GSC là chọn ngẫu nhiên nhưng trông như có căn cứ — tệ hơn là
    chọn theo thứ tự công khai.

    thu_tu:
      uu-tien     — P1 trước, rồi P2 (MẶC ĐỊNH). Đây là nguyên tắc số 1 trong
                    sheet "Cách triển khai" của khách: "Không publish theo thứ
                    tự STT — Ưu tiên P1 trước". 79 bài P1, 29 bài P2.
      cum         — đúng thứ tự STT của khách: ML-01..ML-18, rồi MG-01..
                    Một lô 10 bài nằm trong cùng một dòng thiết bị, gom cụm chủ
                    đề mạnh hơn cho SEO — nhưng đi ngược nguyên tắc 1.
      luan-phien  — vòng qua 6 dòng thiết bị: ML-01, MG-01, TL-01, TD-01, MN-01,
                    TK-01, ML-02... Phủ rộng sớm, mỗi dịch vụ có bài ngay từ lô đầu.
    """
    if so_luong < 1:
        raise ValueError('so_luong phai >= 1')
    if thu_tu not in THU_TU_HOP_LE:
        raise ValueError('thu_tu phai la mot trong %s' % (THU_TU_HOP_LE,))

    # 'cum' va 'luan-phien' dua tren thu tu STT cua khach; 'uu-tien' xep lai.
    chu_de = TopicSelector(thu_tu='uu-tien' if thu_tu == 'uu-tien' else 'stt').all()
    da_co = manifest.da_lam()
    con = [t for t in chu_de if t['id'] not in da_co and t['title'] not in da_co]

    if thu_tu == 'luan-phien':
        theo_nhom = {}
        for t in con:
            theo_nhom.setdefault(t['id'].split('-')[0], []).append(t)
        con = []
        while any(theo_nhom.values()):
            for k in list(theo_nhom):
                if theo_nhom[k]:
                    con.append(theo_nhom[k].pop(0))

    if not con:
        raise HetChuDe('Ca %d chu de deu da co ban nhap.' % len(chu_de))
    return con[:so_luong], len(con)
