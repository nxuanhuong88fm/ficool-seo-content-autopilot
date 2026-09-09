"""Xử lý ảnh tại máy — WebP, đổi cỡ, cắt og.

Mỗi phép ở đây đều bẻ đỏ được; xem cột "bẻ đỏ bằng" trong kế hoạch.
"""
from __future__ import annotations
import io
import struct

import pytest
from PIL import Image

from pipeline.anh_xu_ly import (CHAT_LUONG_MAC_DINH, AnhSai, cat_og,
                                chat_luong_cau_hinh, doi_co, psnr, sang_webp)


def _anh_jpeg(rong=1376, cao=768) -> bytes:
    """Ảnh giống ảnh CHỤP: chuyển sắc mượt + chút vân.

    Không dùng nhiễu tần số cao — nhiễu là đầu vào đối kháng với mọi bộ nén
    ảnh, PSNR đo trên đó không nói gì về ảnh chụp thật.
    """
    im = Image.new('RGB', (rong, cao))
    px = im.load()
    for y in range(cao):
        for x in range(rong):
            px[x, y] = (
                int(210 * x / rong) + (12 if (x // 64 + y // 64) % 2 else 0),
                int(180 * y / cao) + 30,
                int(140 * (x + y) / (rong + cao)) + 60,
            )
    b = io.BytesIO()
    im.save(b, 'JPEG', quality=95)
    return b.getvalue()


NGUON = _anh_jpeg()


def _co(du_lieu: bytes):
    return Image.open(io.BytesIO(du_lieu)).size


# ── định dạng ───────────────────────────────────────────────────────────────
def test_sang_webp_cho_ra_dung_dinh_dang():
    ra = sang_webp(NGUON)
    assert ra[:4] == b'RIFF' and ra[8:12] == b'WEBP'
    assert Image.open(io.BytesIO(ra)).format == 'WEBP'


def test_webp_nhe_hon_jpeg_nguon_cung_kich_thuoc():
    ra = sang_webp(NGUON)
    assert _co(ra) == _co(NGUON)
    assert len(ra) < len(NGUON), '%d B khong nho hon %d B' % (len(ra), len(NGUON))


def test_psnr_du_cao_o_chat_luong_mac_dinh():
    """>=38 dB: nen vua phai, khong vo net."""
    assert psnr(NGUON, sang_webp(NGUON)) >= 38.0


def test_psnr_tut_khi_nen_qua_manh():
    """Phep psnr phai NHAY — neu no tra cung mot so bat ke q thi no khong do gi.

    Do tinh DON DIEU chu khong do nguong tuyet doi: anh chuyen sac muot nen qua
    tot, q=5 van cho 40 dB. Nguong tuyet doi o day se phu thuoc fixture chu
    khong phu thuoc hanh vi cua ham.
    """
    cao = psnr(NGUON, sang_webp(NGUON, 92))
    thap = psnr(NGUON, sang_webp(NGUON, 5))
    assert thap < cao - 3.0, 'q=5 (%.1f dB) khong te hon dang ke q=92 (%.1f dB)' % (thap, cao)


# ── biến môi trường ─────────────────────────────────────────────────────────
def test_chat_luong_mac_dinh(monkeypatch):
    monkeypatch.delenv('FICOOL_WEBP_QUALITY', raising=False)
    assert chat_luong_cau_hinh() == CHAT_LUONG_MAC_DINH


@pytest.mark.parametrize('xau', ['0', '101', '-5', 'tam-muoi', '85.5'])
def test_chat_luong_ngoai_khoang_thi_chan_ngay(monkeypatch, xau):
    """Chan luc DOC cau hinh, khong phai sau khi da tieu tien sinh 4 anh."""
    monkeypatch.setenv('FICOOL_WEBP_QUALITY', xau)
    with pytest.raises(AnhSai):
        chat_luong_cau_hinh()


@pytest.mark.parametrize('tot', ['1', '85', '100'])
def test_chat_luong_hop_le_thi_nhan(monkeypatch, tot):
    monkeypatch.setenv('FICOOL_WEBP_QUALITY', tot)
    assert chat_luong_cau_hinh() == int(tot)


# ── đổi cỡ ──────────────────────────────────────────────────────────────────
def test_doi_co_thu_nho_giu_ti_le():
    assert _co(doi_co(NGUON, 720)) == (720, 402)


def test_doi_co_khong_bao_gio_phong_to():
    """Phong to khong them chi tiet, chi them byte va lam anh mo."""
    assert _co(doi_co(NGUON, 4000)) == (1376, 768)


def test_doi_co_rong_vo_ly_thi_chan():
    with pytest.raises(AnhSai):
        doi_co(NGUON, 0)


# ── bản og ──────────────────────────────────────────────────────────────────
def test_cat_og_dung_kich_thuoc_chuan_social():
    assert _co(cat_og(NGUON)) == (1200, 630)


def test_cat_og_cat_giua_chu_khong_co_gian():
    """Co gian se lam meo nguoi trong anh. Phai CAT."""
    im = Image.new('RGB', (1376, 768), 'white')
    for x in range(1376):
        for y in range(0, 18):
            im.putpixel((x, y), (255, 0, 0))   # vach 18px, mong hon 23px se bi cat
    b = io.BytesIO(); im.save(b, 'JPEG', quality=95)
    ra = Image.open(io.BytesIO(cat_og(b.getvalue())))
    assert ra.size == (1200, 630)
    # Kiem kenh LUC, khong phai kenh do: vach do la (255,0,0), nen trang la
    # (255,255,255) — ca hai deu co R=255, kiem R khong phan biet duoc gi.
    for y in (0, 2, 5):
        r, g, _ = ra.getpixel((600, y))
        assert g > 200, 'hang %d con vach do (%d,%d) => dang co gian chu khong cat' % (y, r, g)


def test_cat_og_nguon_da_dung_ti_le_thi_khong_cat_thua():
    b = io.BytesIO(); Image.new('RGB', (2400, 1260), 'white').save(b, 'JPEG')
    assert _co(cat_og(b.getvalue())) == (1200, 630)


# ── đầu vào hỏng ────────────────────────────────────────────────────────────
@pytest.mark.parametrize('ham', [sang_webp, lambda d: doi_co(d, 720), cat_og])
def test_du_lieu_khong_phai_anh_thi_bao_ro(ham):
    with pytest.raises(AnhSai, match='khong doc duoc anh'):
        ham(b'day khong phai anh' * 10)


# ── VP8L: bộ đọc kích thước không được vỡ ───────────────────────────────────
def test_kich_thuoc_that_doc_duoc_webp_lossless():
    """Ta ghi lossy nen duong chinh an toan, nhung WebP nay la dinh dang chinh
    cua ca pipeline — bo doc khong duoc vo khi gap lossless."""
    from connectors.image_provider.provider import kich_thuoc_that
    b = io.BytesIO()
    Image.open(io.BytesIO(NGUON)).save(b, 'WEBP', lossless=True)
    d = b.getvalue()
    assert d[12:16] == b'VP8L'
    assert kich_thuoc_that(d, 'image/webp') == (1376, 768)


def test_kich_thuoc_that_doc_duoc_webp_lossy():
    from connectors.image_provider.provider import kich_thuoc_that
    d = sang_webp(NGUON)
    assert d[12:16] == b'VP8 '
    assert kich_thuoc_that(d, 'image/webp') == (1376, 768)
