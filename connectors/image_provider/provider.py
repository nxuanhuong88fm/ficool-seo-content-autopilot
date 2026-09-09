from __future__ import annotations
import base64, mimetypes, os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# gpt-image-1 chỉ nhận đúng ba khổ này. Xin khổ khác thì API trả lỗi, nên phải
# quy về khổ gần nhất và BÁO LẠI khổ thật — pipeline ghi width/height vào thẻ
# <img>, khai sai là tự sinh layout shift.
KHO_HOP_LE = [(1024, 1024), (1536, 1024), (1024, 1536)]


def _kho_gan_nhat(width: int, height: int):
    ty = width / height if height else 1.0
    return min(KHO_HOP_LE, key=lambda k: abs(k[0] / k[1] - ty))


@dataclass(frozen=True)
class GeneratedImage:
    path: Path
    width: int
    height: int
    mime_type: str
    provider: str


class ImageProvider(Protocol):
    def generate(self, prompt: str, output_path: Path, width: int = 1536, height: int = 1024) -> GeneratedImage: ...


class OpenAIImageProvider:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', '')
        self.model = model or os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-1')
        if not self.api_key:
            raise RuntimeError('OPENAI_API_KEY is required')

    def generate(self, prompt, output_path, width=1536, height=1024) -> GeneratedImage:
        from openai import OpenAI
        w, h = _kho_gan_nhat(width, height)
        result = OpenAI(api_key=self.api_key).images.generate(model=self.model, prompt=prompt, size=f'{w}x{h}')
        item = result.data[0]
        output_path = Path(output_path).with_suffix('.png')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if getattr(item, 'b64_json', None):
            output_path.write_bytes(base64.b64decode(item.b64_json))
        elif getattr(item, 'url', None):
            import requests
            r = requests.get(item.url, timeout=60); r.raise_for_status()
            output_path.write_bytes(r.content)
        else:
            raise RuntimeError('Image API returned neither b64_json nor url')
        return GeneratedImage(output_path, w, h, mimetypes.guess_type(output_path.name)[0] or 'image/png', 'openai')


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
