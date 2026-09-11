"""Nghiên cứu chủ đề bằng Gemini + Google Search grounding.

Thay cho `openai_research.py`. Khác biệt đáng kể: bản cũ luôn trả
`{'sources': []}` — trường nguồn có tên nhưng không bao giờ có nội dung, nên cổng
QA `co_nguon` thực chất chỉ dựa vào SERP của Serper. Grounding của Gemini trả
URL thật, nên `sources` từ nay là dữ liệu chứ không phải chỗ trống.
"""
from __future__ import annotations

from connectors.gemini import model_van_ban, tao_client


class ResearchError(RuntimeError):
    pass


class GeminiResearchClient:
    def __init__(self, model=None):
        self.client = tao_client()
        self.model = model or model_van_ban()

    def research(self, prompt: str) -> dict:
        from google.genai import types

        try:
            r = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
        except Exception as e:                      # noqa: BLE001 — gói lại cho người gọi
            raise ResearchError(f'Gemini research hong: {type(e).__name__}: {e}') from e

        return {'text': r.text or '', 'sources': self._nguon(r), 'model': self.model}

    @staticmethod
    def _nguon(r) -> list:
        """Rút URL nguồn từ grounding_metadata.

        Đường thuộc tính:
          r.candidates[0].grounding_metadata.grounding_chunks[i].web.uri / .title

        Bọc phòng thủ: khi model KHÔNG tra cứu (nó tự quyết định), grounding_metadata
        vắng mặt hẳn — đó là trạng thái bình thường, không phải lỗi.
        """
        ra, thay = [], set()
        for c in (getattr(r, 'candidates', None) or []):
            md = getattr(c, 'grounding_metadata', None)
            for chunk in (getattr(md, 'grounding_chunks', None) or []):
                web = getattr(chunk, 'web', None)
                uri = getattr(web, 'uri', None)
                if uri and uri not in thay:
                    thay.add(uri)
                    ra.append({'url': uri, 'title': getattr(web, 'title', '') or ''})
        return ra
