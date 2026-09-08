from pathlib import Path
from typing import Protocol

class ImageProvider(Protocol):
    def generate(self, prompt: str, output_path: Path, width: int = 1600, height: int = 900) -> Path: ...

class MockImageProvider:
    """Creates deterministic SVG placeholder assets for local pipeline tests."""
    def generate(self, prompt: str, output_path: Path, width: int = 1600, height: int = 900) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text = prompt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:180]
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#eef4ff"/><text x="60" y="120" font-family="Arial" font-size="48" fill="#112a63">Ficool Image Placeholder</text><text x="60" y="210" font-family="Arial" font-size="28" fill="#112a63">{text}</text></svg>'''
        # Demo placeholders are SVG despite the production WebP target.
        output_path = output_path.with_suffix(".svg")
        output_path.write_text(svg, encoding="utf-8")
        return output_path
