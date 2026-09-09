"""Xử lý ảnh tại máy: WebP, đổi cỡ, cắt bản og.

Vì sao phải làm tại máy: Gemini API KHÔNG cho xin định dạng đầu ra. Cả
`output_mime_type` lẫn `output_compression_quality` của `types.ImageConfig` đều
ghi rõ trong SDK là *"This field is not supported in Gemini API"* — chúng chỉ
chạy trên Vertex AI. Gemini luôn trả JPEG, và trả JPEG nén rất nhẹ.

Số đo thật trên 4 ảnh bài ML-01 (nguồn JPEG 1376x768, tổng 2.856 KB):

    q=70   207 KB   PSNR 35,8-39,3 dB
    q=80   268 KB   PSNR 37,5-40,4 dB
    q=85   343 KB   PSNR 38,9-41,3 dB   <- mac dinh
    q=88   421 KB   PSNR 39,9-41,8 dB
    q=92   604 KB   PSNR 41,6-42,9 dB

Chọn q=85: từ 40 dB trở lên là ngưỡng mắt thường không phân biệt được, và đây
là "nén vừa phải" đúng nghĩa — giảm 88% byte mà không vỡ nét.

Các hàm ở đây là hàm THUẦN: nhận bytes, trả bytes. Không chạm mạng, không chạm
đĩa, không biết gì về Gemini. Nhờ vậy test được mà không cần khoá API.
"""
from __future__ import annotations
import io
import math
import os

from PIL import Image, ImageChops, ImageStat

CHAT_LUONG_MAC_DINH = 85
# method=6 là mức nén chậm nhất/nhỏ nhất của libwebp. Ảnh sinh một lần rồi dùng
# mãi, nên đánh đổi thời gian lấy byte là đúng chiều.
PHUONG_PHAP = 6

# Tỉ lệ chuẩn cho thẻ chia sẻ mạng xã hội. Khác 16:9 (1,778) của ảnh gốc, nên
# bản og phải CẮT chứ không co giãn — co giãn sẽ làm méo người trong ảnh.
OG_RONG, OG_CAO = 1200, 630


class AnhSai(ValueError):
    pass


def chat_luong_cau_hinh() -> int:
    """Đọc FICOOL_WEBP_QUALITY, kiểm biên ngay lúc đọc.

    Kiểm ở đây chứ không lúc dùng: một giá trị sai phải làm hỏng lượt chạy ngay
    từ đầu, không phải sau khi đã tiêu tiền sinh bốn tấm ảnh.
    """
    raw = os.getenv('FICOOL_WEBP_QUALITY', '')
    if not raw.strip():
        return CHAT_LUONG_MAC_DINH
    try:
        q = int(raw)
    except ValueError:
        raise AnhSai('FICOOL_WEBP_QUALITY=%r khong phai so nguyen' % raw) from None
    if not 1 <= q <= 100:
        raise AnhSai('FICOOL_WEBP_QUALITY=%d ngoai khoang 1..100' % q)
    return q


def _mo(du_lieu: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(du_lieu)).convert('RGB')
    except Exception as e:
        raise AnhSai('khong doc duoc anh: %s: %s' % (type(e).__name__, e)) from e


def _ghi_webp(im: Image.Image, chat_luong: int) -> bytes:
    b = io.BytesIO()
    im.save(b, 'WEBP', quality=chat_luong, method=PHUONG_PHAP)
    return b.getvalue()


def sang_webp(du_lieu: bytes, chat_luong: int | None = None) -> bytes:
    return _ghi_webp(_mo(du_lieu), chat_luong or chat_luong_cau_hinh())


def doi_co(du_lieu: bytes, rong: int, chat_luong: int | None = None) -> bytes:
    """Thu nhỏ về `rong`, giữ tỉ lệ. KHÔNG BAO GIỜ PHÓNG TO.

    Phóng to không thêm chi tiết, chỉ thêm byte và làm ảnh mờ. Xin rộng hơn ảnh
    gốc thì trả về đúng cỡ gốc.
    """
    if rong < 1:
        raise AnhSai('rong=%d phai >= 1' % rong)
    im = _mo(du_lieu)
    if rong < im.width:
        im = im.resize((rong, round(im.height * rong / im.width)), Image.LANCZOS)
    return _ghi_webp(im, chat_luong or chat_luong_cau_hinh())


def cat_og(du_lieu: bytes, rong: int = OG_RONG, cao: int = OG_CAO,
           chat_luong: int | None = None) -> bytes:
    """Cắt giữa về tỉ lệ og rồi thu nhỏ.

    Ảnh gốc 16:9 (1,778) rộng hơn tỉ lệ og (1,905) theo chiều dọc, nên phép cắt
    lấy bớt trên/dưới. Cắt GIỮA vì chủ thể của ảnh luôn nằm giữa khung.
    """
    im = _mo(du_lieu)
    ty = rong / cao
    cw, ch = im.width, round(im.width / ty)
    if ch > im.height:
        ch, cw = im.height, round(im.height * ty)
    x, y = (im.width - cw) // 2, (im.height - ch) // 2
    im = im.crop((x, y, x + cw, y + ch))
    if im.width != rong:
        im = im.resize((rong, cao), Image.LANCZOS)
    return _ghi_webp(im, chat_luong or chat_luong_cau_hinh())


def psnr(goc: bytes, sau: bytes) -> float:
    """Đo mức sai lệch so với ảnh gốc, đơn vị dB. Càng cao càng giống.

    Dùng PIL.ImageStat thay vì numpy — repo không có numpy, và thêm một phụ
    thuộc nặng chỉ để tính một căn bậc hai là không đáng.
    """
    a, b = _mo(goc), _mo(sau)
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    s = ImageStat.Stat(ImageChops.difference(a, b))
    mse = sum(x * x for x in s.rms) / 3
    return 99.0 if mse == 0 else 20 * math.log10(255.0 / math.sqrt(mse))
