"""Ảnh THẬT đã có sẵn trong Media Library — đường riêng của ML-02.

Bốn ảnh của ML-02 (post 383) sinh từ 09/09 bằng đường Gemini, trước khi dự án
chuyển sang trình giữ chỗ. Kế hoạch đã chốt giữ nguyên chúng, nên bài này KHÔNG
được dựng bằng `dung_lai_bai.py` — làm vậy là thay bốn ảnh thật bằng bốn hộp
"CẦN ẢNH", tức là đi lùi.

Các phép ở đây đo hai điều khoản của hợp đồng đó:
  · bản ghi ảnh thật phải rẽ được sang nhánh `_the_figure` (assembly.py:147);
  · ảnh KHÔNG nằm trong bảng phải đi nguyên vẹn sang nhánh giữ chỗ.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from dung_lai_anh_co_san import dap_anh_that, doc_cau_hinh   # noqa: E402

from pipeline.assembly import AssemblyPipeline               # noqa: E402

THAN = {
    'IMG-002': {'id': 385, 'url': 'https://ficool.top/a-02.webp',
                'width': 1376, 'height': 768},
}


def _uploaded_giu_cho(*ids):
    return [{'id': i, 'giu_cho': True} for i in ids]


# ── đắp dữ liệu ảnh thật ────────────────────────────────────────────────────
def test_anh_trong_bang_thanh_ban_ghi_anh_that():
    ra = dap_anh_that(_uploaded_giu_cho('IMG-002'), THAN)[0]
    assert ra['giu_cho'] is False
    assert ra['media_id'] == 385
    assert ra['source_url'] == 'https://ficool.top/a-02.webp'


def test_anh_ngoai_bang_khong_bi_dong_vao():
    """Bẻ đỏ bằng cách bỏ nhánh `if not that: ra.append(u)` — lúc đó mọi ảnh
    đều bị đắp và bài mất hết khối giữ chỗ."""
    ra = dap_anh_that(_uploaded_giu_cho('IMG-003'), THAN)[0]
    assert ra == {'id': 'IMG-003', 'giu_cho': True}


def test_giu_nguyen_thu_tu_va_so_luong():
    ra = dap_anh_that(_uploaded_giu_cho('IMG-002', 'IMG-003', 'IMG-004'), THAN)
    assert [x['id'] for x in ra] == ['IMG-002', 'IMG-003', 'IMG-004']


# ── nhánh dựng figure ───────────────────────────────────────────────────────
def _dung(uploaded):
    anh = [{'id': 'IMG-002', 'type': 'instructional', 'alt': 'A', 'title': 'A',
            'caption': 'C', 'width': 1376, 'height': 768}]
    bai = {'body': '# T\n\nx\n\n<!-- IMAGE: IMG-002 -->\n', 'slug': 's'}
    return AssemblyPipeline().run(bai, anh, uploaded, ROOT / 'output')


def test_ban_ghi_anh_that_ra_figure_co_wp_image():
    """Class `wp-image-<id>` KHÔNG bỏ được: thiếu nó thì WordPress không chèn
    `srcset` (assembly.py:83)."""
    html = _dung(dap_anh_that(_uploaded_giu_cho('IMG-002'), THAN))
    assert 'wp-image-385' in html
    assert 'data-anh-id' not in html


def test_van_con_giu_cho_khi_khong_dap():
    html = _dung(_uploaded_giu_cho('IMG-002'))
    assert 'data-anh-id="IMG-002"' in html
    assert 'wp-image-' not in html


# ── cấu hình ────────────────────────────────────────────────────────────────
def test_cau_hinh_chi_co_ML_02_va_du_ba_anh_than():
    """Nếu có mã thứ hai lọt vào đây, nó sẽ lặng lẽ thoát khỏi đường giữ chỗ."""
    c = doc_cau_hinh()
    assert list(c) == ['ML-02']
    assert sorted(c['ML-02']['than']) == ['IMG-002', 'IMG-003', 'IMG-004']


def test_IMG_001_khong_nam_trong_than():
    """Ảnh vai trò `featured` không vào thân bài (RULES A128) — để nó ở đây là
    dựng lại đúng khuyết tật đã sửa."""
    assert 'IMG-001' not in doc_cau_hinh()['ML-02']['than']


def test_featured_khac_og():
    """Bài 383 đang đặt NHẦM bản og 1200×630 làm ảnh đại diện."""
    ft = doc_cau_hinh()['ML-02']['featured']
    assert ft['id'] != ft['og']


@pytest.mark.parametrize('truong', ['id', 'url', 'width', 'height'])
def test_moi_anh_than_du_bon_truong(truong):
    for ma, v in doc_cau_hinh()['ML-02']['than'].items():
        assert truong in v, '%s thieu %s' % (ma, truong)
