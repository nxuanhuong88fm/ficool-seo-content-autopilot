"""Phủ phần rủi ro nhất của lượt chuyển sang Gemini: đọc kích thước ảnh THẬT
và đường model từ chối trả ảnh.

Bản OpenAI cũ khai width/height theo con số xin trước; Gemini chỉ nhận TỈ LỆ và
`image_size='2K'` không nói chính xác bao nhiêu pixel. Con số đó đi thẳng vào
`<img width height>`, khai sai là tự sinh layout shift.
"""
from __future__ import annotations
import struct
import zlib

import pytest

from connectors.image_provider import GeneratedImage, kich_thuoc_that, ti_le_gan_nhat
from connectors.image_provider.provider import GeminiImageProvider


# ── dựng ảnh thật/header thật để kiểm bộ đọc ────────────────────────────────
def png_that(rong, cao):
    def chunk(ten, noi_dung):
        return (struct.pack('>I', len(noi_dung)) + ten + noi_dung
                + struct.pack('>I', zlib.crc32(ten + noi_dung) & 0xFFFFFFFF))
    ihdr = struct.pack('>IIBBBBB', rong, cao, 8, 2, 0, 0, 0)
    raw = b''.join(b'\x00' + b'\xff\x00\x00' * rong for _ in range(cao))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def jpeg_header(rong, cao):
    sof = b'\xff\xc0' + struct.pack('>HBHHB', 17, 8, cao, rong, 3) + b'\x00' * 9
    return b'\xff\xd8' + b'\xff\xe0' + struct.pack('>H', 16) + b'JFIF\x00' + b'\x00' * 9 + sof


def webp_vp8x(rong, cao):
    than = (b'VP8X' + struct.pack('<I', 10) + b'\x00' * 4
            + (rong - 1).to_bytes(3, 'little') + (cao - 1).to_bytes(3, 'little'))
    return b'RIFF' + struct.pack('<I', 4 + len(than)) + b'WEBP' + than


@pytest.mark.parametrize('dung,mime,rong,cao', [
    (png_that, 'image/png', 7, 3),
    (png_that, 'image/png', 1920, 1080),
    (jpeg_header, 'image/jpeg', 1536, 864),
    (webp_vp8x, 'image/webp', 2048, 1152),
])
def test_doc_dung_kich_thuoc_that(dung, mime, rong, cao):
    assert kich_thuoc_that(dung(rong, cao), mime) == (rong, cao)


def test_dinh_dang_la_thi_dung_lai_chu_khong_khai_bua():
    """Thà hỏng rõ ràng còn hơn khai bừa width/height vào thẻ <img>."""
    with pytest.raises(RuntimeError, match='khong doc duoc kich thuoc'):
        kich_thuoc_that(b'GIF89a' + b'\x00' * 40, 'image/gif')


@pytest.mark.parametrize('rong,cao,mong', [
    (1600, 900, '16:9'), (1536, 1024, '3:2'), (1024, 1024, '1:1'),
    (1080, 1920, '9:16'), (1024, 768, '4:3'), (768, 1024, '3:4'),
])
def test_quy_ve_ti_le_gan_nhat(rong, cao, mong):
    assert ti_le_gan_nhat(rong, cao) == mong


# ── provider: đường thành công và đường model từ chối ───────────────────────
class _Phan:
    def __init__(self, du_lieu, mime):
        self.inline_data = type('D', (), {'data': du_lieu, 'mime_type': mime})()


class _ClientGia:
    def __init__(self, phan, chu=''):
        self._phan, self._chu = phan, chu
        self.goi = {}

    @property
    def models(self):
        return self

    def generate_content(self, model=None, contents='', config=None, **k):
        self.goi = {'model': model, 'config': config}
        return type('R', (), {'parts': self._phan, 'text': self._chu})()


def _provider(monkeypatch, client):
    monkeypatch.setenv('GEMINI_API_KEY', 'gia')
    monkeypatch.setattr('connectors.image_provider.provider.tao_client', lambda *a, **k: client)
    return GeminiImageProvider()


