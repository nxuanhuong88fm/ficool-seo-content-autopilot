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
