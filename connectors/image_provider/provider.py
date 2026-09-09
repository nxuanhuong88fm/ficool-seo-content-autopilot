from __future__ import annotations
import mimetypes
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from connectors.gemini import model_anh, tao_client

# Gemini nhận TỈ LỆ, không nhận số pixel. Danh sách đối chiếu tài liệu
# ai.google.dev ngày 09/09/2026.
TI_LE_HOP_LE = {
    '1:1': 1.0, '2:3': 2 / 3, '3:2': 1.5, '3:4': 0.75, '4:3': 4 / 3,
    '9:16': 9 / 16, '16:9': 16 / 9, '21:9': 21 / 9,
}
KHO_HOP_LE = ('1K', '2K', '4K')


def ti_le_gan_nhat(width: int, height: int) -> str:
    muc = width / height if height else 1.0
    return min(TI_LE_HOP_LE, key=lambda k: abs(TI_LE_HOP_LE[k] - muc))


def kich_thuoc_that(du_lieu: bytes, mime: str):
    """Đọc chiều rộng/cao THẬT từ header ảnh.

    Vì sao không khai theo tỉ lệ × khổ: `image_size='2K'` không nói chính xác bao
    nhiêu pixel, và con số đó đi thẳng vào `<img width height>`. Khai sai là tự
    sinh layout shift — đúng thứ cổng A85/CLS đang canh.
    """
    if du_lieu[:8] == b'\x89PNG\r\n\x1a\n' and du_lieu[12:16] == b'IHDR':
        return struct.unpack('>II', du_lieu[16:24])

    if du_lieu[:2] == b'\xff\xd8':                                  # JPEG
        i, n = 2, len(du_lieu)
        while i + 9 < n:
            if du_lieu[i] != 0xFF:
                i += 1
                continue
            dau = du_lieu[i + 1]
            if 0xC0 <= dau <= 0xCF and dau not in (0xC4, 0xC8, 0xCC):
                cao, rong = struct.unpack('>HH', du_lieu[i + 5:i + 9])
                return rong, cao
            i += 2 + struct.unpack('>H', du_lieu[i + 2:i + 4])[0]

    if du_lieu[:4] == b'RIFF' and du_lieu[8:12] == b'WEBP':
        dang = du_lieu[12:16]
        if dang == b'VP8X':
            r = int.from_bytes(du_lieu[24:27], 'little') + 1
            c = int.from_bytes(du_lieu[27:30], 'little') + 1
            return r, c
        if dang == b'VP8 ':
            return (struct.unpack('<H', du_lieu[26:28])[0] & 0x3FFF,
                    struct.unpack('<H', du_lieu[28:30])[0] & 0x3FFF)

    raise RuntimeError(
        f'khong doc duoc kich thuoc anh (mime={mime}, {len(du_lieu)} B). '
        'Dung lai thay vi khai bua width/height vao the <img>.')


@dataclass(frozen=True)
class GeneratedImage:
    path: Path
    width: int
    height: int
    mime_type: str
    provider: str


class ImageProvider(Protocol):
    def generate(self, prompt: str, output_path: Path, width: int = 1536, height: int = 1024) -> GeneratedImage: ...


class GeminiImageProvider:
    """Sinh ảnh bằng Gemini (Nano Banana) qua Google AI Studio."""

    def __init__(self, model=None, kho=None):
        self.client = tao_client()
        self.model = model or model_anh()
        import os
        # Mac dinh 1K, do duoc ngay 09/09/2026 tren gemini-3.1-flash-image, 16:9:
        #   1K ->   355.447 B, 1376x768
        #   2K -> 1.648.460 B, 2752x1536   (4,6 lan so byte)
        # Anh trong bai hien thi rong khoang 800px, nen 1376px da du cho man
        # hinh 2x. Chon 2K la tra 4,6 lan dung luong cho phan khong ai nhin thay.
        self.kho = (kho or os.getenv('GEMINI_IMAGE_SIZE') or '1K').upper()
        if self.kho not in KHO_HOP_LE:
            raise RuntimeError(f'GEMINI_IMAGE_SIZE={self.kho} khong hop le, chon {KHO_HOP_LE}')

    def generate(self, prompt, output_path, width=1536, height=1024) -> GeneratedImage:
        from google.genai import types

        r = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio=ti_le_gan_nhat(width, height),
                    image_size=self.kho,
                ),
            ),
        )

        phan = next((p for p in (getattr(r, 'parts', None) or []) if getattr(p, 'inline_data', None)), None)
        if phan is None:
            # Model có thể từ chối (bộ lọc an toàn) và chỉ trả chữ. Nói rõ lý do
            # thay vì để nổ IndexError ở chỗ khác.
            raise RuntimeError(f'Gemini khong tra ve anh nao. Phan hoi chu: {(getattr(r, "text", "") or "")[:300]}')

        du_lieu = phan.inline_data.data
        mime = phan.inline_data.mime_type or 'image/png'
        duoi = mimetypes.guess_extension(mime) or '.png'
        output_path = Path(output_path).with_suffix('.jpg' if duoi == '.jpe' else duoi)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(du_lieu)

        rong, cao = kich_thuoc_that(du_lieu, mime)
        return GeneratedImage(output_path, rong, cao, mime, 'gemini')


class MockImageProvider:
    def generate(self, prompt, output_path, width=1600, height=900) -> GeneratedImage:
        output_path = Path(output_path).with_suffix('.svg')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text = prompt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')[:180]
        output_path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
            f'<rect width="100%" height="100%" fill="#eef4ff"/>'
            f'<text x="60" y="120" font-family="Arial" font-size="48" fill="#112a63">Ficool Image Placeholder</text>'
            f'<text x="60" y="210" font-family="Arial" font-size="28" fill="#112a63">{text}</text></svg>',
            encoding='utf-8')
        return GeneratedImage(output_path, width, height, 'image/svg+xml', 'mock')
