from pathlib import Path
from typing import Protocol
import os, base64

class ImageProvider(Protocol):
    def generate(self, prompt: str, output_path: Path, width: int = 1536, height: int = 1024) -> Path: ...

class OpenAIImageProvider:
    def __init__(self, api_key=None, model=None):
        self.api_key=api_key or os.getenv('OPENAI_API_KEY','')
        self.model=model or os.getenv('OPENAI_IMAGE_MODEL','gpt-image-1')
        if not self.api_key: raise RuntimeError('OPENAI_API_KEY is required')
    def generate(self,prompt,output_path,width=1536,height=1024):
        from openai import OpenAI
        client=OpenAI(api_key=self.api_key)
        result=client.images.generate(model=self.model,prompt=prompt,size='1536x1024')
        item=result.data[0]
        output_path=output_path.with_suffix('.png'); output_path.parent.mkdir(parents=True,exist_ok=True)
        if getattr(item,'b64_json',None): output_path.write_bytes(base64.b64decode(item.b64_json))
        elif getattr(item,'url',None):
            import requests
            r=requests.get(item.url,timeout=60); r.raise_for_status(); output_path.write_bytes(r.content)
        else: raise RuntimeError('Image API returned neither b64_json nor url')
        return output_path

class MockImageProvider:
    def generate(self, prompt: str, output_path: Path, width: int = 1600, height: int = 900) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text=prompt.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')[:180]
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="#eef4ff"/><text x="60" y="120" font-family="Arial" font-size="48" fill="#112a63">Ficool Image Placeholder</text><text x="60" y="210" font-family="Arial" font-size="28" fill="#112a63">{text}</text></svg>'
        output_path=output_path.with_suffix('.svg'); output_path.write_text(svg,encoding='utf-8'); return output_path