def test_ghi_dung_file_va_doc_dung_kich_thuoc(monkeypatch, tmp_path):
    c = _ClientGia([_Phan(png_that(1920, 1080), 'image/png')])
    a = _provider(monkeypatch, c).generate('x', tmp_path / 'anh', width=1600, height=900)

    assert isinstance(a, GeneratedImage)
    assert a.path.suffix == '.png' and a.path.exists()
    assert (a.width, a.height) == (1920, 1080)      # đọc từ byte, không phải 1600x900 đã xin
    assert a.provider == 'gemini'
    assert c.goi['config'].image_config.aspect_ratio == '16:9'
    assert c.goi['config'].response_modalities == ['IMAGE']


def test_mime_webp_thi_duoi_file_theo_mime(monkeypatch, tmp_path):
    c = _ClientGia([_Phan(webp_vp8x(2048, 1152), 'image/webp')])
    a = _provider(monkeypatch, c).generate('x', tmp_path / 'anh')
    assert a.path.suffix == '.webp' and (a.width, a.height) == (2048, 1152)


def test_model_tu_choi_thi_bao_ro_ly_do(monkeypatch, tmp_path):
    """Bộ lọc an toàn trả CHỮ chứ không trả ảnh. Đây là chuyện sẽ xảy ra thật,
    và phải đọc được lý do thay vì nổ IndexError ở chỗ khác."""
    c = _ClientGia([], chu='Toi khong the tao anh nay vi ly do an toan.')
    with pytest.raises(RuntimeError, match='khong tra ve anh nao'):
        _provider(monkeypatch, c).generate('x', tmp_path / 'anh')


def test_kho_anh_khong_hop_le_thi_chan_ngay_luc_khoi_tao(monkeypatch):
    monkeypatch.setenv('GEMINI_IMAGE_SIZE', '8K')
    with pytest.raises(RuntimeError, match='khong hop le'):
        _provider(monkeypatch, _ClientGia([]))


# ── ke hoach anh: loi do duoc tren bai ML-01 that (09/09) ───────────────────
def test_bon_anh_phai_co_alt_KHAC_NHAU():
    """Ban cu lay subject cua IMG-001/002/003 tu title, primary_keyword va
    secondary_keywords[0] — ca ba gan nhu trung nhau, nen ba anh cung prompt,
    cung alt. Vua phi tien sinh, vua la alt trung lap."""
    from pipeline.images import ImagePipeline
    from pipeline.topic_selector import TopicSelector

    ke = ImagePipeline(provider=object()).plan(TopicSelector().by_id('ML-01'))
    alt = [x['alt'] for x in ke]
    assert len(set(alt)) == 4, alt
    assert len({x['canh'] for x in ke}) == 4


def test_khong_dan_chong_dia_phuong():
    """alt cu cua IMG-004: 'ky thuat vien dien lanh tai TP.HCM tai TP.HCM'."""
    from pipeline.images import ImagePipeline, _gon
    from pipeline.topic_selector import TopicSelector

    assert _gon('kỹ thuật viên điện lạnh tại TP.HCM') == 'kỹ thuật viên điện lạnh'
    assert _gon('Máy lạnh chảy nước trong nhà') == 'Máy lạnh chảy nước trong nhà'

    for t in TopicSelector().all():
        for a in ImagePipeline(provider=object()).plan(t):
            assert a['alt'].count('TP.HCM') <= 1, a['alt']
            assert a['alt'].count('Ficool') == 1


def test_moi_anh_deu_co_alt_title_caption():
    from pipeline.images import ImagePipeline
    from pipeline.topic_selector import TopicSelector

    for a in ImagePipeline(provider=object()).plan(TopicSelector().by_id('MG-05')):
        assert a['alt'] and a['title'] and a['caption']
        assert a['caption'].startswith('Hình minh họa:')


def test_alt_khong_lap_cum_hai_tu_lien_ke():
    """'... chay nuoc trong nha trong nha o TP.HCM' — mau alt dinh ngu chi noi
    chon dat SAU {chu_de} thi dung phai tieu de von da ket thuc bang 'trong nha'."""
    from pipeline.images import ImagePipeline
    from pipeline.topic_selector import TopicSelector

    for t in TopicSelector().all():
        for a in ImagePipeline(provider=object()).plan(t):
            tu = a['alt'].lower().split()
            cap = [' '.join(tu[i:i + 2]) for i in range(len(tu) - 1)]
            for i in range(len(cap) - 2):
                assert cap[i] != cap[i + 2], '%s: lap %r' % (a['alt'], cap[i])
