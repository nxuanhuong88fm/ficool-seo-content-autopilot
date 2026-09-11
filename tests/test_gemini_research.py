"""Nguồn từ Google Search grounding.

Bản OpenAI cũ luôn trả `{'sources': []}` — trường có tên nhưng không bao giờ có
nội dung, nên cổng QA `co_nguon` thực chất chỉ dựa vào SERP của Serper. Từ nay
`sources` là dữ liệu thật, nên phải đo được cả lúc có lẫn lúc không.
"""
from __future__ import annotations
import pytest

from connectors.web_search.gemini_research import GeminiResearchClient, ResearchError


def _r(chunks):
    web = lambda u, t: type('W', (), {'uri': u, 'title': t})()
    md = type('M', (), {'grounding_chunks': [type('C', (), {'web': web(u, t)})() for u, t in chunks]})()
    return type('R', (), {'candidates': [type('Cd', (), {'grounding_metadata': md})()], 'text': 'noi dung'})()


def test_rut_url_nguon():
    n = GeminiResearchClient._nguon(_r([('https://a.vn/1', 'A'), ('https://b.vn/2', 'B')]))
    assert [x['url'] for x in n] == ['https://a.vn/1', 'https://b.vn/2']
    assert n[0]['title'] == 'A'


def test_bo_url_trung():
    n = GeminiResearchClient._nguon(_r([('https://a.vn/1', 'A'), ('https://a.vn/1', 'A lan hai')]))
    assert len(n) == 1


def test_model_khong_tra_cuu_thi_khong_phai_loi():
    """Gemini TỰ QUYẾT ĐỊNH có tìm hay không. Không tìm thì grounding_metadata
    vắng hẳn — trạng thái bình thường, không được nổ."""
    assert GeminiResearchClient._nguon(type('R', (), {'candidates': []})()) == []
    assert GeminiResearchClient._nguon(type('R', (), {})()) == []
    trong = type('R', (), {'candidates': [type('C', (), {'grounding_metadata': None})()]})()
    assert GeminiResearchClient._nguon(trong) == []


def test_loi_goi_api_duoc_goi_lai_thanh_ResearchError(monkeypatch):
    class _C:
        @property
        def models(self): return self
        def generate_content(self, **k): raise ValueError('429 quota')
    monkeypatch.setenv('GEMINI_API_KEY', 'gia')
    monkeypatch.setattr('connectors.web_search.gemini_research.tao_client', lambda *a, **k: _C())
    with pytest.raises(ResearchError, match='429 quota'):
        GeminiResearchClient().research('x')
